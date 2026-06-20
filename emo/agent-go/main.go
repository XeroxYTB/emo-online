package main

// emo-agent — Local execution agent for Émo, in Go.
// Single static binary. No runtime dependencies.
//
// Reads token from (in this order):
//   1. --token CLI flag
//   2. EMO_AGENT_TOKEN env var
//   3. ./token.txt (next to the binary)
//   4. ~/.emo/token.txt
//
// Backend URL from --backend or EMO_BACKEND_URL or compiled-in default.

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// Default backend — override at build: -ldflags "-X main.defaultBackend=http://127.0.0.1:8010"
var defaultBackend = "http://127.0.0.1:8010"
var version = "2.4.1"

type ToolRequest struct {
	ID   string                 `json:"id"`
	Tool string                 `json:"tool"`
	Args map[string]interface{} `json:"args"`
}

type PollResponse struct {
	Empty   bool         `json:"empty"`
	Request *ToolRequest `json:"request,omitempty"`
}

type ToolResult map[string]interface{}

var (
	httpClient = &http.Client{Timeout: 35 * time.Second}
	debugLog   = false
)

func logf(format string, args ...interface{}) {
	fmt.Printf("[emo-agent] "+format+"\n", args...)
}

func debugf(format string, args ...interface{}) {
	if debugLog {
		fmt.Printf("[emo-agent debug] "+format+"\n", args...)
	}
}

// -------------------------- TOOLS --------------------------

