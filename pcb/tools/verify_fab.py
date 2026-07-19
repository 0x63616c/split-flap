"""Numeric pre-fab checks on a FILLED board, shared by both driver boards.

    python3 pcb/tools/verify_fab.py BOARD.kicad_pcb

These are the things KiCad's DRC either does not check, checks only as a
warning, or -- in the case of the courtyard rules -- ships as an *ignored*
check, so that a board with no courtyards at all passes cleanly. Everything
here is computed from the board file itself, in board coordinates, with
footprint and pad rotation applied.

  1. every footprint carries an F.CrtYd courtyard (unless it declares
     allow_missing_courtyard, which only the NPTH mount pads do)
  2. no two courtyards overlap
  3. no pad or courtyard sticks out past the Edge.Cuts outline
  4. no silkscreen stroke crosses a solder-mask opening (i.e. lands on exposed
     copper a builder has to solder to)
  5. every silkscreen stroke and text is >= 0.15mm wide -- PCBWay's stated
     minimum, below which they reserve the right to drop the artwork

Parsed with a local s-expression reader rather than faebryk's: the fab source
is the KiCad-written build/filled.kicad_pcb, and faebryk's parser rejects the
dialect `kicad-cli --save-board` emits (it adds `(tenting (front yes))`).

Exits non-zero and prints every failure if anything trips.
"""

import math
import sys
from pathlib import Path

MIN_SILK_W = 0.15
EPS = 1e-6
# How far a silk stroke has to reach into a mask opening before it counts as
# a defect. The vendored EasyEDA connector footprints draw their body lip
# flush with the pad windows and clip a few tens of microns into them along
# the way; that is below what a fab can hold and below what its own automatic
# silk-over-mask clipping cares about. Anything that puts a third of a
# minimum-width stroke (0.05mm) onto a pad is a real defect and fails.
MAX_GRAZE = 0.05


# ---------------------------------------------------------------- s-expr ----

def parse(text):
    """Minimal KiCad s-expression reader -> nested lists of str."""
    out, stack, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "(":
            new = []
            (stack[-1] if stack else out).append(new)
            stack.append(new)
            i += 1
        elif c == ")":
            stack.pop()
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while text[j] != '"':
                if text[j] == "\\":
                    buf.append(text[j + 1])
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            stack[-1].append("".join(buf))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            stack[-1].append(text[i:j])
            i = j
    return out[0]


def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def kid(node, name):
    got = kids(node, name)
    return got[0] if got else None


def num(node, i):
    return float(node[i])


def xy(node):
    return (num(node, 1), num(node, 2))


# ------------------------------------------------------------- geometry ----

def rot(x, y, deg):
    a = math.radians(-deg)  # KiCad rotation is CCW in a y-down world
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def boxes_overlap(a, b, gap=0.0):
    return (a[0] < b[2] - gap and b[0] < a[2] - gap
            and a[1] < b[3] - gap and b[1] < a[3] - gap)


def seg_box_hit(p1, p2, box, w):
    """Does the segment p1-p2, stroked at width w, intersect the AABB?"""
    h = w / 2
    x1, y1, x2, y2 = box[0] - h, box[1] - h, box[2] + h, box[3] + h
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, p1[0] - x1), (dx, x2 - p1[0]),
                 (-dy, p1[1] - y1), (dy, y2 - p1[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    return t1 - t0 > EPS and t0 < t1


def seg_box_depth(p1, p2, box, w):
    """How far the stroked segment reaches inside the AABB, in mm."""
    h = w / 2
    best, n = 0.0, 64
    for i in range(n + 1):
        x = p1[0] + (p2[0] - p1[0]) * i / n
        y = p1[1] + (p2[1] - p1[1]) * i / n
        dx = min(x - box[0], box[2] - x) + h
        dy = min(y - box[1], box[3] - y) + h
        if dx > 0 and dy > 0:
            best = max(best, min(dx, dy, box[2] - box[0], box[3] - box[1]))
    return best


GRAPHICS = ("fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly",
            "gr_line", "gr_rect", "gr_circle", "gr_arc", "gr_poly")


def arc_points(a, b, c, n=24):
    """Sample the circular arc through three points."""
    (x1, y1), (x2, y2), (x3, y3) = a, b, c
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:                      # collinear -> straight
        return [a, b, c]
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1)
          + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3)
          + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.dist((ux, uy), a)
    t1 = math.atan2(y1 - uy, x1 - ux)
    t2 = math.atan2(y2 - uy, x2 - ux)
    t3 = math.atan2(y3 - uy, x3 - ux)
    # unwrap so the mid angle lies between the two ends
    while t2 < t1:
        t2 += 2 * math.pi
    while t3 < t2:
        t3 += 2 * math.pi
    return [(ux + r * math.cos(t1 + (t3 - t1) * i / n),
             uy + r * math.sin(t1 + (t3 - t1) * i / n)) for i in range(n + 1)]


