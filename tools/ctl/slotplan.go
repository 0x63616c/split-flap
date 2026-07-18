package main

// Split-flap slot planner — the portable maths behind the bench screen.
//
// Pure functions, no I/O, no serial, no terminal. The bench TUI calls into
// this; nothing flows the other way. Lift it into the real firmware once the
// model feels right.
//
// The awkward number that makes this non-trivial:
//
//	4096 half-steps / rev  /  45 slots  =  91.02...  steps/slot   (NOT integer)
//
// So a slot boundary almost never lands on a whole step. Two ways to cope:
//
//   - move RELATIVE, slot-by-slot, rounding each hop -> error accumulates, the
//     drum walks off over many moves.
//   - always compute the ABSOLUTE target step from home -> rounding is bounded
//     to +/-0.5 slot forever, never accumulates.  <-- we do this.
//
// Even so the gear train slips, so per the conventions decision (#3) the drum
// re-homes on the hall magnet and snaps its step counter back to 0. That
// resync is modelled here as a pure fact (home is step 0); the shell decides
// when to actually re-home.
//
// 28BYJ-48 is driven forward-only (reversing loses steps to backlash), so a
// move is always the forward distance around the ring, mod one rev.

import (
	"fmt"
	"math"
	"strings"
)

// benchGlyphs is the David Kingsman drum order, non-umlaut variant: blank,
// A-Z, $ & #, 0-9, : . - ? ! ($ & # take the umlaut slots.) This is the FIXED
// physical flap order round the drum — the sequence the window shows as the
// drum turns forward.
const benchGlyphs = " ABCDEFGHIJKLMNOPQRSTUVWXYZ$&#0123456789:.-?!"

const (
	nSlots      = len(benchGlyphs) // 45
	stepsPerRev = 4096             // 28BYJ-48 half-step, matches the spike firmware
	blank       = ' '
)

// offDrum are chars the UI lets you type that are NOT on this drum. '$' '#'
// '.' ARE on it now; only '£' stays off.
const offDrum = "£"

// errNotOnDrum reports a typed glyph that is valid input but has no slot on
// the current 45-slot drum.
type errNotOnDrum struct{ ch rune }

func (e errNotOnDrum) Error() string {
	return fmt.Sprintf("'%c' not on the %d-slot drum", e.ch, nSlots)
}

// drum holds the one per-module fact the maths needs: WHICH flap the hall
// magnet sits opposite, i.e. which glyph the drum shows at home (step 0). Set
// by assembly, not software — so you declare it (setHomeGlyph). Everything the
// module plans is measured in "slots forward from home", so this one number
// rotates the whole glyph<->slot mapping without moving the motor.
type drum struct {
	homeIndex int
}

// normalise folds user input to a drum glyph: upper-case; 0 / '_' mean blank.
func normalise(ch rune) rune {
	if ch == 0 || ch == '_' || ch == ' ' {
		return blank
	}
	return []rune(strings.ToUpper(string(ch)))[0]
}

// index resolves a glyph to its position in benchGlyphs (the physical flap
// order), or errNotOnDrum.
func index(ch rune) (int, error) {
	g := normalise(ch)
	if strings.ContainsRune(offDrum, g) {
		return 0, errNotOnDrum{g}
	}
	i := strings.IndexRune(benchGlyphs, g)
	if i < 0 {
		return 0, errNotOnDrum{ch}
	}
	return i, nil
}

// setHomeGlyph declares which glyph the drum shows when homed. Rotates the
// whole glyph<->slot mapping; moves no motor. Returns the normalised glyph.
func (d *drum) setHomeGlyph(ch rune) (rune, error) {
	i, err := index(ch)
	if err != nil {
		return 0, err
	}
	d.homeIndex = i
	return rune(benchGlyphs[i]), nil
}

func (d *drum) homeGlyph() rune { return rune(benchGlyphs[d.homeIndex]) }

// glyphToSlot maps a glyph char to a slot index (slots FORWARD FROM HOME).
func (d *drum) glyphToSlot(ch rune) (int, error) {
	i, err := index(ch)
	if err != nil {
		return 0, err
	}
	return ((i-d.homeIndex)%nSlots + nSlots) % nSlots, nil
}

// slotToGlyph maps a slot (slots forward from home) to the glyph now in the
// window.
func (d *drum) slotToGlyph(slot int) rune {
	return rune(benchGlyphs[((slot+d.homeIndex)%nSlots+nSlots)%nSlots])
}

// targetStep is the absolute half-step from home for a slot's centre (bounded
// rounding).
func targetStep(slot int) int {
	return int(math.Round(float64(slot)*stepsPerRev/float64(nSlots))) % stepsPerRev
}

// forwardSteps is the forward-only distance (half-steps) from cur to tgt, mod
// one rev.
func forwardSteps(curStep, tgtStep int) int {
	return ((tgtStep-curStep)%stepsPerRev + stepsPerRev) % stepsPerRev
}

// nearestSlot is which slot the drum is closest to, given an absolute step.
// Exactly one step (2048) sits dead between two slots; we round it up. (The
// python original rounded it down — banker's rounding — but the drum is
// mid-flap either way, so it only changes which neighbour we name.)
func nearestSlot(curStep int) int {
	return int(math.Round(float64(curStep)*float64(nSlots)/stepsPerRev)) % nSlots
}

// plan works out a move to glyph ch from absolute position curStep.
//
// crossesHome is true when the forward path passes step 0 — a chance to
// re-home and resync the counter mid-move.
func (d *drum) plan(curStep int, ch rune) (slot, tgt, fwd int, crossesHome bool, err error) {
	slot, err = d.glyphToSlot(ch)
	if err != nil {
		return 0, 0, 0, false, err
	}
	tgt = targetStep(slot)
	fwd = forwardSteps(curStep, tgt)
	crossesHome = curStep != 0 && curStep+fwd >= stepsPerRev
	return slot, tgt, fwd, crossesHome, nil
}