func toolExecShell(args map[string]interface{}) ToolResult {
	cmd, _ := args["cmd"].(string)
	if cmd == "" {
		return ToolResult{"ok": false, "error": "cmd missing"}
	}
	cwd, _ := args["cwd"].(string)
	timeout := 60
	if t, ok := args["timeout"].(float64); ok && t > 0 {
		timeout = int(t)
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()

	var c *exec.Cmd
	if runtime.GOOS == "windows" {
		c = exec.CommandContext(ctx, "cmd.exe", "/C", cmd)
	} else {
		c = exec.CommandContext(ctx, "sh", "-c", cmd)
	}
	if cwd != "" {
		c.Dir = expand(cwd)
	}
	var stdout, stderr bytes.Buffer
	c.Stdout = &stdout
	c.Stderr = &stderr
	err := c.Run()
	exitCode := 0
	if c.ProcessState != nil {
		exitCode = c.ProcessState.ExitCode()
	}
	if ctx.Err() == context.DeadlineExceeded {
		return ToolResult{"ok": false, "error": fmt.Sprintf("timeout after %ds", timeout), "exit_code": -1}
	}
	if err != nil && exitCode == 0 {
		exitCode = -1
	}
	// Cap stdout/stderr at 64 KB each. Massive outputs (e.g. recursive `dir /s` on a whole drive)
	// would otherwise saturate the SSE pipe and freeze the chat.
	const maxOut = 64 * 1024
	soStr, soTrunc := capString(stdout.String(), maxOut)
	seStr, seTrunc := capString(stderr.String(), maxOut)
	return ToolResult{
		"ok":               true,
		"exit_code":        exitCode,
		"stdout":           soStr,
		"stderr":           seStr,
		"stdout_truncated": soTrunc,
		"stderr_truncated": seTrunc,
	}
}

// capString returns a possibly-truncated string keeping the tail (where errors usually live).
func capString(s string, n int) (string, bool) {
	if len(s) <= n {
		return s, false
	}
	return fmt.Sprintf("…[truncated — kept last %d KB of %d total bytes]…\n%s", n/1024, len(s), s[len(s)-n:]), true
}

func toolReadFile(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	if path == "" {
		return ToolResult{"ok": false, "error": "path missing"}
	}
	p := expand(path)
	info, err := os.Stat(p)
	if err != nil {
		return ToolResult{"ok": false, "error": "file not found"}
	}
	if info.Size() > 5*1024*1024 {
		return ToolResult{"ok": false, "error": "file too large (>5MB) — use offset/limit or grep"}
	}
	data, err := os.ReadFile(p)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	content := string(data)
	offset := 1
	limit := 0
	if o, ok := args["offset"].(float64); ok && o > 0 {
		offset = int(o)
	}
	if l, ok := args["limit"].(float64); ok && l > 0 {
		limit = int(l)
	}
	if offset > 1 || limit > 0 {
		lines := strings.Split(content, "\n")
		start := offset - 1
		if start >= len(lines) {
			return ToolResult{"ok": true, "content": "", "path": p, "offset": offset, "total_lines": len(lines)}
		}
		end := len(lines)
		if limit > 0 && start+limit < end {
			end = start + limit
		}
		slice := lines[start:end]
		var b strings.Builder
		for i, ln := range slice {
			fmt.Fprintf(&b, "%6d|%s\n", start+i+1, ln)
		}
		content = b.String()
	}
	abs, _ := filepath.Abs(p)
	return ToolResult{"ok": true, "content": content, "path": abs, "offset": offset, "limit": limit}
}

func toolWriteFile(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	content, _ := args["content"].(string)
	if path == "" {
		return ToolResult{"ok": false, "error": "path required"}
	}
	p := expand(path)
	if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	if err := os.WriteFile(p, []byte(content), 0644); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	abs, _ := filepath.Abs(p)
	return ToolResult{"ok": true, "path": abs, "bytes": len(content)}
}

func toolListDir(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	if path == "" {
		path = "."
	}
	depth := 1
	if d, ok := args["depth"].(float64); ok && d > 0 {
		depth = int(d)
		if depth > 4 {
			depth = 4
		}
	}
	p := expand(path)
	root, err := filepath.Abs(p)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	if depth <= 1 {
	entries, err := os.ReadDir(p)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	files := []string{}
	dirs := []string{}
	for _, e := range entries {
		name := e.Name()
		if strings.HasPrefix(name, ".") {
			continue
		}
		if e.IsDir() {
			dirs = append(dirs, name)
		} else {
			files = append(files, name)
		}
		}
		return ToolResult{"ok": true, "path": root, "files": files, "dirs": dirs}
	}
	type entry struct {
		Path  string `json:"path"`
		IsDir bool   `json:"is_dir"`
	}
	out := []entry{}
	var walk func(string, int) error
	walk = func(dir string, lvl int) error {
		if lvl > depth {
			return nil
		}
		entries, err := os.ReadDir(dir)
		if err != nil {
			return err
		}
		for _, e := range entries {
			name := e.Name()
			if strings.HasPrefix(name, ".") {
				continue
			}
			full := filepath.Join(dir, name)
			rel, _ := filepath.Rel(root, full)
			out = append(out, entry{Path: filepath.ToSlash(rel), IsDir: e.IsDir()})
			if e.IsDir() && lvl < depth && len(out) < 500 {
				if err := walk(full, lvl+1); err != nil {
					return err
				}
			}
			if len(out) >= 500 {
				return nil
			}
		}
		return nil
	}
	_ = walk(p, 1)
	return ToolResult{"ok": true, "path": root, "entries": out, "truncated": len(out) >= 500}
}

func isBinarySample(data []byte) bool {
	if bytes.IndexByte(data, 0) >= 0 {
		return true
	}
	for _, b := range data {
		if b < 9 || (b > 13 && b < 32) {
			return true
		}
	}
	return false
}

func toolGrep(args map[string]interface{}) ToolResult {
	pattern, _ := args["pattern"].(string)
	if pattern == "" {
		if q, ok := args["query"].(string); ok && q != "" {
			pattern = q
		}
	}
	if pattern == "" {
		return ToolResult{"ok": false, "error": "pattern or query missing"}
	}
	root := "."
	if p, ok := args["path"].(string); ok && p != "" {
		root = expand(p)
	}
	glob := "*"
	if g, ok := args["glob"].(string); ok && g != "" {
		glob = g
	}
	maxResults := 100
	if m, ok := args["max_results"].(float64); ok && m > 0 {
		maxResults = int(m)
		if maxResults > 200 {
			maxResults = 200
		}
	}
	caseInsensitive := false
	if c, ok := args["ignore_case"].(bool); ok {
		caseInsensitive = c
	}
	pat := pattern
	if caseInsensitive {
		pat = strings.ToLower(pattern)
	}
	type match struct {
		File string `json:"file"`
		Line int    `json:"line"`
		Text string `json:"text"`
	}
	matches := []match{}
	_ = filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || len(matches) >= maxResults {
			return nil
		}
		if info.IsDir() {
			base := info.Name()
			if strings.HasPrefix(base, ".") || base == "node_modules" || base == ".git" || base == "vendor" || base == "__pycache__" {
				return filepath.SkipDir
			}
			return nil
		}
		ok, _ := filepath.Match(glob, info.Name())
		if !ok {
			return nil
		}
		if info.Size() > 2*1024*1024 {
			return nil
		}
		f, err := os.Open(path)
		if err != nil {
			return nil
		}
		defer f.Close()
		head := make([]byte, 512)
		n, _ := f.Read(head)
		if isBinarySample(head[:n]) {
			return nil
		}
		f.Seek(0, 0)
		sc := bufio.NewScanner(f)
		lineNo := 0
		for sc.Scan() {
			lineNo++
			line := sc.Text()
			hay := line
			if caseInsensitive {
				hay = strings.ToLower(line)
			}
			if strings.Contains(hay, pat) {
				matches = append(matches, match{File: path, Line: lineNo, Text: ellipsis(line, 300)})
				if len(matches) >= maxResults {
					break
				}
			}
		}
		return nil
	})
	return ToolResult{"ok": true, "pattern": pattern, "matches": matches, "truncated": len(matches) >= maxResults}
}

