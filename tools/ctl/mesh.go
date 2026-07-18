package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
)

// Renders an exported STL as ASCII: the real part from cad/export/, tumbling
// in the terminal. Triangles are rasterised into the same depth-buffered
// canvas the cube uses, so hidden surfaces sort themselves out.

type tri struct{ a, b, c [3]float64 }

// mesh holds triangles already normalised to fit inside a unit sphere at the
// origin, so the canvas projection needs no per-model tuning.
type mesh struct {
	name string
	tris []tri
}

const stlHeader = 84 // 80-byte header + uint32 triangle count

// loadSTL reads a binary STL. Normals in the file are ignored — plenty of
// exporters write garbage there, and the winding gives us a better one.
func loadSTL(path string) (*mesh, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var head [stlHeader]byte
	if _, err := io.ReadFull(f, head[:]); err != nil {
		return nil, fmt.Errorf("%s: short header: %w", filepath.Base(path), err)
	}
	if string(head[:5]) == "solid" {
		return nil, fmt.Errorf("%s: ASCII STL, only binary is supported", filepath.Base(path))
	}
	count := binary.LittleEndian.Uint32(head[80:])

	body, err := io.ReadAll(f)
	if err != nil {
		return nil, err
	}
	if want := int(count) * 50; len(body) < want {
		return nil, fmt.Errorf("%s: says %d triangles but has bytes for %d",
			filepath.Base(path), count, len(body)/50)
	}

	m := &mesh{name: stlName(path), tris: make([]tri, count)}
	f32 := func(off int) float64 {
		return float64(math.Float32frombits(binary.LittleEndian.Uint32(body[off:])))
	}
	for i := range m.tris {
		o := i*50 + 12 // skip the stored normal
		m.tris[i] = tri{
			a: [3]float64{f32(o), f32(o + 4), f32(o + 8)},
			b: [3]float64{f32(o + 12), f32(o + 16), f32(o + 20)},
			c: [3]float64{f32(o + 24), f32(o + 28), f32(o + 32)},
		}
	}
	m.normalise()
	return m, nil
}

func stlName(path string) string {
	base := filepath.Base(path)
	return base[:len(base)-len(filepath.Ext(base))]
}

// normalise centres the mesh on its bounding box and scales it so the
// furthest vertex sits at radius 1.
func (m *mesh) normalise() {
	if len(m.tris) == 0 {
		return
	}
	lo, hi := m.tris[0].a, m.tris[0].a
	m.each(func(p [3]float64) {
		for i := 0; i < 3; i++ {
			lo[i], hi[i] = math.Min(lo[i], p[i]), math.Max(hi[i], p[i])
		}
	})
	var mid [3]float64
	for i := 0; i < 3; i++ {
		mid[i] = (lo[i] + hi[i]) / 2
	}

	r := 0.0
	m.each(func(p [3]float64) {
		d := 0.0
		for i := 0; i < 3; i++ {
			d += (p[i] - mid[i]) * (p[i] - mid[i])
		}
		r = math.Max(r, math.Sqrt(d))
	})
	if r == 0 {
		return
	}
	for i := range m.tris {
		for _, v := range [...]*[3]float64{&m.tris[i].a, &m.tris[i].b, &m.tris[i].c} {
			for j := 0; j < 3; j++ {
				v[j] = (v[j] - mid[j]) / r
			}
		}
	}
}

func (m *mesh) each(fn func([3]float64)) {
	for _, t := range m.tris {
		fn(t.a)
		fn(t.b)
		fn(t.c)
	}
}

func sub(a, b [3]float64) [3]float64 { return [3]float64{a[0] - b[0], a[1] - b[1], a[2] - b[2]} }

func cross(a, b [3]float64) [3]float64 {
	return [3]float64{a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]}
}

func norm(v [3]float64) [3]float64 {
	l := math.Sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
	if l == 0 {
		return v
	}
	return [3]float64{v[0] / l, v[1] / l, v[2] / l}
}

// renderMesh draws the mesh at the given orientation into a w×h char grid.
func renderMesh(m *mesh, w, h int, ang [3]float64, wire bool) []string {
	c := renderMeshCanvas(m, w, h, ang, wire)
	if c == nil {
		return nil
	}
	return c.lines()
}

