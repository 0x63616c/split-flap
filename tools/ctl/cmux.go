package main

import (
	"encoding/json"
	"os/exec"
	"regexp"
)

// cmuxCallerPane returns the pane ref this process runs inside, or false
// when cmux is missing/unreachable (view then just prints the URL).
func cmuxCallerPane() (string, bool) {
	out, err := exec.Command("cmux", "identify", "--json").Output()
	if err != nil {
		return "", false
	}
	var id struct {
		Caller struct {
			PaneRef string `json:"pane_ref"`
		} `json:"caller"`
	}
	if json.Unmarshal(out, &id) != nil || id.Caller.PaneRef == "" {
		return "", false
	}
	return id.Caller.PaneRef, true
}

var surfaceRe = regexp.MustCompile(`surface:[0-9]+`)

// cmuxOpenViewerTab adds a focused browser tab to pane (tab 1 stays this
// command's logs, tab 2 becomes the viewer).
func cmuxOpenViewerTab(pane, url string) (string, bool) {
	out, err := exec.Command("cmux", "new-surface", "--type", "browser",
		"--pane", pane, "--url", url, "--focus", "true").Output()
	if err != nil {
		return "", false
	}
	s := surfaceRe.FindString(string(out))
	return s, s != ""
}

func cmuxCloseSurface(surface string) {
	_ = exec.Command("cmux", "close-surface", "--surface", surface).Run()
}

func cmuxNotify(title, body string) {
	_ = exec.Command("cmux", "notify", "--title", title, "--body", body).Run()
}