func toolEditFile(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	oldStr, _ := args["old_string"].(string)
	newStr, _ := args["new_string"].(string)
	if path == "" || oldStr == "" {
		return ToolResult{"ok": false, "error": "path and old_string required"}
	}
	p := expand(path)
	data, err := os.ReadFile(p)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	content := string(data)
	count := strings.Count(content, oldStr)
	if count == 0 {
		return ToolResult{"ok": false, "error": "old_string not found"}
	}
	replaceAll := false
	if r, ok := args["replace_all"].(bool); ok {
		replaceAll = r
	}
	if !replaceAll && count > 1 {
		return ToolResult{"ok": false, "error": fmt.Sprintf("old_string found %d times — use replace_all or be more specific", count)}
	}
	var updated string
	replaced := 0
	if replaceAll {
		updated = strings.ReplaceAll(content, oldStr, newStr)
		replaced = count
	} else {
		updated = strings.Replace(content, oldStr, newStr, 1)
		replaced = 1
	}
	if err := os.WriteFile(p, []byte(updated), 0644); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	abs, _ := filepath.Abs(p)
	return ToolResult{"ok": true, "path": abs, "replacements": replaced}
}

func toolDeletePath(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	if path == "" {
		return ToolResult{"ok": false, "error": "path missing"}
	}
	p := expand(path)
	info, err := os.Stat(p)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	if info.IsDir() {
		err = os.RemoveAll(p)
	} else {
		err = os.Remove(p)
	}
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	return ToolResult{"ok": true, "deleted": p}
}

func toolMovePath(args map[string]interface{}) ToolResult {
	src, _ := args["from"].(string)
	dst, _ := args["to"].(string)
	if src == "" || dst == "" {
		return ToolResult{"ok": false, "error": "from and to required"}
	}
	from := expand(src)
	to := expand(dst)
	if err := os.MkdirAll(filepath.Dir(to), 0755); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	if err := os.Rename(from, to); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	return ToolResult{"ok": true, "from": from, "to": to}
}

func toolFindFiles(args map[string]interface{}) ToolResult {
	pattern, _ := args["pattern"].(string)
	if pattern == "" {
		return ToolResult{"ok": false, "error": "pattern missing (ex: *.java, **/pom.xml)"}
	}
	root := "."
	if p, ok := args["path"].(string); ok && p != "" {
		root = expand(p)
	}
	maxResults := 200
	if m, ok := args["max_results"].(float64); ok && m > 0 {
		maxResults = int(m)
		if maxResults > 500 {
			maxResults = 500
		}
	}
	found := []string{}
	_ = filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || len(found) >= maxResults {
			return nil
		}
		if info.IsDir() {
			base := info.Name()
			if strings.HasPrefix(base, ".") || base == "node_modules" || base == ".git" {
				return filepath.SkipDir
			}
			return nil
		}
		name := info.Name()
		matched := false
		if strings.Contains(pattern, "*") {
			matched, _ = filepath.Match(pattern, name)
		} else {
			matched = strings.Contains(strings.ToLower(path), strings.ToLower(pattern))
		}
		if matched {
			found = append(found, path)
		}
		return nil
	})
	return ToolResult{"ok": true, "pattern": pattern, "files": found, "truncated": len(found) >= maxResults}
}

func toolCodebaseSearch(args map[string]interface{}) ToolResult {
	query, _ := args["query"].(string)
	if query == "" {
		return ToolResult{"ok": false, "error": "query missing"}
	}
	if p, ok := args["path"].(string); ok && p != "" {
		args["path"] = p
	}
	args["pattern"] = query
	args["ignore_case"] = true
	if args["glob"] == nil {
		args["glob"] = "*"
	}
	res := toolGrep(args)
	res["query"] = query
	res["note"] = "recherche texte (grep) — pas sémantique vectorielle"
	return res
}

