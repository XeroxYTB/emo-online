package main

import (
	"encoding/json"
	"os"
	"path/filepath"
)

type Permissions struct {
	AllowShell  bool `json:"allow_shell"`
	AllowRead   bool `json:"allow_read"`
	AllowWrite  bool `json:"allow_write"`
	AllowDelete bool `json:"allow_delete"`
	AllowGrep   bool `json:"allow_grep"`
	Enabled     bool `json:"enabled"`
}

func defaultPermissions() Permissions {
	return Permissions{
		AllowShell:  true,
		AllowRead:   true,
		AllowWrite:  false,
		AllowDelete: false,
		AllowGrep:   true,
		Enabled:     true,
	}
}

func permissionsPath() string {
	return filepath.Join(appDataDir(), "permissions.json")
}

func loadPermissions() Permissions {
	p := defaultPermissions()
	b, err := os.ReadFile(permissionsPath())
	if err != nil {
		return p
	}
	_ = json.Unmarshal(b, &p)
	if !p.Enabled {
		p = defaultPermissions()
		p.Enabled = false
	}
	return p
}

func savePermissions(p Permissions) error {
	if err := os.MkdirAll(appDataDir(), 0755); err != nil {
		return err
	}
	b, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(permissionsPath(), b, 0600)
}

func (p Permissions) allowsTool(tool string) bool {
	if !p.Enabled {
		return false
	}
	switch tool {
	case "exec_shell", "run_terminal_cmd", "bash", "shell":
		return p.AllowShell
	case "read_file", "list_dir", "find_files", "codebase_search", "file_search",
		"file_info", "get_env", "system_info", "git_status", "git_diff":
		return p.AllowRead
	case "write_file", "edit_file", "move_path", "append_file", "create_dir",
		"copy_path", "apply_patch", "download_url", "create_file":
		return p.AllowWrite
	case "delete_path":
		return p.AllowDelete
	case "grep", "search":
		return p.AllowGrep || p.AllowRead
	default:
		return p.AllowRead
	}
}
