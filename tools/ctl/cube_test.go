package main

import (
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

func TestRenderCubeFitsInsideGrid(t *testing.T) {
	// Every border cell should stay blank at any orientation — the scale is
	// meant to keep even the furthest corner inside.
	for i := 0; i < 12; i++ {
		ang := [3]float64{float64(i) * 0.5, float64(i) * 0.31, float64(i) * 0.17}
		lines := renderCube(60, 25, ang, true)
		for y, l := range lines {
			if (y == 0 || y == len(lines)-1) && strings.TrimSpace(l) != "" {
				t.Fatalf("ang %v: drew on border row %d", ang, y)
			}
			r := []rune(l)
			if r[0] != ' ' || r[len(r)-1] != ' ' {
				t.Fatalf("ang %v: drew on border column of row %d", ang, y)
			}
		}
	}
}

func TestRenderCubeWireframeOverlays(t *testing.T) {
	ang := [3]float64{0.6, 0.4, 0.2}
	plain := strings.Join(renderCube(50, 25, ang, false), "\n")
	wired := strings.Join(renderCube(50, 25, ang, true), "\n")
	if strings.ContainsRune(plain, cubeWire) {
		t.Fatal("wire char leaked into the shaded-only render")
	}
	if !strings.ContainsRune(wired, cubeWire) {
		t.Fatal("wireframe drew no edges")
	}
	if !strings.ContainsAny(wired, cubeRamp) {
		t.Fatal("wireframe replaced the shading instead of overlaying it")
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
	c := newCubeModel(1)
	start := c.ang
	for i := 0; i < 30; i++ {
		c.step()
	}
	if c.ang == start {
		t.Fatal("angles never moved")
	}
}

func TestCubeModelSpinDrifts(t *testing.T) {
	c := newCubeModel(7)
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
	a, b := newCubeModel(42), newCubeModel(42)
	for i := 0; i < 200; i++ {
		a.step()
		b.step()
	}
	if a.ang != b.ang {
		t.Fatalf("same seed diverged: %v vs %v", a.ang, b.ang)
	}
}
