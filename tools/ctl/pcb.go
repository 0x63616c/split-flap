package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// The driver board lives in one atopile project; everything here is relative
// to it. Placement/routing is python (tools/place_and_render.py), and DRC,
// renders, gerbers and the GLB all come from kicad-cli.

const kicadCLIPath = "/Applications/KiCad.app/Contents/MacOS/kicad-cli"

func pcbDir(root string) string { return filepath.Join(root, "pcb", "driver-board") }

func pcbFile(root string) string {
	return filepath.Join(pcbDir(root), "layouts", "default", "default.kicad_pcb")
}

// kicadCLI prefers the app bundle (the cask half-installs — the binary is
// there but never gets symlinked onto PATH), then falls back to PATH.
func kicadCLI() (string, error) {
	if _, err := os.Stat(kicadCLIPath); err == nil {
		return kicadCLIPath, nil
	}
	if p, err := exec.LookPath("kicad-cli"); err == nil {
		return p, nil
	}
	return "", fmt.Errorf("kicad-cli not found — install with: brew install --cask kicad")
}

// pcbBuild runs the one-shot script: place -> DRC -> renders -> gerbers.
// quick stops after DRC, skipping the raytracer.
func pcbBuild(root string, quick bool) *exec.Cmd {
	args := []string{}
	if quick {
		args = append(args, "--quick")
	}
	cmd := exec.Command(filepath.Join(pcbDir(root), "tools", "build_outputs.sh"), args...)
	cmd.Dir = pcbDir(root)
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	return cmd
}

// pcbPlace re-runs placement/routing only — the fast inner loop, no kicad.
func pcbPlace(root string) *exec.Cmd {
	cmd := exec.Command(atoPython(), filepath.Join(pcbDir(root), "tools", "place_and_render.py"))
	cmd.Dir = pcbDir(root)
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	return cmd
}

// atoPython is atopile's interpreter — it bundles faebryk, which owns the
// kicad file format reader/writer the placement script uses.
func atoPython() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return "python3"
	}
	return filepath.Join(home, ".local", "share", "uv", "tools", "atopile", "bin", "python")
}

// exportGLB writes the board as binary glTF for the 3D viewer.
func exportGLB(root, dest string) error {
	cli, err := kicadCLI()
	if err != nil {
		return err
	}
	out, err := exec.Command(cli, "pcb", "export", "glb",
		"-o", dest, "--include-tracks", "--include-pads", "--include-zones",
		"--subst-models", pcbFile(root)).CombinedOutput()
	if err != nil {
		return fmt.Errorf("glb export: %v — %s", err, out)
	}
	return nil
}

func runPcb(args []string) error {
	// just's `pcb cmd=""` default passes an empty string — treat as no args
	if len(args) == 0 || args[0] == "" {
		return runPcbMenu()
	}
	root, err := repoRoot()
	if err != nil {
		return err
	}
	passthru := func(cmd *exec.Cmd) error {
		cmd.Stdout, cmd.Stderr, cmd.Stdin = os.Stdout, os.Stderr, os.Stdin
		return cmd.Run()
	}
	switch args[0] {
	case "view":
		return runPcbView()
	case "build":
		return passthru(pcbBuild(root, false))
	case "drc":
		return passthru(pcbBuild(root, true))
	case "place":
		return passthru(pcbPlace(root))
	default:
		return fmt.Errorf("unknown pcb command %q (have: view, build, drc, place)", args[0])
	}
}