func toolAppendFile(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	content, _ := args["content"].(string)
	if path == "" {
		return ToolResult{"ok": false, "error": "path required"}
	}
	p := expand(path)
	if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	f, err := os.OpenFile(p, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	defer f.Close()
	n, err := f.WriteString(content)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	abs, _ := filepath.Abs(p)
	return ToolResult{"ok": true, "path": abs, "bytes_written": n}
}

func toolCreateDir(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	if path == "" {
		return ToolResult{"ok": false, "error": "path missing"}
	}
	p := expand(path)
	if err := os.MkdirAll(p, 0755); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	abs, _ := filepath.Abs(p)
	return ToolResult{"ok": true, "path": abs}
}

func toolCopyPath(args map[string]interface{}) ToolResult {
	src, _ := args["from"].(string)
	dst, _ := args["to"].(string)
	if src == "" || dst == "" {
		return ToolResult{"ok": false, "error": "from and to required"}
	}
	from := expand(src)
	to := expand(dst)
	info, err := os.Stat(from)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	if err := os.MkdirAll(filepath.Dir(to), 0755); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	if info.IsDir() {
		var cpCmd *exec.Cmd
		if runtime.GOOS == "windows" {
			cpCmd = exec.Command("xcopy", from, to, "/E", "/I", "/Y")
		} else {
			cpCmd = exec.Command("cp", "-r", from, to)
		}
		out, err := cpCmd.CombinedOutput()
		if err != nil {
			return ToolResult{"ok": false, "error": err.Error(), "output": string(out)}
		}
	} else {
		in, err := os.Open(from)
		if err != nil {
			return ToolResult{"ok": false, "error": err.Error()}
		}
		defer in.Close()
		out, err := os.Create(to)
		if err != nil {
			return ToolResult{"ok": false, "error": err.Error()}
		}
		defer out.Close()
		if _, err := io.Copy(out, in); err != nil {
			return ToolResult{"ok": false, "error": err.Error()}
		}
	}
	return ToolResult{"ok": true, "from": from, "to": to}
}

func toolFileInfo(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	if path == "" {
		return ToolResult{"ok": false, "error": "path missing"}
	}
	p := expand(path)
	info, err := os.Stat(p)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	abs, _ := filepath.Abs(p)
	return ToolResult{
		"ok": true, "path": abs, "size": info.Size(),
		"is_dir": info.IsDir(), "mod_time": info.ModTime().Format(time.RFC3339),
		"mode": info.Mode().String(),
	}
}

func toolGetEnv(args map[string]interface{}) ToolResult {
	names := []string{}
	if raw, ok := args["names"].([]interface{}); ok {
		for _, n := range raw {
			if s, ok := n.(string); ok && s != "" {
				names = append(names, s)
			}
		}
	}
	if len(names) == 0 {
		names = []string{"PATH", "USER", "USERNAME", "HOME", "USERPROFILE", "OS", "COMPUTERNAME", "HOSTNAME"}
	}
	out := map[string]string{}
	for _, n := range names {
		if v := os.Getenv(n); v != "" {
			out[n] = v
		}
	}
	out["go_os"] = runtime.GOOS
	out["go_arch"] = runtime.GOARCH
	return ToolResult{"ok": true, "env": out}
}

func toolSystemInfo(args map[string]interface{}) ToolResult {
	hostname, _ := os.Hostname()
	home, _ := os.UserHomeDir()
	return ToolResult{
		"ok": true, "os": runtime.GOOS, "arch": runtime.GOARCH,
		"hostname": hostname, "home": home, "agent_version": version,
	}
}

func toolGit(args map[string]interface{}, subcmd string) ToolResult {
	root := "."
	if p, ok := args["path"].(string); ok && p != "" {
		root = expand(p)
	}
	extra := []string{subcmd}
	if subcmd == "diff" {
		if staged, ok := args["staged"].(bool); ok && staged {
			extra = append(extra, "--cached")
		}
		if f, ok := args["file"].(string); ok && f != "" {
			extra = append(extra, "--", f)
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "git", extra...)
	cmd.Dir = root
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	exitCode := 0
	if cmd.ProcessState != nil {
		exitCode = cmd.ProcessState.ExitCode()
	}
	so, _ := capString(stdout.String(), 48*1024)
	se, _ := capString(stderr.String(), 16*1024)
	if err != nil && exitCode != 0 && so == "" {
		return ToolResult{"ok": false, "error": se, "exit_code": exitCode}
	}
	return ToolResult{"ok": true, "stdout": so, "stderr": se, "exit_code": exitCode, "path": root}
}

func toolDownloadURL(args map[string]interface{}) ToolResult {
	url, _ := args["url"].(string)
	path, _ := args["path"].(string)
	if url == "" || path == "" {
		return ToolResult{"ok": false, "error": "url and path required"}
	}
	p := expand(path)
	if err := os.MkdirAll(filepath.Dir(p), 0755); err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	resp, err := httpClient.Do(req)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return ToolResult{"ok": false, "error": fmt.Sprintf("HTTP %d", resp.StatusCode)}
	}
	f, err := os.Create(p)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	defer f.Close()
	n, err := io.Copy(f, resp.Body)
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	abs, _ := filepath.Abs(p)
	return ToolResult{"ok": true, "path": abs, "bytes": n, "url": url}
}

func toolApplyPatch(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	patch, _ := args["patch"].(string)
	if path == "" || patch == "" {
		return ToolResult{"ok": false, "error": "path and patch required"}
	}
	tmp, err := os.CreateTemp("", "emo-patch-*.diff")
	if err != nil {
		return ToolResult{"ok": false, "error": err.Error()}
	}
	tmpPath := tmp.Name()
	defer os.Remove(tmpPath)
	if _, err := tmp.WriteString(patch); err != nil {
		tmp.Close()
		return ToolResult{"ok": false, "error": err.Error()}
	}
	tmp.Close()
	p := expand(path)
	dir := filepath.Dir(p)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "git", "apply", "--unsafe-paths", tmpPath)
	cmd.Dir = dir
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return ToolResult{"ok": false, "error": "git apply failed: " + stderr.String()}
	}
	return ToolResult{"ok": true, "path": p, "method": "git apply"}
}

