package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

func defaultPrinterName() string {
	if runtime.GOOS != "windows" {
		return ""
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "powershell", "-NoProfile", "-Command",
		"(Get-CimInstance Win32_Printer | Where-Object {$_.Default -eq $true}).Name")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}

func findAcrobat() string {
	candidates := []string{
		filepath.Join(os.Getenv("ProgramFiles"), "Adobe", "Acrobat DC", "Acrobat", "Acrobat.exe"),
		filepath.Join(os.Getenv("ProgramFiles(x86)"), "Adobe", "Acrobat Reader DC", "Reader", "AcroRd32.exe"),
		filepath.Join(os.Getenv("ProgramFiles"), "Adobe", "Acrobat Reader DC", "Reader", "AcroRd32.exe"),
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}
	return ""
}

func toolPrintFile(args map[string]interface{}) ToolResult {
	path, _ := args["path"].(string)
	printer, _ := args["printer"].(string)
	copies := 1
	if c, ok := args["copies"].(float64); ok && c > 0 {
		copies = int(c)
	}
	if path == "" {
		return ToolResult{"ok": false, "error": "path required"}
	}
	p := expand(path)
	abs, _ := filepath.Abs(p)
	if st, err := os.Stat(abs); err != nil || st.IsDir() {
		return ToolResult{"ok": false, "error": "file not found: " + abs}
	}
	if printer == "" {
		printer = defaultPrinterName()
	}
	if printer == "" && runtime.GOOS == "windows" {
		return ToolResult{"ok": false, "error": "no default printer found"}
	}

	for i := 0; i < copies; i++ {
		if err := printFileOnce(abs, printer); err != nil {
			return ToolResult{"ok": false, "error": err.Error(), "path": abs, "printer": printer}
		}
	}
	return ToolResult{"ok": true, "path": abs, "printer": printer, "copies": copies}
}

func printFileOnce(abs, printer string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	switch runtime.GOOS {
	case "windows":
		ext := strings.ToLower(filepath.Ext(abs))
		if ext == ".pdf" {
			acrobat := findAcrobat()
			if acrobat == "" {
				return fmt.Errorf("Adobe Acrobat/Reader required to print PDF")
			}
			cmd := exec.CommandContext(ctx, acrobat, "/t", abs, printer)
			if err := cmd.Start(); err != nil {
				return err
			}
			return nil
		}
		ps := fmt.Sprintf("Start-Process -FilePath %q -Verb Print", abs)
		cmd := exec.CommandContext(ctx, "powershell", "-NoProfile", "-Command", ps)
		return cmd.Run()
	default:
		args := []string{}
		if printer != "" {
			args = append(args, "-d", printer)
		}
		args = append(args, abs)
		cmd := exec.CommandContext(ctx, "lp", args...)
		out, err := cmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("%s: %s", err, strings.TrimSpace(string(out)))
		}
		return nil
	}
}
