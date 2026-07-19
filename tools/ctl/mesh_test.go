package main

import (
	"encoding/binary"
	"math"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// writeSTL builds a binary STL from triangles, for tests that need a mesh of
// known shape rather than whatever cad/export/ happens to hold.
func writeSTL(t *testing.T, tris []tri) string {
	t.Helper()
	buf := make([]byte, stlHeader+len(tris)*50)
	binary.LittleEndian.PutUint32(buf[80:], uint32(len(tris)))
	put := func(off int, v float64) {
		binary.LittleEndian.PutUint32(buf[off:], math.Float32bits(float32(v)))
	}
	for i, tr := range tris {
		o := stlHeader + i*50 + 12
		for j, p := range [3][3]float64{tr.a, tr.b, tr.c} {
			for k := 0; k < 3; k++ {
				put(o+j*12+k*4, p[k])
			}
		}
	}
	path := filepath.Join(t.TempDir(), "test.stl")
	if err := os.WriteFile(path, buf, 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

// quad is a flat square facing the camera: wound so the normal comes out
// along -z, which is what "towards the viewer" means here.
func quad(z float64) []tri {
	return []tri{
		{a: [3]float64{-10, -10, z}, b: [3]float64{10, 10, z}, c: [3]float64{10, -10, z}},
		{a: [3]float64{-10, -10, z}, b: [3]float64{-10, 10, z}, c: [3]float64{10, 10, z}},
	}
}

func TestLoadSTLReadsTriangles(t *testing.T) {
	m, err := loadSTL(writeSTL(t, quad(0)))
	if err != nil {
		t.Fatal(err)
	}
	if len(m.tris) != 2 {
		t.Fatalf("got %d triangles, want 2", len(m.tris))
	}
	if m.name != "test" {
		t.Fatalf("name %q, want %q", m.name, "test")
	}
}

// Whatever the source units, the mesh must come out centred at the origin
// with its furthest vertex at radius 1 — that is the contract the canvas
// projection is sized against.
func TestLoadSTLNormalises(t *testing.T) {
	far := []tri{{
		a: [3]float64{1000, 1000, 1000},
		b: [3]float64{1002, 1000, 1000},
		c: [3]float64{1000, 1002, 1000},
	}}
	m, err := loadSTL(writeSTL(t, far))
	if err != nil {
		t.Fatal(err)
	}
	maxR, sum := 0.0, [3]float64{}
	m.each(func(p [3]float64) {
		maxR = math.Max(maxR, math.Sqrt(p[0]*p[0]+p[1]*p[1]+p[2]*p[2]))
		for i := 0; i < 3; i++ {
			sum[i] += p[i]
		}
	})
	if math.Abs(maxR-1) > 1e-6 {
		t.Fatalf("furthest vertex at radius %v, want 1", maxR)
	}
	for i, s := range sum {
		if math.Abs(s/3) > 0.5 {
			t.Fatalf("axis %d not centred: mean %v", i, s/3)
		}
	}
}

func TestLoadSTLRejectsASCII(t *testing.T) {
	path := filepath.Join(t.TempDir(), "a.stl")
	os.WriteFile(path, []byte(strings.Repeat("solid xyz ", 20)), 0o644)
	if _, err := loadSTL(path); err == nil || !strings.Contains(err.Error(), "ASCII") {
		t.Fatalf("want an ASCII-STL error, got %v", err)
	}
}

func TestLoadSTLRejectsTruncated(t *testing.T) {
	path := writeSTL(t, quad(0))
	full, _ := os.ReadFile(path)
	os.WriteFile(path, full[:len(full)-20], 0o644)
	if _, err := loadSTL(path); err == nil {
		t.Fatal("truncated file loaded without error")
	}
}

func TestRenderMeshFillsAndFits(t *testing.T) {
	m, err := loadSTL(writeSTL(t, quad(0)))
	if err != nil {
		t.Fatal(err)
	}
	lines := renderMesh(m, 60, 25, [3]float64{}, 1, false)
	if len(lines) != 25 {
		t.Fatalf("got %d rows, want 25", len(lines))
	}
	if nonBlank(lines) == 0 {
		t.Fatal("flat quad facing the camera drew nothing")
	}
	for y, l := range lines {
		if (y == 0 || y == len(lines)-1) && strings.TrimSpace(l) != "" {
			t.Fatalf("drew on border row %d", y)
		}
	}
}

// The near surface must win the depth test: two parallel quads, the nearer
// one drawn second, and every filled cell should carry the near depth.
func TestRenderMeshDepthSortsNearestFirst(t *testing.T) {
	tris := append(quad(0.5), quad(-0.5)...) // far first, near second
	m, err := loadSTL(writeSTL(t, tris))
	if err != nil {
		t.Fatal(err)
	}
	// Depths come from the normalised mesh, not the source coordinates —
	// loadSTL rescales, so ±0.5 in the file is not ±0.5 in camera space.
	lo, hi := math.Inf(1), math.Inf(-1)
	m.each(func(p [3]float64) { lo, hi = math.Min(lo, p[2]), math.Max(hi, p[2]) })

	c := renderMeshCanvas(m, 40, 20, [3]float64{}, 1, false)
	near, far := 1/(cubeDist+lo), 1/(cubeDist+hi)
	got := c.depth[(c.h/2)*c.w+c.w/2]
	if math.Abs(got-near) > math.Abs(got-far) {
		t.Fatalf("centre depth %v is the far quad (near %v, far %v)", got, near, far)
	}
}

func TestRenderMeshWireframeDropsFill(t *testing.T) {
	m, err := loadSTL(writeSTL(t, quad(0)))
	if err != nil {
		t.Fatal(err)
	}
	wired := strings.Join(renderMesh(m, 60, 25, [3]float64{0.3, 0.2, 0}, 1, true), "\n")
	if !strings.ContainsRune(wired, cubeWire) {
		t.Fatal("wireframe drew no edges")
	}
	if strings.ContainsAny(wired, cubeRamp) {
		t.Fatal("wireframe still shaded faces")
	}
}

func TestRenderMeshDegenerate(t *testing.T) {
	if got := renderMesh(nil, 40, 20, [3]float64{}, 1, false); got != nil {
		t.Fatalf("nil mesh should render nil, got %v", got)
	}
}

// The real thing: whatever is in cad/export/ must load and draw. Skipped
// when the exports are absent, since they are build output.
func TestRenderRealUnit(t *testing.T) {
	root, err := repoRoot()
	if err != nil {
		t.Skip("not in a repo")
	}
	paths := findSTLs(root)
	if len(paths) == 0 {
		t.Skip("no exports on disk — run: just cad export")
	}
	for _, p := range paths {
		m, err := loadSTL(p)
		if err != nil {
			t.Errorf("%s: %v", filepath.Base(p), err)
			continue
		}
		if len(m.tris) == 0 {
			t.Errorf("%s: no triangles", filepath.Base(p))
			continue
		}
		lines := renderMesh(m, 80, 30, [3]float64{0.6, 0.4, 0.2}, 1, false)
		if n := nonBlank(lines); n < 100 {
			t.Errorf("%s: only %d chars drawn, expected a solid body", filepath.Base(p), n)
		}
	}
}

// A triangle smaller than a single cell must still leave a mark: at mesh
// densities most triangles are sub-cell, and each miss is a pinhole showing
// the inside of the part.
func TestTriangleSubCellStillDraws(t *testing.T) {
	c := newCanvas(40, 20, 1, viewFill)
	tiny := 0.001
	c.triangle([3]float64{0, 0, 0}, [3]float64{tiny, 0, 0}, [3]float64{0, tiny, 0}, '@')
	if nonBlank(c.lines()) == 0 {
		t.Fatal("sub-cell triangle drew nothing")
	}
}