func expand(p string) string {
	if strings.HasPrefix(p, "~") {
		home, _ := os.UserHomeDir()
		if len(p) <= 1 {
			return home
		}
		rest := strings.TrimPrefix(p, "~")
		rest = strings.TrimPrefix(rest, "/")
		rest = strings.TrimPrefix(rest, "\\")
		return filepath.Join(home, rest)
	}
	return p
}

func dispatch(req *ToolRequest) ToolResult {
	args := req.Args
	if args == nil {
		args = map[string]interface{}{}
	}
	perms := loadPermissions()
	if !perms.allowsTool(req.Tool) {
		return ToolResult{"ok": false, "error": "refusé par les permissions locales Emo Agent"}
	}
	switch req.Tool {
	case "exec_shell", "run_terminal_cmd", "bash", "shell":
		return toolExecShell(args)
	case "read_file", "file_search":
		return toolReadFile(args)
	case "write_file", "create_file":
		return toolWriteFile(args)
	case "append_file":
		return toolAppendFile(args)
	case "create_dir":
		return toolCreateDir(args)
	case "copy_path":
		return toolCopyPath(args)
	case "file_info":
		return toolFileInfo(args)
	case "get_env":
		return toolGetEnv(args)
	case "system_info":
		return toolSystemInfo(args)
	case "git_status":
		return toolGit(args, "status")
	case "git_diff":
		return toolGit(args, "diff")
	case "apply_patch":
		return toolApplyPatch(args)
	case "download_url":
		return toolDownloadURL(args)
	case "list_dir":
		return toolListDir(args)
	case "grep", "search":
		return toolGrep(args)
	case "codebase_search":
		return toolCodebaseSearch(args)
	case "edit_file":
		return toolEditFile(args)
	case "delete_path", "delete_file":
		return toolDeletePath(args)
	case "move_path":
		return toolMovePath(args)
	case "find_files":
		return toolFindFiles(args)
	case "print_file", "print_document", "print":
		return toolPrintFile(args)
	default:
		return ToolResult{"ok": false, "error": "unknown tool: " + req.Tool}
	}
}

// -------------------------- HTTP --------------------------

func postJSON(url string, payload interface{}) error {
	body, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)
	if resp.StatusCode >= 400 {
		return fmt.Errorf("HTTP %d", resp.StatusCode)
	}
	return nil
}

