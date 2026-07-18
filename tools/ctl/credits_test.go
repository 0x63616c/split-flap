package main

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

// stripANSI drops the colour escapes so a rendered row can be compared as text.
func stripANSI(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		if s[i] == 0x1b {
			for i < len(s) && s[i] != 'm' {
				i++
			}
			continue
		}
		b.WriteByte(s[i])
	}
	return b.String()
}

// The first line lands on the bottom row at t == 0 and is still full width
// there — the crawl opens legible, then recedes.
func TestCreditsFirstLineEntersFullWidth(t *testing.T) {
	c := newCreditsModel()
	rows := c.render(80, 20)
	got := strings.TrimSpace(stripANSI(rows[19]))
	if want := strings.TrimSpace(creditsText[0]); got != want {
		t.Errorf("bottom row = %q, want %q", got, want)
	}
	for _, r := range rows[:19] {
		if strings.TrimSpace(stripANSI(r)) != "" {
			t.Errorf("row above the entry point is not empty: %q", stripANSI(r))
		}
	}
}

// Lines climb toward the horizon and narrow as they go.
func TestCreditsRecedes(t *testing.T) {
	c := newCreditsModel()
	rowOf := func() (row, width int) {
		row = -1
		for y, r := range c.render(80, 20) {
			if w := len(strings.TrimSpace(stripANSI(r))); w > 0 {
				row, width = y, w
				break
			}
		}
		return
	}
	c.t = 0
	row0, w0 := rowOf()
	c.t = 2
	row1, w1 := rowOf()
	if row1 >= row0 {
		t.Errorf("line did not climb: row %d → %d", row0, row1)
	}
	if w1 >= w0 {
		t.Errorf("line did not narrow: width %d → %d", w0, w1)
	}
}

// The crawl loops rather than running off into an empty field forever.
func TestCreditsLoops(t *testing.T) {
	c := newCreditsModel()
	c.t = c.span()
	c.step()
	if c.t != 0 {
		t.Errorf("t = %v after passing the span, want 0", c.t)
	}
}

func TestCreditsPauseAndRewind(t *testing.T) {
	m := &appModel{root: ".", stack: []screen{rootScreen()}}
	m.startCredits()
	if m.top().id != "credits" {
		t.Fatalf("top screen = %q, want credits", m.top().id)
	}
	m.credits.t = 5
	m.creditsKey(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("p")})
	if !m.credits.paused {
		t.Error("p did not pause the crawl")
	}
	m.credits.step()
	if m.credits.t != 5 {
		t.Errorf("a paused crawl advanced to %v", m.credits.t)
	}
	m.creditsKey(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("r")})
	if m.credits.t != 0 {
		t.Errorf("r did not rewind: t = %v", m.credits.t)
	}
	m.creditsKey(tea.KeyMsg{Type: tea.KeyEsc})
	if m.credits != nil || m.top().id != "root" {
		t.Error("esc did not drop back to the menu")
	}
}
