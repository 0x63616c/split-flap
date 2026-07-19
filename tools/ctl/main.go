// ctl — split-flap project tooling. Bare run = TUI menu; namespaced args
// (e.g. `ctl cad view holder`) run directly. Go orchestrates only; all CAD
// geometry work happens in python via `uv run --project cad`.
package main

import (
	"fmt"
	"os"
)

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		if err := runRootMenu(); err != nil {
			fmt.Fprintln(os.Stderr, "ctl:", err)
			os.Exit(1)
		}
		return
	}
	var err error
	switch args[0] {
	case "cad":
		err = runCad(args[1:])
	case "pcb":
		err = runPcb(args[1:])
	case "bench":
		err = runBenchCLI(args[1:])
	default:
		err = fmt.Errorf("unknown namespace %q (have: cad, pcb, bench)", args[0])
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "ctl:", err)
		os.Exit(1)
	}
}
