package main

import "testing"

// Golden slot/step pairs lifted from the python planner this replaces.
func TestGlyphToSlotAndTargetStep(t *testing.T) {
	var d drum
	for _, tc := range []struct {
		ch         rune
		slot, step int
	}{
		{' ', 0, 0},
		{'A', 1, 91},
		{'Z', 26, 2367},
		{'$', 27, 2458},
		{'0', 30, 2731},
		{'9', 39, 3550},
		{'!', 44, 4005},
		{'a', 1, 91}, // lower-case folds up
		{'_', 0, 0},  // underscore is blank
	} {
		slot, err := d.glyphToSlot(tc.ch)
		if err != nil {
			t.Fatalf("%q: %v", tc.ch, err)
		}
		if slot != tc.slot {
			t.Errorf("%q: slot %d, want %d", tc.ch, slot, tc.slot)
		}
		if got := targetStep(slot); got != tc.step {
			t.Errorf("%q: step %d, want %d", tc.ch, got, tc.step)
		}
	}
}

// Rounding is bounded to ±0.5 slot for every slot — the whole reason we target
// absolute steps rather than hopping slot-by-slot.
func TestTargetStepRoundingBounded(t *testing.T) {
	const half = float64(stepsPerRev) / float64(nSlots) / 2
	for slot := 0; slot < nSlots; slot++ {
		ideal := float64(slot) * stepsPerRev / float64(nSlots)
		if drift := float64(targetStep(slot)) - ideal; drift > half || drift < -half {
			t.Errorf("slot %d: drift %.2f exceeds ±%.2f", slot, drift, half)
		}
	}
}

// nearestSlot is targetStep's inverse: every slot's centre must map back.
func TestNearestSlotRoundTrips(t *testing.T) {
	for slot := 0; slot < nSlots; slot++ {
		if got := nearestSlot(targetStep(slot)); got != slot {
			t.Errorf("slot %d -> step %d -> slot %d", slot, targetStep(slot), got)
		}
	}
	if got := nearestSlot(2048); got != 23 { // the one exact-half step, rounds up
		t.Errorf("nearestSlot(2048) = %d, want 23", got)
	}
}

// Declaring the home glyph rotates the whole map without moving anything.
func TestSetHomeGlyphRotatesTheMap(t *testing.T) {
	var d drum
	g, err := d.setHomeGlyph('2')
	if err != nil {
		t.Fatal(err)
	}
	if g != '2' || d.homeGlyph() != '2' {
		t.Fatalf("home glyph %q", g)
	}
	if d.slotToGlyph(0) != '2' {
		t.Errorf("slot 0 shows %q, want '2'", d.slotToGlyph(0))
	}
	for _, tc := range []struct {
		ch   rune
		slot int
	}{{' ', 13}, {'A', 14}, {'2', 0}, {'!', 12}} {
		slot, err := d.glyphToSlot(tc.ch)
		if err != nil {
			t.Fatal(err)
		}
		if slot != tc.slot {
			t.Errorf("%q: slot %d, want %d", tc.ch, slot, tc.slot)
		}
		if back := d.slotToGlyph(slot); back != normalise(tc.ch) {
			t.Errorf("%q round-tripped to %q", tc.ch, back)
		}
	}
}

func TestForwardStepsIsForwardOnly(t *testing.T) {
	if got := forwardSteps(4000, 91); got != 187 { // wraps the long way round
		t.Errorf("forwardSteps(4000, 91) = %d, want 187", got)
	}
	if got := forwardSteps(91, 4000); got != 3909 {
		t.Errorf("forwardSteps(91, 4000) = %d, want 3909", got)
	}
	if got := forwardSteps(91, 91); got != 0 {
		t.Errorf("forwardSteps(91, 91) = %d, want 0", got)
	}
}

func TestPlanFlagsHomeCrossing(t *testing.T) {
	var d drum
	if _, err := d.setHomeGlyph('2'); err != nil {
		t.Fatal(err)
	}
	slot, tgt, fwd, crosses, err := d.plan(4000, 'A')
	if err != nil {
		t.Fatal(err)
	}
	if slot != 14 || tgt != 1274 || fwd != 1370 || !crosses {
		t.Errorf("plan(4000,'A') = %d %d %d %v, want 14 1274 1370 true", slot, tgt, fwd, crosses)
	}
	// Sitting on home already: the move can't "cross" what it starts on.
	if _, _, _, crosses, _ := d.plan(0, ' '); crosses {
		t.Error("plan from step 0 reported a home crossing")
	}
	if _, _, fwd, crosses, _ := d.plan(100, ' '); crosses || fwd != 1083 {
		t.Errorf("plan(100,' ') fwd %d crosses %v, want 1083 false", fwd, crosses)
	}
}

func TestOffDrumGlyphRejected(t *testing.T) {
	var d drum
	if _, err := d.glyphToSlot('£'); err == nil {
		t.Error("'£' accepted, want errNotOnDrum")
	}
	if _, err := d.setHomeGlyph('~'); err == nil {
		t.Error("'~' accepted as a home glyph")
	}
}