func agentMachineContext() map[string]interface{} {
	home, _ := os.UserHomeDir()
	desktop := filepath.Join(home, "Desktop")
	if _, err := os.Stat(desktop); err != nil {
		alt := filepath.Join(home, "OneDrive", "Desktop")
		if _, err2 := os.Stat(alt); err2 == nil {
			desktop = alt
		}
	}
	username := os.Getenv("USERNAME")
	if username == "" {
		username = os.Getenv("USER")
	}
	userprofile := os.Getenv("USERPROFILE")
	if userprofile == "" {
		userprofile = home
	}
	hostname, _ := os.Hostname()
	return map[string]interface{}{
		"home":        home,
		"desktop":     desktop,
		"username":    username,
		"userprofile": userprofile,
		"os":          runtime.GOOS,
		"hostname":    hostname,
	}
}

func heartbeatLoop(ctx context.Context, backend, token string, wg *sync.WaitGroup, onStatus func(bool)) {
	defer wg.Done()
	url := backend + "/api/agent/heartbeat?token=" + token
	ctxPayload := agentMachineContext()
	for {
		err := postJSON(url, ctxPayload)
		if onStatus != nil {
			onStatus(err == nil)
		} else if err != nil {
			debugf("heartbeat error: %v", err)
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(5 * time.Second):
		}
	}
}

func executeAndPost(backend, token string, req *ToolRequest) {
	short := summarizeArgs(req.Tool, req.Args)
	logf("→ %s(%s)", req.Tool, short)
	result := dispatch(req)
	logf("← %s", summarizeResult(result))
	body := map[string]interface{}{"id": req.ID, "result": result}
	if err := postJSON(backend+"/api/agent/result?token="+token, body); err != nil {
		logf("! failed to post result: %v", err)
	}
}

func pollOnce(backend, token string) (*ToolRequest, error) {
	req, err := http.NewRequest("GET", backend+"/api/agent/poll?token="+token, nil)
	if err != nil {
		return nil, err
	}
	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}
	var p PollResponse
	if err := json.NewDecoder(resp.Body).Decode(&p); err != nil {
		return nil, err
	}
	if p.Empty {
		return nil, nil
	}
	return p.Request, nil
}

func runWithStatus(ctx context.Context, backend, token string, onStatus func(bool)) {
	logf("Émo agent v%s — backend = %s", version, backend)

	if err := postJSON(backend+"/api/agent/heartbeat?token="+token, agentMachineContext()); err != nil {
		logf("auth/connectivity failed: %v", err)
		if onStatus != nil {
			onStatus(false)
			return
		}
		os.Exit(2)
	}
	if onStatus != nil {
		onStatus(true)
	}
	logf("online. Émo can now pilot this machine.")

	var wg sync.WaitGroup
	wg.Add(1)
	go heartbeatLoop(ctx, backend, token, &wg, onStatus)

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}
		req, err := pollOnce(backend, token)
		if err != nil {
			debugf("poll error: %v", err)
			select {
			case <-ctx.Done():
				return
			case <-time.After(3 * time.Second):
			}
			continue
		}
		if req == nil {
			continue
		}
		go executeAndPost(backend, token, req)
	}
}

func run(ctx context.Context, backend, token string) {
	runWithStatus(ctx, backend, token, nil)
}

func summarizeArgs(tool string, args map[string]interface{}) string {
	if args == nil {
		return ""
	}
	switch tool {
	case "exec_shell":
		s, _ := args["cmd"].(string)
		return ellipsis(s, 100)
	case "read_file", "list_dir":
		s, _ := args["path"].(string)
		return s
	case "write_file":
		path, _ := args["path"].(string)
		c, _ := args["content"].(string)
		return fmt.Sprintf("%s (%d chars)", path, len(c))
	}
	b, _ := json.Marshal(args)
	return ellipsis(string(b), 100)
}

func summarizeResult(r ToolResult) string {
	if ok, _ := r["ok"].(bool); !ok {
		e, _ := r["error"].(string)
		return "ERROR: " + ellipsis(e, 120)
	}
	if ec, ok := r["exit_code"].(int); ok {
		so, _ := r["stdout"].(string)
		return fmt.Sprintf("exit=%d, out=%dc", ec, len(so))
	}
	if c, ok := r["content"].(string); ok {
		return fmt.Sprintf("read %d chars", len(c))
	}
	if f, ok := r["files"].([]string); ok {
		d, _ := r["dirs"].([]string)
		return fmt.Sprintf("%d files, %d dirs", len(f), len(d))
	}
	return "ok"
}

func ellipsis(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}

// -------------------------- CONFIG --------------------------

