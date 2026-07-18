package main

import (
	"math"
	"strings"
	"testing"
)

func nonBlank(lines []string) int {
	n := 0
	for _, l := range lines {
		n += len(strings.TrimSpace(l))
	}
	return n
}

func TestRenderCubeGrid(t *testing.T) {
	lines := renderCube(50, 25, [3]float64{0.6, 0.4, 0.2}, false)
	if len(lines) != 25 {
		t.Fatalf("got %d rows, want 25", len(lines))
	}
	for i, l := range lines {
		if len([]rune(l)) != 50 {
			t.Fatalf("row %d is %d cols, want 50", i, len([]rune(l)))
		}
	}
	if nonBlank(lines) == 0 {
		t.Fatal("nothing drawn")
	}
}

// At fill 1.0 the projection guarantees a fit: no point on the bounding
// sphere can land outside the grid, whatever the orientation.
func TestCanvasFillOneAlwaysFits(t *testing.T) {
	r := cubeHalf * math.Sqrt(3)
	c := newCanvas(60, 25, r, 1.0)
	for i := 0; i < 40; i++ {
		ang := [3]float64{float64(i) * 0.5, float64(i) * 0.31, float64(i) * 0.17}
		for corner := 0; corner < 8; corner++ {
			x, y, _ := c.project(rot(cubeCorner(corner), ang))
			if x < 0 || x > float64(c.w-1) || y < 0 || y > float64(c.h-1) {
				t.Fatalf("ang %v corner %d projected to (%.1f,%.1f), outside %dx%d",
					ang, corner, x, y, c.w, c.h)
			}
		}
	}
}

// The demo trades that guarantee for presence: viewFill draws a quarter
// larger, and the odd clipped corner is the accepted cost.
func TestViewFillDrawsLarger(t *testing.T) {
	r := cubeHalf * math.Sqrt(3)
	fit := newCanvas(60, 25, r, 1.0).scale
	got := newCanvas(60, 25, r, viewFill).scale / fit
	if math.Abs(got-1.25) > 1e-9 {
		t.Fatalf("viewFill scales by %v, want 1.25", got)
	}
}

// Oversizing must clip cleanly rather than corrupt the grid: every row stays
// exactly w wide however far the model overhangs.
func TestRenderCubeClipsCleanly(t *testing.T) {
	for i := 0; i < 12; i++ {
		ang := [3]float64{float64(i) * 0.5, float64(i) * 0.31, float64(i) * 0.17}
		for _, wire := range []bool{false, true} {
			for _, l := range renderCube(60, 25, ang, wire) {
				if len([]rune(l)) != 60 {
					t.Fatalf("ang %v wire %v: row is %d cols, want 60", ang, wire, len([]rune(l)))
				}
			}
		}
	}
}

func TestRenderCubeWireframeDropsFaces(t *testing.T) {
	ang := [3]float64{0.6, 0.4, 0.2}
	plain := strings.Join(renderCube(50, 25, ang, false), "\n")
	wired := strings.Join(renderCube(50, 25, ang, true), "\n")
	if strings.ContainsRune(plain, cubeWire) {
		t.Fatal("wire char leaked into the shaded-only render")
	}
	if !strings.ContainsRune(wired, cubeWire) {
		t.Fatal("wireframe drew no edges")
	}
	if strings.ContainsAny(wired, cubeRamp) {
		t.Fatal("wireframe still shaded faces; it should be edges only")
	}
}

// The skeleton is see-through: at rest the far square sits concentrically
// inside the near one, so the middle row crosses four separate edges. Only
// two would mean the back edges are being occluded.
func TestRenderCubeWireframeShowsBackEdges(t *testing.T) {
	lines := renderCube(60, 25, [3]float64{}, true)
	mid := lines[len(lines)/2]
	runs, in := 0, false
	for _, r := range mid {
		if r == cubeWire && !in {
			runs++
		}
		in = r == cubeWire
	}
	if runs != 4 {
		t.Fatalf("middle row crosses %d edges, want 4 (near pair + far pair): %q", runs, mid)
	}
}

// The centre cell must land on the face nearest the camera, never the far
// one — drawing the far face means we are seeing the inside of the cube.
func TestRenderCubeShowsNearFace(t *testing.T) {
	near, far := 1/(cubeDist-cubeHalf), 1/(cubeDist+cubeHalf)
	for _, ang := range [][3]float64{{}, {0.6, 0.4, 0.2}, {1.1, 0.9, 0.3}, {2.4, 1.7, 0.8}} {
		c := renderCubeCanvas(60, 25, ang, false)
		got := c.depth[(c.h/2)*c.w+c.w/2]
		if got == 0 {
			t.Fatalf("ang %v: centre cell empty", ang)
		}
		if got < (near+far)/2 {
			t.Fatalf("ang %v: centre depth %v is a far-side surface (near %v, far %v)",
				ang, got, near, far)
		}
	}
}

func TestRenderCubeDegenerateSize(t *testing.T) {
	if got := renderCube(0, 10, [3]float64{}, false); got != nil {
		t.Fatalf("want nil for zero width, got %v", got)
	}
}

func TestCubeModelTumbles(t *testing.T) {
	c := newDemoModel(1, "")
	start := c.ang
	for i := 0; i < 30; i++ {
		c.step()
	}
	if c.ang == start {
		t.Fatal("angles never moved")
	}
}

func TestCubeModelSpinDrifts(t *testing.T) {
	c := newDemoModel(7, "")
	first := c.vel
	for i := 0; i < cubeRerollAt*2; i++ {
		c.step()
	}
	if c.vel == first {
		t.Fatal("spin never re-rolled")
	}
	for i, v := range c.vel {
		if v > cubeSpinMax || v < -cubeSpinMax {
			t.Fatalf("axis %d spin %v escaped ±%v", i, v, cubeSpinMax)
		}
	}
}

func TestCubeModelDeterministicFromSeed(t *testing.T) {
	a, b := newDemoModel(42, ""), newDemoModel(42, "")
	for i := 0; i < 200; i++ {
		a.step()
		b.step()
	}
	if a.ang != b.ang {
		t.Fatalf("same seed diverged: %v vs %v", a.ang, b.ang)
	}
}

func TestCubeModelStartsWireframed(t *testing.T) {
	if !newDemoModel(1, "").scene().wire {
		t.Fatal("the cube should open in wireframe")
	}
}