def graphic_polyline(g):
    """Local-space polyline(s) approximating a graphic's stroked path.

    Returned as a list of point lists. Circles and arcs are sampled rather
    than reduced to their bounding box -- an 0603's silk arcs wrap around the
    pads without touching them, and a bbox test calls that a collision.
    """
    st, en = kid(g, "start"), kid(g, "end")
    ctr, mid = kid(g, "center"), kid(g, "mid")
    if g[0].endswith("circle") and ctr is not None and en is not None:
        c, e = xy(ctr), xy(en)
        r = math.dist(c, e)
        n = 24
        return [[(c[0] + r * math.cos(2 * math.pi * i / n),
                  c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]]
    if g[0].endswith("arc") and st is not None and mid is not None and en is not None:
        return [arc_points(xy(st), xy(mid), xy(en))]
    if g[0].endswith("rect") and st is not None and en is not None:
        (x1, y1), (x2, y2) = xy(st), xy(en)
        return [[(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]]
    if st is not None and en is not None:
        return [[xy(st), xy(en)]]
    p = kid(g, "pts")
    if p is not None:
        pts = [xy(c) for c in kids(p, "xy")]
        return [pts + pts[:1]] if pts else []
    return []


def graphic_points(g):
    """Every local-space point a graphic touches (for bounding boxes)."""
    out = []
    for pl in graphic_polyline(g):
        out += pl
    return out


def layer_of(g):
    lay = kid(g, "layer")
    return lay[1] if lay else ""


def stroke_w(g):
    s = kid(g, "stroke")
    if s is not None:
        w = kid(s, "width")
        if w is not None:
            return num(w, 1)
    w = kid(g, "width")
    return num(w, 1) if w is not None else 0.0


def text_thickness(t):
    e = kid(t, "effects")
    f = kid(e, "font") if e is not None else None
    th = kid(f, "thickness") if f is not None else None
    return num(th, 1) if th is not None else None


# ------------------------------------------------------------------ main ----

def main(path):
    board_sexp = parse(Path(path).read_text())
    errs = []

    edge_pts = []
    for g in board_sexp:
        if isinstance(g, list) and g and g[0] in GRAPHICS and layer_of(g) == "Edge.Cuts":
            edge_pts += graphic_points(g)
    assert edge_pts, "no Edge.Cuts outline found"
    board = bbox(edge_pts)

    # the printed opening is the pad grown by the board's mask expansion, not
    # the copper -- that is the area a builder actually has to wet with solder
    setup = kid(board_sexp, "setup")
    mc = kid(setup, "pad_to_mask_clearance") if setup is not None else None
    mask_exp = num(mc, 1) if mc is not None else 0.0

    courtyards, mask_pads, silk = [], [], []

    for fp in kids(board_sexp, "footprint"):
        ref = "?"
        for p in kids(fp, "property"):
            if p[1] == "Reference":
                ref = p[2] or "?"
        at = kid(fp, "at")
        fx, fy = num(at, 1), num(at, 2)
        fr = num(at, 3) if len(at) > 3 else 0.0
        attrs = " ".join(str(x) for x in (kid(fp, "attr") or []))

        cy_pts = []
        for g in fp:
            if not (isinstance(g, list) and g and g[0] in GRAPHICS):
                continue
            lay = layer_of(g)
            polys = [[(fx + a, fy + b)
                      for a, b in (rot(px, py, fr) for px, py in pl)]
                     for pl in graphic_polyline(g)]
            if "CrtYd" in lay:
                for pl in polys:
                    cy_pts += pl
            if "SilkS" in lay:
                w = stroke_w(g)
                # a filled poly has stroke width 0 by construction; the fill is
                # what prints, and it is always wider than the minimum
                filled = kid(g, "fill") is not None and "solid" in " ".join(kid(g, "fill")[1:])
                if w < MIN_SILK_W and not filled:
                    errs.append(f"{ref}: silk {g[0]} stroke {w}mm < {MIN_SILK_W}mm on {lay}")
                for pl in polys:
                    for a, b in zip(pl, pl[1:]):
                        silk.append((ref, lay, a, b, max(w, 0.0)))

        for t in kids(fp, "fp_text") + kids(fp, "property"):
            if "SilkS" not in layer_of(t):
                continue
            if not (len(t) > 2 and str(t[2]).strip()):
                continue                       # empty field -- nothing prints
            th = text_thickness(t)
            if (th or 0) < MIN_SILK_W:
                errs.append(f"{ref}: silk text thickness {th}mm < {MIN_SILK_W}mm")

        if cy_pts:
            courtyards.append((ref, bbox(cy_pts)))
        elif "allow_missing_courtyard" not in attrs:
            errs.append(f"{ref}: no F.CrtYd courtyard")

        for pad in kids(fp, "pad"):
            layers = " ".join(kid(pad, "layers")[1:])
            pat = kid(pad, "at")
            size = kid(pad, "size")
            w, h = num(size, 1), num(size, 2)
            # a pad's angle in a BOARD file is absolute, not relative to the
            # footprint -- adding fr to it double-counts the rotation and
            # sizes every rotated pad along the wrong axis
            pr = num(pat, 3) if len(pat) > 3 else fr
            if round(pr % 180) == 90:
                w, h = h, w
            px, py = rot(num(pat, 1), num(pat, 2), fr)
            box = (fx + px - w / 2, fy + py - h / 2, fx + px + w / 2, fy + py + h / 2)
            if (box[0] < board[0] or box[1] < board[1]
                    or box[2] > board[2] or box[3] > board[3]):
                errs.append(f"{ref}.{pad[1]}: pad off-board")
            if "Mask" in layers:
                mask_pads.append((f"{ref}.{pad[1]}", layers,
                                  (box[0] - mask_exp, box[1] - mask_exp,
                                   box[2] + mask_exp, box[3] + mask_exp)))

    for g in board_sexp:
        if not (isinstance(g, list) and g and g[0] in GRAPHICS):
            continue
        if "SilkS" not in layer_of(g):
            continue
        w = stroke_w(g)
        if w < MIN_SILK_W:
            errs.append(f"board {g[0]} stroke {w}mm < {MIN_SILK_W}mm")
        for pl in graphic_polyline(g):
            for a, b in zip(pl, pl[1:]):
                silk.append(("board", layer_of(g), a, b, w))
    for t in kids(board_sexp, "gr_text"):
        if "SilkS" not in layer_of(t):
            continue
        th = text_thickness(t)
        if (th or 0) < MIN_SILK_W:
            errs.append(f"board text {t[1]!r}: thickness {th}mm < {MIN_SILK_W}mm")

    for ref, cy in courtyards:
        if (cy[0] < board[0] or cy[1] < board[1]
                or cy[2] > board[2] or cy[3] > board[3]):
            errs.append(f"{ref}: courtyard off-board {tuple(round(v, 2) for v in cy)}")
    for i, (ra, a) in enumerate(courtyards):
        for rb, b in courtyards[i + 1:]:
            if boxes_overlap(a, b, gap=0.01):
                errs.append(f"{ra} <-> {rb}: courtyards overlap")

    worst = {}
    for ref, lay, s, e, w in silk:
        side = "F.Mask" if lay.startswith("F") else "B.Mask"
        for pn, players, box in mask_pads:
            if side not in players and "*.Mask" not in players:
                continue
            if not seg_box_hit(s, e, box, w):
                continue
            d = seg_box_depth(s, e, box, w)
            if d > worst.get(pn, (0.0, ""))[0]:
                worst[pn] = (d, ref)
    grazes = []
    for pn, (d, ref) in sorted(worst.items(), key=lambda kv: -kv[1][0]):
        msg = f"silk of {ref} reaches {d * 1000:.0f}um into the mask opening of {pn}"
        (errs if d > MAX_GRAZE else grazes).append(msg)

    for g in grazes:
        print("  note: " + g + f" (under the {MAX_GRAZE * 1000:.0f}um threshold)")
    print(f"{Path(path).name}: board {board[2] - board[0]:.1f}x{board[3] - board[1]:.1f}mm, "
          f"{len(kids(board_sexp, 'footprint'))} footprints, {len(courtyards)} courtyards, "
          f"{len(mask_pads)} mask openings, {len(silk)} silk strokes")
    if errs:
        print("VERIFY FAILED:")
        for e in sorted(set(errs)):
            print("  " + e)
        sys.exit(1)
    print("verify ok: courtyards present & disjoint, nothing off-board, "
          "no silk on exposed pads, all silk >= 0.15mm")


if __name__ == "__main__":
    main(sys.argv[1])