func resolveToken(cli string) string {
	if cli != "" {
		return cli
	}
	if e := os.Getenv("EMO_AGENT_TOKEN"); e != "" {
		return e
	}
	// next to the binary
	if exe, err := os.Executable(); err == nil {
		dir := filepath.Dir(exe)
		if b, err := os.ReadFile(filepath.Join(dir, "token.txt")); err == nil {
			return strings.TrimSpace(string(b))
		}
	}
	// user home config
	if home, err := os.UserHomeDir(); err == nil {
		if b, err := os.ReadFile(filepath.Join(home, ".emo", "token.txt")); err == nil {
			return strings.TrimSpace(string(b))
		}
	}
	return ""
}

func resolveBackend(cli string) string {
	if cli != "" {
		return strings.TrimRight(cli, "/")
	}
	if e := os.Getenv("EMO_BACKEND_URL"); e != "" {
		return strings.TrimRight(e, "/")
	}
	readBackendFile := func(path string) string {
		b, err := os.ReadFile(path)
		if err != nil {
			return ""
		}
		return strings.TrimSpace(string(b))
	}
	if exe, err := os.Executable(); err == nil {
		if u := readBackendFile(filepath.Join(filepath.Dir(exe), "backend.txt")); u != "" {
			return strings.TrimRight(u, "/")
		}
	}
	if home, err := os.UserHomeDir(); err == nil {
		if u := readBackendFile(filepath.Join(home, ".emo", "backend.txt")); u != "" {
			return strings.TrimRight(u, "/")
		}
		if u := readBackendFile(filepath.Join(appDataDir(), "backend.txt")); u != "" {
			return strings.TrimRight(u, "/")
		}
	}
	return strings.TrimRight(defaultBackend, "/")
}

func main() {
	tokenFlag := flag.String("token", "", "Agent token from Émo (Settings → Agent)")
	backendFlag := flag.String("backend", "", "Backend URL (default: built-in)")
	debugFlag := flag.Bool("debug", false, "Verbose debug logging")
	versionFlag := flag.Bool("version", false, "Print version and exit")
	installFlag := flag.Bool("install", false, "Install to system (copy binary, register auto-start, then run)")
	uninstallFlag := flag.Bool("uninstall", false, "Uninstall (remove auto-start + binary)")
	headlessFlag := flag.Bool("headless", false, "Run agent without permission UI (background)")
	flag.Parse()

	if *versionFlag {
		fmt.Println("emo-agent", version, runtime.GOOS, runtime.GOARCH)
		return
	}

	debugLog = *debugFlag
	unblockSelf()

	if *uninstallFlag {
		uninstallSelf()
		return
	}

	if *installFlag {
		installSelf()
	}

	emb := readEmbeddedConfig()
	backend := resolveBackend(*backendFlag)
	if *backendFlag == "" && emb.Backend != "" {
		backend = strings.TrimRight(emb.Backend, "/")
	}

	token := resolveToken(*tokenFlag)
	if token == "" && emb.Token != "" {
		token = emb.Token
	}

	if *headlessFlag {
	if token == "" {
			fmt.Fprintln(os.Stderr, "[emo-agent] Token requis en mode headless")
		os.Exit(2)
		}
		run(context.Background(), backend, token)
		return
	}

	runGUI(backend, token)
}

// -------------------------- INSTALL --------------------------

func appDataDir() string {
	home, _ := os.UserHomeDir()
	switch runtime.GOOS {
	case "windows":
		if app := os.Getenv("LOCALAPPDATA"); app != "" {
			return filepath.Join(app, "Emo")
		}
		return filepath.Join(home, "AppData", "Local", "Emo")
	case "darwin":
		return filepath.Join(home, "Library", "Application Support", "Emo")
	default:
		return filepath.Join(home, ".local", "share", "emo")
	}
}

