//go:build windows

package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Retire le blocage "fichier téléchargé depuis Internet" (Zone.Identifier).
func unblockSelf() {
	exe, err := os.Executable()
	if err != nil {
		return
	}
	exe, err = filepath.EvalSymlinks(exe)
	if err != nil {
		exe, _ = filepath.Abs(exe)
	}
	safe := strings.ReplaceAll(exe, "'", "''")
	cmd := exec.Command(
		"powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
		"Unblock-File -LiteralPath '"+safe+"' -ErrorAction SilentlyContinue",
	)
	_ = cmd.Run()
}
