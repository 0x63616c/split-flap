package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// repoRoot walks up from cwd to the directory containing `justfile`.
func repoRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "justfile")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("not inside the split-flap repo (no justfile found)")
		}
		dir = parent
	}
}

// pyCmd builds a splitflap_cad CLI invocation rooted at the repo.
func pyCmd(root string, args ...string) *exec.Cmd {
	full := append([]string{"run", "--project", "cad", "python", "-m", "splitflap_cad"}, args...)
	cmd := exec.Command("uv", full...)
	cmd.Dir = root
	// output often lands in a pipe (TUI run screen) — keep it line-by-line
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	return cmd
}

type catalog struct {
	Models     map[string]string `json:"models"`
	Printable  []string          `json:"printable"`
	SrcToModel map[string]string `json:"src_to_model"`
}

func parseCatalog(data []byte) (catalog, error) {
	var c catalog
	if err := json.Unmarshal(data, &c); err != nil {
		return c, fmt.Errorf("parse model catalog: %w", err)
	}
	return c, nil
}

func loadCatalog(root string) (catalog, error) {
	out, err := pyCmd(root, "list", "--json").Output()
	if err != nil {
		return catalog{}, fmt.Errorf("load model catalog: %w", err)
	}
	return parseCatalog(out)
}