func installSelf() {
	exe, err := os.Executable()
	if err != nil {
		logf("install failed: cannot locate self: %v", err)
		os.Exit(3)
	}

	target := appDataDir()
	if err := os.MkdirAll(target, 0755); err != nil {
		logf("install failed: %v", err)
		os.Exit(3)
	}

	// Resolve token from sibling token.txt first (download bundle case)
	exeDir := filepath.Dir(exe)
	siblingToken := filepath.Join(exeDir, "token.txt")
	var tokenData []byte
	if b, err := os.ReadFile(siblingToken); err == nil {
		tokenData = bytes.TrimSpace(b)
	} else if t := os.Getenv("EMO_AGENT_TOKEN"); t != "" {
		tokenData = []byte(t)
	}

	// Copy binary to target dir
	binName := "emo-agent"
	if runtime.GOOS == "windows" {
		binName = "emo-agent.exe"
	}
	targetBin := filepath.Join(target, binName)

	if exe != targetBin {
		src, err := os.Open(exe)
		if err != nil {
			logf("install: cannot read self: %v", err)
			os.Exit(3)
		}
		dst, err := os.OpenFile(targetBin, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0755)
		if err != nil {
			src.Close()
			logf("install: cannot write target: %v", err)
			os.Exit(3)
		}
		if _, err := io.Copy(dst, src); err != nil {
			src.Close()
			dst.Close()
			logf("install: copy failed: %v", err)
			os.Exit(3)
		}
		src.Close()
		dst.Close()
		logf("installed binary → %s", targetBin)
	}

	if len(tokenData) > 0 {
		if err := os.WriteFile(filepath.Join(target, "token.txt"), tokenData, 0600); err != nil {
			logf("install: token write failed: %v", err)
		} else {
			logf("token saved → %s", filepath.Join(target, "token.txt"))
		}
	}

	// Register auto-start
	switch runtime.GOOS {
	case "windows":
		installWindowsAutostart(targetBin)
	case "darwin":
		installMacAutostart(targetBin)
	default:
		installLinuxAutostart(targetBin)
	}
	logf("install complete. Émo agent démarrera automatiquement à chaque session.")
}

func autostartCommand(binPath string) string {
	return fmt.Sprintf(`"%s" --headless`, binPath)
}

func installWindowsAutostart(binPath string) {
	// Use HKCU\Software\Microsoft\Windows\CurrentVersion\Run registry key
	cmd := exec.Command("reg", "add",
		`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`,
		"/v", "EmoAgent", "/t", "REG_SZ", "/d", autostartCommand(binPath), "/f")
	if err := cmd.Run(); err != nil {
		logf("autostart registry failed (you can add manually): %v", err)
	} else {
		logf("autostart registered in HKCU Run")
	}
}

func installMacAutostart(binPath string) {
	home, _ := os.UserHomeDir()
	plistDir := filepath.Join(home, "Library", "LaunchAgents")
	os.MkdirAll(plistDir, 0755)
	plistPath := filepath.Join(plistDir, "com.emo.agent.plist")
	plist := fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.emo.agent</string>
<key>ProgramArguments</key><array><string>%s</string><string>--headless</string></array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>/tmp/emo-agent.out.log</string>
<key>StandardErrorPath</key><string>/tmp/emo-agent.err.log</string>
</dict></plist>`, binPath)
	if err := os.WriteFile(plistPath, []byte(plist), 0644); err != nil {
		logf("plist write failed: %v", err)
		return
	}
	exec.Command("launchctl", "unload", plistPath).Run()
	if err := exec.Command("launchctl", "load", plistPath).Run(); err != nil {
		logf("launchctl load failed: %v", err)
	} else {
		logf("LaunchAgent loaded: %s", plistPath)
	}
}

func installLinuxAutostart(binPath string) {
	home, _ := os.UserHomeDir()
	unitDir := filepath.Join(home, ".config", "systemd", "user")
	os.MkdirAll(unitDir, 0755)
	unitPath := filepath.Join(unitDir, "emo-agent.service")
	unit := fmt.Sprintf(`[Unit]
Description=Emo local agent
After=network.target

[Service]
Type=simple
ExecStart=%s --headless
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
`, binPath)
	if err := os.WriteFile(unitPath, []byte(unit), 0644); err != nil {
		logf("unit write failed: %v", err)
		return
	}
	exec.Command("systemctl", "--user", "daemon-reload").Run()
	exec.Command("systemctl", "--user", "enable", "emo-agent.service").Run()
	exec.Command("systemctl", "--user", "start", "emo-agent.service").Run()
	logf("systemd user unit installed: %s", unitPath)
}

func uninstallSelf() {
	switch runtime.GOOS {
	case "windows":
		exec.Command("reg", "delete", `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, "/v", "EmoAgent", "/f").Run()
	case "darwin":
		home, _ := os.UserHomeDir()
		plistPath := filepath.Join(home, "Library", "LaunchAgents", "com.emo.agent.plist")
		exec.Command("launchctl", "unload", plistPath).Run()
		os.Remove(plistPath)
	default:
		exec.Command("systemctl", "--user", "stop", "emo-agent.service").Run()
		exec.Command("systemctl", "--user", "disable", "emo-agent.service").Run()
		home, _ := os.UserHomeDir()
		os.Remove(filepath.Join(home, ".config", "systemd", "user", "emo-agent.service"))
	}
	target := appDataDir()
	os.RemoveAll(target)
	logf("uninstalled.")
}