func renderMeshCanvas(m *mesh, w, h int, ang [3]float64, wire bool) *canvas {
	if w < 1 || h < 1 || m == nil {
		return nil
	}
	c := newCanvas(w, h, 1, viewFill)
	light := norm([3]float64{0, cubeLight, -1})

	for _, t := range m.tris {
		a, b, cc := rot(t.a, ang), rot(t.b, ang), rot(t.c, ang)
		n := norm(cross(sub(b, a), sub(cc, a)))
		if n[2] >= 0 {
			continue // back face: the camera sits at -z looking towards +z
		}
		if wire {
			for _, e := range [3][2][3]float64{{a, b}, {b, cc}, {cc, a}} {
				c.line(e[0], e[1], cubeWire)
			}
			continue
		}
		lum := math.Max(n[0]*light[0]+n[1]*light[1]+n[2]*light[2], cubeAmbient)
		c.triangle(a, b, cc, rune(cubeRamp[min(int(lum*float64(len(cubeRamp))), len(cubeRamp)-1)]))
	}
	return c
}

// triangle fills a projected triangle, interpolating 1/z across it so the
// depth buffer resolves overlaps per cell rather than per face.
func (c *canvas) triangle(p0, p1, p2 [3]float64, ch rune) {
	x0, y0, z0 := c.project(p0)
	x1, y1, z1 := c.project(p1)
	x2, y2, z2 := c.project(p2)
	if z0 <= 0.1 || z1 <= 0.1 || z2 <= 0.1 {
		return
	}

	area := (x1-x0)*(y2-y0) - (x2-x0)*(y1-y0)
	if math.Abs(area) < 1e-9 {
		return // edge-on sliver, nothing to fill
	}

	minX := max(int(math.Floor(math.Min(x0, math.Min(x1, x2)))), 0)
	maxX := min(int(math.Ceil(math.Max(x0, math.Max(x1, x2)))), c.w-1)
	minY := max(int(math.Floor(math.Min(y0, math.Min(y1, y2)))), 0)
	maxY := min(int(math.Ceil(math.Max(y0, math.Max(y1, y2)))), c.h-1)

	if maxX < minX || maxY < minY {
		return
	}

	filled := 0
	for y := minY; y <= maxY; y++ {
		for x := minX; x <= maxX; x++ {
			px, py := float64(x), float64(y)
			w0 := ((x1-px)*(y2-py) - (x2-px)*(y1-py)) / area
			w1 := ((x2-px)*(y0-py) - (x0-px)*(y2-py)) / area
			w2 := 1 - w0 - w1
			if w0 < 0 || w1 < 0 || w2 < 0 {
				continue
			}
			c.set(x, y, w0/z0+w1/z1+w2/z2, ch)
			filled++
		}
	}

	// A triangle smaller than a cell can slip between cell centres and cover
	// nothing. At mesh densities that is most of them, and every miss is a
	// pinhole showing the inside of the part, so fall back to its centroid.
	if filled == 0 {
		c.set(int(math.Round((x0+x1+x2)/3)), int(math.Round((y0+y1+y2)/3)), 3/(z0+z1+z2), ch)
	}
}

// line draws a projected segment with a depth bias, so wireframe edges win
// against the surface they lie on.
func (c *canvas) line(p0, p1 [3]float64, ch rune) {
	x0, y0, z0 := c.project(p0)
	x1, y1, z1 := c.project(p1)
	if z0 <= 0.1 || z1 <= 0.1 {
		return
	}
	steps := int(math.Max(math.Abs(x1-x0), math.Abs(y1-y0)))
	for i := 0; i <= steps; i++ {
		t := 0.0
		if steps > 0 {
			t = float64(i) / float64(steps)
		}
		ooz := (1-t)/z0 + t/z1
		c.set(int(math.Round(x0+t*(x1-x0))), int(math.Round(y0+t*(y1-y0))), ooz+1e-3, ch)
	}
}

// findSTLs lists the exported STLs at the repo root, largest part first so
// the headline model leads.
func findSTLs(root string) []string {
	paths, err := filepath.Glob(filepath.Join(root, "cad", "export", "*.stl"))
	if err != nil {
		return nil
	}
	return paths
}
