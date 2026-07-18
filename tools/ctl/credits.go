package main

import (
	"math"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// The credits screen is a Star Wars crawl: text lying on a plane that runs
// away from the camera, so lines enter full-width at the bottom, shrink and
// pale as they climb, and vanish at the horizon.

const (
	creditsFPS     = 20
	creditsSpacing = 0.13  // gap between lines in plane units
	creditsSpeed   = 0.007 // plane units per frame
	creditsNear    = 1.0   // depth of the bottom row
)

// creditsFade is the yellow the crawl burns through as it recedes: hot at the
// bottom, ember at the horizon. Index by how far up the plane a line has got.
var creditsFade = []lipgloss.Color{"229", "228", "227", "226", "220", "214", "208", "172", "136", "94", "58"}

var creditsText = []string{
	"SPLIT-FLAP",
	"",
	"a departure board that nobody asked for",
	"",
	"",
	"Episode I",
	"",
	"THE PROTOTYPE MENACE",
	"",
	"",
	"It is a period of civil engineering.",
	"A lone maker, striking from a desk",
	"in a spare room, has won its first",
	"victory against the flat, silent",
	"screens of the Empire.",
	"",
	"During the battle, a 28BYJ-48 stepper",
	"managed to steal secret plans to the",
	"Empire's ultimate weapon: a display",
	"that makes a NOISE when it changes.",
	"",
	"",
	"CAST",
	"",
	"the drum . . . . . . . 40 flaps, one seam",
	"the hall sensor . . . . knows where home is",
	"the stepper . . . . . . 4096 steps, no complaints",
	"the ULN2003 . . . . . . does the shouting",
	"the ESP8266 . . . . . . holds the plan",
	"",
	"",
	"BUILT WITH",
	"",
	"build123d . . . . . . . geometry, in python",
	"micropython . . . . . . firmware, on a board",
	"go + bubbletea . . . . this very menu",
	"atopile . . . . . . . . a PCB, described in text",
	"",
	"",
	"NO VENDOR GEOMETRY WAS HARMED",
	"IN THE MAKING OF THIS MODULE",
	"",
	"",
	"",
	"may the flaps be with you",
	"",
	"",
	"",
}

type creditsModel struct {
	t      float64 // how far the crawl has travelled up the plane
	paused bool
	lines  []string
}

func newCreditsModel() *creditsModel {
	return &creditsModel{lines: creditsText}
}

// span is how far the crawl must travel before the last line has receded past
// the horizon: the length of the block, plus enough run-out that the tail
// shrinks to nothing on any sane terminal height.
func (c *creditsModel) span() float64 {
	return float64(len(c.lines))*creditsSpacing + 40*creditsNear
}

func (c *creditsModel) step() {
	if c.paused {
		return
	}
	c.t += creditsSpeed
	if c.t > c.span() {
		c.t = 0 // loop, so the crawl never just stops on a blank field
	}
}

// render draws the crawl into a w×h grid. Line i sits at depth
// d = near + t - i*spacing: it arrives at the bottom of the screen when
// t reaches i*spacing and recedes from there, so the whole block marches
// away from the camera rather than toward it.
//
// Screen row is horizon + (h-1)*near/d, so d == near lands on the bottom row
// and d → ∞ collapses onto the horizon. Width tapers off the same scale,
// which is what makes the block narrow as it climbs.
func (c *creditsModel) render(w, h int) []string {
	if w < 8 {
		w = 8
	}
	if h < 3 {
		h = 3
	}
	grid := make([][]rune, h)
	depth := make([]float64, h) // depth of whatever landed on each row, for colour
	for y := range grid {
		grid[y] = []rune(strings.Repeat(" ", w))
		depth[y] = -1
	}
	centre := w / 2

	// Farthest first (lowest index has been travelling longest), so nearer
	// lines win any row they collide on — text piles up at the horizon and
	// the front of the crawl stays legible.
	for i, text := range c.lines {
		if strings.TrimSpace(text) == "" {
			continue
		}
		d := creditsNear + c.t - float64(i)*creditsSpacing
		if d < creditsNear {
			continue // hasn't reached the bottom of the screen yet
		}
		s := creditsNear / d
		row := int(math.Round(float64(h-1) * s))
		// Taper the width more gently than the height (sqrt of the true
		// perspective scale). Honest 1/d horizontally decimates a line into
		// confetti within a second of it entering; this keeps it readable
		// for the climb and still narrows the block toward the horizon.
		s = math.Sqrt(s)
		if row < 1 || row >= h {
			continue // row 0 is the horizon itself: nothing readable lands there
		}
		// Sample destination → source: squeezing by mapping each source
		// char to a column drops whichever letters collide, which reads as
		// noise. Picking one source char per output column decimates the
		// line evenly instead, so distant text still looks like text.
		rs := []rune(text)
		span := int(math.Round(float64(len(rs)) * s))
		if span < 1 {
			continue
		}
		left := centre - span/2
		for k := 0; k < span; k++ {
			j := k * len(rs) / span
			r := rs[j]
			col := left + k
			if r == ' ' || col < 0 || col >= w {
				continue
			}
			grid[row][col] = r
		}
		depth[row] = d
	}

	out := make([]string, h)
	for y, rowRunes := range grid {
		line := strings.TrimRight(string(rowRunes), " ")
		if line == "" || depth[y] < 0 {
			out[y] = ""
			continue
		}
		out[y] = lipgloss.NewStyle().Foreground(creditsShade(depth[y])).Render(line)
	}
	return out
}

// creditsShade picks a colour off the fade ramp by depth — one step per two
// line-gaps, so the ramp spans roughly the visible crawl.
func creditsShade(d float64) lipgloss.Color {
	i := int((d - creditsNear) / (creditsSpacing * 5))
	if i < 0 {
		i = 0
	}
	if i >= len(creditsFade) {
		i = len(creditsFade) - 1
	}
	return creditsFade[i]
}
