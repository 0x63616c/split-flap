package main

import (
	"fmt"
	"os"
)

func runCad(args []string) error {
	// just's `cad cmd=""` default passes an empty string — treat as no args
	if len(args) == 0 || args[0] == "" {
		return runCadMenu()
	}
	switch args[0] {
	case "list", "export":
		root, err := repoRoot()
		if err != nil {
			return err
		}
		cmd := pyCmd(root, args...)
		cmd.Stdout, cmd.Stderr, cmd.Stdin = os.Stdout, os.Stderr, os.Stdin
		return cmd.Run()
	case "view":
		model := ""
		if len(args) > 1 {
			model = args[1]
		}
		return runView(model)
	default:
		return fmt.Errorf("unknown cad command %q (have: view, export, list)", args[0])
	}
}
