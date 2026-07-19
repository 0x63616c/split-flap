"""Place footprints on the driver board and render an SVG preview.

Run with atopile's interpreter (it bundles faebryk):
    ~/.local/share/uv/tools/atopile/bin/python tools/place_and_render.py

Placement is by atopile_address, so it survives `ato build` designator
reshuffles. Rendering is pads + silk + edge + airwires — enough to sanity
check placement and connectivity without KiCad installed.
"""

import math
import re
from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad

ROOT = Path(__file__).parent.parent
PCB = ROOT / "layouts/default/default.kicad_pcb"

# address -> (x, y, rot_deg)  origin top-left, y down, mm
# Board 45x60 — fits behind a module (plate is 95x118) with room to spare, so
# parts are spaced for hand-soldering rather than packed. XIAO socket rows
# 15.24mm apart, USB end at top edge.
PLACEMENT = {
    "xiao_left": (14.88, 14.0, 270),   # D0..D6, pin1 at top
    "xiao_right": (30.12, 14.0, 270),  # 5V..D7, pin1 at top
    "uln": (18.0, 34.0, 90),
    "c_hf": (25.5, 34.0, 90),
    "c_bulk": (30.5, 34.5, 90),
    # rot 0 (was 180): latch faces the board edge so the motor cable exits
    # off-board instead of over the chip. Pin order along +x is 5..1.
    "j_motor": (13.0, 44.0, 0),
    "j_hall": (30.0, 50.5, 0),
}
BOARD_W, BOARD_H = 45.0, 60.0

# PCBWay's stated minimum silkscreen line width. The vendored footprints draw
# pin-1 dots at 0.06mm and outlines at 0.10mm, both under it, and a dropped
# pin-1 dot is not cosmetic -- so widths are normalised here rather than
# trusted from the libraries. Same value and reasoning as the v2 board.
MIN_SILK_W = 0.15

# M3 clearance holes, one per corner — heat-set inserts in the back shell.
MOUNT_HOLES = [(3.5, 3.5), (41.5, 3.5), (3.5, 56.5), (41.5, 56.5)]
MOUNT_DIA = 3.2

# Board-level silk: (text, x, y, size, rot). Per-footprint refdes/polarity/pin-1
# silk already comes from the footprints — this is the stuff that makes the
# board self-documenting when you're plugging connectors into it.
SILK = [
    ("XIAO ESP32-C6", 22.5, 2.6, 1.0, 0),
    ("USB ^", 22.5, 4.4, 0.8, 0),
    ("SPLIT-FLAP DRIVER v1", 22.5, 25.6, 1.1, 0),
    ("IN1-4 = D0-D3", 8.0, 29.5, 0.8, 0),
    ("HALL DO = D8", 8.0, 31.3, 0.8, 0),
    ("28BYJ-48 MOTOR", 13.5, 54.2, 0.9, 0),
    ("+5V", 7.92, 41.4, 0.8, 0),
    ("HALL", 30.0, 46.8, 0.9, 0),
    ("Designed by 0x63616c", 22.5, 57.6, 0.9, 0),
]

# Footprint-local refdes overrides, for the ones whose stock position lands on
# their own pad or a neighbour's. Local coords; the footprint rotation is
# applied on top, so these are pre-rotation.
REFDES_LOCAL = {
    "xiao_left": (-8.99, 2.5),   # J3 — off the pad column, to its left
    "xiao_right": (-8.99, 2.5),  # J4 — ditto
    "c_hf": (-8.0, -2.0),        # C2 — open space below, well clear of C1
    "c_bulk": (-7.0, 0.0),       # C1 — stock position lands inside its own pad 1
}


def rot(x, y, deg):
    a = math.radians(-deg)  # kicad rotation is CCW in a y-down world
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)




def fp_boxes(k):
    """(addr, pad_boxes, body_box) in board coords, honouring pad rotation."""
    out = []
    for fp in k.footprints:
        addr = next(p.value for p in fp.propertys if p.name == "atopile_address").split(".")[-1]
        fx, fy, fr = fp.at.x, fp.at.y, fp.at.r or 0
        pads, xs, ys = [], [], []
        for pad in fp.pads:
            px, py = rot(pad.at.x, pad.at.y, fr)
            w, h = pad.size.w, (pad.size.h or pad.size.w)
            # pad.at.r is ABSOLUTE in a board file (main() folds the
            # footprint rotation into it), so adding fr again double-counts
            if round((pad.at.r or 0) % 180) == 90:
                w, h = h, w
            box = (fx + px - w / 2, fy + py - h / 2, fx + px + w / 2, fy + py + h / 2)
            pads.append((pad.name, box))
            xs += [box[0], box[2]]
            ys += [box[1], box[3]]
        for ln in list(fp.fp_lines) + list(fp.fp_rects):
            if "SilkS" not in str(ln.layer) and "CrtYd" not in str(ln.layer):
                continue
            for px, py in (rot(ln.start.x, ln.start.y, fr), rot(ln.end.x, ln.end.y, fr)):
                xs.append(fx + px)
                ys.append(fy + py)
        out.append((addr, pads, (min(xs), min(ys), max(xs), max(ys))))
    return out


def thicken_silk(k):
    """Raise every footprint silk stroke and text to at least MIN_SILK_W.

    The vendored EasyEDA footprints draw their pin-1 dots as 0.06mm circles and
    most of their outlines at 0.10mm, both under PCBWay's 0.15mm minimum. A
    0.06mm dot is the marking that says which way round a polarised part goes,
    so losing it in production is not cosmetic.
    """
    bumped = 0
    for fp in k.footprints:
        graphics = (list(fp.fp_lines) + list(fp.fp_rects)
                    + list(fp.fp_circles) + list(fp.fp_arcs) + list(fp.fp_poly))
        for g in graphics:
            if "SilkS" not in str(getattr(g, "layer", "")):
                continue
            if g.stroke and g.stroke.width < MIN_SILK_W:
                g.stroke.width = MIN_SILK_W
                bumped += 1
        for t in list(fp.fp_texts) + list(fp.propertys):
            if "SilkS" not in str(getattr(t, "layer", "")):
                continue
            if t.effects and t.effects.font and (t.effects.font.thickness or 0) < MIN_SILK_W:
                t.effects.font.thickness = MIN_SILK_W
                bumped += 1
    print(f"silk: raised {bumped} strokes/texts to >= {MIN_SILK_W}mm")


def check(k):
    """Body overlap / off-board / pad clearance, numerically. Raises on failure."""
    boxes = fp_boxes(k)
    errs = []

    def overlap(a, b, gap=0.0):
        return (a[0] < b[2] - gap and b[0] < a[2] - gap
                and a[1] < b[3] - gap and b[1] < a[3] - gap)

    for addr, pads, body in boxes:
        if body[0] < 0 or body[1] < 0 or body[2] > BOARD_W or body[3] > BOARD_H:
            errs.append(f"{addr}: body off-board {tuple(round(v, 2) for v in body)}")
        for hx, hy in MOUNT_HOLES:
            hole = (hx - MOUNT_DIA / 2, hy - MOUNT_DIA / 2, hx + MOUNT_DIA / 2, hy + MOUNT_DIA / 2)
            if overlap(body, hole):
                errs.append(f"{addr}: body over mount hole at ({hx}, {hy})")

    for i, (a_addr, a_pads, a_body) in enumerate(boxes):
        for b_addr, b_pads, b_body in boxes[i + 1:]:
            if overlap(a_body, b_body, gap=0.01):
                errs.append(f"{a_addr} <-> {b_addr}: bodies overlap")
            for an, ab in a_pads:
                for bn, bb in b_pads:
                    if overlap(ab, bb, gap=-0.2):  # 0.2mm pad-to-pad minimum
                        errs.append(f"{a_addr}.{an} <-> {b_addr}.{bn}: pads < 0.2mm apart")

    if errs:
        raise SystemExit("PLACEMENT CHECK FAILED:\n  " + "\n  ".join(sorted(set(errs))))
    print(f"placement check ok: {len(boxes)} footprints, none overlapping or off-board")


def main():
    pcb = kicad.loads(kicad.pcb.PcbFile, strip_mount_holes(PCB.read_text()))
    k = pcb.kicad_pcb

    for fp in k.footprints:
        # faebryk's rotate_fp chokes on propertys/texts without an `at`
        for p in fp.propertys:
            if p.at is None:
                p.at = kicad.pcb.Xyr(x=0, y=0, r=0)
            elif p.at.r is None:
                p.at.r = 0
        for t in fp.fp_texts:
            if t.at.r is None:
                t.at.r = 0

        addr = next(p.value for p in fp.propertys if p.name == "atopile_address")
        if addr not in PLACEMENT:
            continue
        x, y, r = PLACEMENT[addr]
        cur = fp.at.r or 0
        fp.at.x, fp.at.y = x, y
        fp.at.r = r
        delta = (r - cur) % 360
        if delta:
            for obj in list(fp.pads) + list(fp.fp_texts) + list(fp.propertys):
                obj.at.r = ((obj.at.r or 0) + delta) % 360

        if addr in REFDES_LOCAL:
            ref = next(p for p in fp.propertys if p.name == "Reference")
            ref.at.x, ref.at.y = REFDES_LOCAL[addr]
            # these fields ship right-justified; with the footprint rotated that
            # throws KiCad's extent calc off, so centre them
            if ref.effects:
                ref.effects.justify = None

    # board outline
    while len(k.gr_lines):
        k.gr_lines.pop(len(k.gr_lines) - 1)
    for (x1, y1), (x2, y2) in [
        ((0, 0), (BOARD_W, 0)),
        ((BOARD_W, 0), (BOARD_W, BOARD_H)),
        ((BOARD_W, BOARD_H), (0, BOARD_H)),
        ((0, BOARD_H), (0, 0)),
    ]:
        line = kicad.pcb.Line(
            start=kicad.pcb.Xy(x=x1, y=y1),
            end=kicad.pcb.Xy(x=x2, y=y2),
            stroke=kicad.pcb.Stroke(width=0.1, type="default"),
            layer="Edge.Cuts",
        )
        k.gr_lines.append(line)

    # M3 mounting holes. These used to be Edge.Cuts circles, i.e. routed inner
    # contours: a fab does cut those, but `kicad-cli export drill` then wrote an
    # EMPTY non-plated drill file, so nothing in the fab package declared them
    # as holes at all. They are emitted as real NPTH pads by add_mount_holes()
    # below -- same fix the v2 board already carries.
    while len(k.gr_circles):
        k.gr_circles.pop(len(k.gr_circles) - 1)

    # board-level silkscreen
    while len(k.gr_texts):
        k.gr_texts.pop(len(k.gr_texts) - 1)
    for text, tx, ty, size, rot in SILK:
        k.gr_texts.append(kicad.pcb.Text(
            text=text,
            at=kicad.pcb.Xyr(x=tx, y=ty, r=rot),
            layer=kicad.pcb.TextLayer(layer="F.SilkS"),
            effects=kicad.pcb.Effects(
                font=kicad.pcb.Font(size=kicad.pcb.Wh(w=size, h=size),
                                    thickness=max(MIN_SILK_W,
                                                  round(size * 0.15, 3))),
            ),
        ))

    thicken_silk(k)
    check(k)

    route(k)
    kicad.dumps(pcb, PCB)
    add_mount_holes()
    set_mask_expansion()
    render(pcb)


# Routing ---------------------------------------------------------------------
# Hand-routed, 2 layers. Convention: long runs on B.Cu, stubs/fans on F.Cu.
# Each route: (from_pad, width, [(x, y), ...] waypoints incl. start/end).
# "via" entries switch layer at that point. Pads referenced as "addr.pin".
SIG, PWR = 0.4, 0.8
VIA_SIZE, VIA_DRILL = 0.6, 0.3

# Layer discipline: B.Cu carries the four d-signal lanes and both power spines;
# F.Cu carries every power branch, so branches cross the lanes on the far side.
ROUTES = [
    # dN: xiao_left pad (THT) -> B.Cu right + down its own lane -> via -> F.Cu
    # stub to the ULN input. Lanes sit between the ULN's right pads (x 20.74)
    # and c_hf (x 25.5).
    ("xiao_left.1", SIG, [("B", 14.88, 6.38), ("B", 24.0, 6.38), ("B", 24.0, 38.45), ("via",), ("F", 20.74, 38.45)]),
    ("xiao_left.2", SIG, [("B", 14.88, 8.92), ("B", 23.25, 8.92), ("B", 23.25, 37.17), ("via",), ("F", 20.74, 37.17)]),
    ("xiao_left.3", SIG, [("B", 14.88, 11.46), ("B", 22.5, 11.46), ("B", 22.5, 35.9), ("via",), ("F", 20.74, 35.9)]),
    ("xiao_left.4", SIG, [("B", 14.88, 14.0), ("B", 21.75, 14.0), ("B", 21.75, 34.63), ("via",), ("F", 20.74, 34.63)]),
    # OUTn: ULN output (SMD) -> short F.Cu stub left -> via -> B.Cu diagonal
    # down to its motor pad. Stub x staggers so the diagonals stay parallel.
    ("uln.16", SIG, [("F", 15.26, 38.45), ("F", 14.0, 38.45), ("via",), ("B", 18.08, 44.0)]),
    ("uln.15", SIG, [("F", 15.26, 37.17), ("F", 12.0, 37.17), ("via",), ("B", 15.54, 44.0)]),
    ("uln.14", SIG, [("F", 15.26, 35.9), ("F", 10.2, 35.9), ("via",), ("B", 13.0, 44.0)]),
    ("uln.13", SIG, [("F", 15.26, 34.63), ("F", 8.4, 34.63), ("via",), ("B", 10.46, 44.0)]),
    # 5V spine: xiao_right.1 -> right corridor (x 37.5) -> along the bottom ->
    # up into j_motor.5
    ("xiao_right.1", PWR, [("B", 30.12, 6.38), ("B", 37.5, 6.38), ("B", 37.5, 54.0), ("B", 7.92, 54.0), ("B", 7.92, 44.0)]),
    # 5V branch: via off spine -> F.Cu left, then down into j_hall.1
    ("j_hall.1", PWR, [("B", 37.5, 47.0), ("via",), ("F", 27.5, 47.0), ("F", 27.5, 50.5)]),
    # 5V branch: via off spine -> F.Cu left above the chip, down into COM (pin 9)
    ("uln.9", PWR, [("B", 37.5, 23.5), ("via",), ("F", 14.2, 23.5), ("F", 14.2, 29.55), ("F", 15.26, 29.55)]),
    # 5V branch: via off spine -> F.Cu left below c_bulk, up into c_hf.1
    ("c_hf.1", PWR, [("B", 37.5, 40.5), ("via",), ("F", 25.5, 40.5), ("F", 25.5, 34.7)]),
    # 5V branch: via off spine -> F.Cu left into c_bulk.POS
    ("c_bulk.1", PWR, [("B", 37.5, 37.17), ("via",), ("F", 30.5, 37.17)]),
    # GND spine: xiao_right.2 -> inner right corridor (x 35.0) -> j_hall.2
    ("xiao_right.2", PWR, [("B", 30.12, 8.92), ("B", 35.0, 8.92), ("B", 35.0, 45.5), ("B", 30.0, 45.5), ("B", 30.0, 50.5)]),
    # GND branch: via off spine -> F.Cu left, down into ULN E (pin 8)
    ("uln.8", PWR, [("B", 35.0, 26.5), ("via",), ("F", 20.74, 26.5), ("F", 20.74, 29.55)]),
    # GND branch: via off spine -> F.Cu left, down into c_hf.2
    ("c_hf.2", PWR, [("B", 35.0, 29.0), ("via",), ("F", 25.5, 29.0), ("F", 25.5, 33.3)]),
    # GND branch: via off spine -> F.Cu left into c_bulk.NEG
    ("c_bulk.2", PWR, [("B", 35.0, 31.83), ("via",), ("F", 30.5, 31.83)]),
    # hall DO: xiao_right.6 (D8) -> F.Cu out to the right margin, down, into j_hall.3
    ("xiao_right.6", SIG, [("F", 30.12, 19.08), ("F", 40.0, 22.0), ("F", 40.0, 48.0), ("F", 32.5, 50.5)]),
]

LAYERS = {"F": "F.Cu", "B": "B.Cu"}


def route(k):
    # wipe previous routing
    for coll in (k.segments, k.vias):
        while len(coll):
            coll.pop(len(coll) - 1)

    # pad -> net lookup
    padnet = {}
    for fp in k.footprints:
        addr = next(p.value for p in fp.propertys if p.name == "atopile_address")
        for pad in fp.pads:
            if pad.net:
                padnet[f"{addr}.{pad.name}"] = pad.net.number

    for start_pad, width, path in ROUTES:
        net = padnet[start_pad]
        prev = None
        for step in path:
            if step[0] == "via":
                k.vias.append(kicad.pcb.Via(
                    at=kicad.pcb.Xy(x=prev[0], y=prev[1]),
                    size=VIA_SIZE, drill=VIA_DRILL,
                    layers=["F.Cu", "B.Cu"], net=net,
                ))
                continue
            layer, x, y = LAYERS[step[0]], step[1], step[2]
            if prev is not None and (prev[0], prev[1]) != (x, y):
                k.segments.append(kicad.pcb.Segment(
                    start=kicad.pcb.Xy(x=prev[0], y=prev[1]),
                    end=kicad.pcb.Xy(x=x, y=y),
                    width=width, layer=layer, net=net,
                ))
            prev = (x, y)


def render(pcb):
    k = pcb.kicad_pcb
    S = 14  # px per mm
    out = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="-40 -40 {BOARD_W * S + 80} {BOARD_H * S + 80}" '
        f'font-family="monospace">'
    )
    out.append(
        f'<rect x="-40" y="-40" width="{BOARD_W * S + 80}" height="{BOARD_H * S + 80}" fill="#10141a"/>'
    )
    out.append(
        f'<rect x="0" y="0" width="{BOARD_W * S}" height="{BOARD_H * S}" '
        f'rx="8" fill="#173425" stroke="#c8a038" stroke-width="2"/>'
    )

    # copper segments: B.Cu under everything, F.Cu on top of pads' layer order
    for want, color, op in (("B.Cu", "#3b6ea5", 0.9), ("F.Cu", "#b0433b", 0.9)):
        for seg in k.segments:
            if str(seg.layer) != want:
                continue
            out.append(
                f'<line x1="{seg.start.x * S:.1f}" y1="{seg.start.y * S:.1f}" '
                f'x2="{seg.end.x * S:.1f}" y2="{seg.end.y * S:.1f}" '
                f'stroke="{color}" stroke-width="{seg.width * S:.1f}" '
                f'stroke-linecap="round" opacity="{op}"/>'
            )

    net_pads = {}
    routed_nets = {seg.net for seg in k.segments}
    for fp in k.footprints:
        fx, fy, fr = fp.at.x, fp.at.y, fp.at.r or 0
        ref = next(p.value for p in fp.propertys if p.name == "Reference")
        addr = next(p.value for p in fp.propertys if p.name == "atopile_address")
        # silk lines
        for ln in fp.fp_lines:
            if "SilkS" not in str(ln.layer):
                continue
            x1, y1 = rot(ln.start.x, ln.start.y, fr)
            x2, y2 = rot(ln.end.x, ln.end.y, fr)
            out.append(
                f'<line x1="{(fx + x1) * S:.1f}" y1="{(fy + y1) * S:.1f}" '
                f'x2="{(fx + x2) * S:.1f}" y2="{(fy + y2) * S:.1f}" '
                f'stroke="#8fa3b8" stroke-width="1.2"/>'
            )
        for pad in fp.pads:
            lx, ly = rot(pad.at.x, pad.at.y, fr)
            px, py = (fx + lx) * S, (fy + ly) * S
            w, h = pad.size.w * S, (pad.size.h or pad.size.w) * S
            pr = (pad.at.r or 0) % 360
            if pr in (90, 270):
                w, h = h, w
            tht = str(pad.type) == "thru_hole"
            color = "#d4b03c" if tht else "#c87533"
            if str(pad.shape) == "circle":
                out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{w / 2:.1f}" fill="{color}"/>')
            else:
                rx = 2 if str(pad.shape) in ("roundrect", "oval") else 0
                out.append(
                    f'<rect x="{px - w / 2:.1f}" y="{py - h / 2:.1f}" width="{w:.1f}" '
                    f'height="{h:.1f}" rx="{rx}" fill="{color}"/>'
                )
            if tht and pad.drill and pad.drill.size_x:
                out.append(
                    f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{pad.drill.size_x * S / 2:.1f}" fill="#10141a"/>'
                )
            if pad.net and pad.net.number and pad.net.number not in routed_nets:
                net_pads.setdefault(pad.net.name, []).append((px, py))
        # reference + address label
        out.append(
            f'<text x="{fx * S:.1f}" y="{(fy) * S - 4:.1f}" fill="#e8e0d0" '
            f'font-size="11" text-anchor="middle">{ref} {addr}</text>'
        )

    # vias
    for via in k.vias:
        out.append(
            f'<circle cx="{via.at.x * S:.1f}" cy="{via.at.y * S:.1f}" '
            f'r="{via.size * S / 2:.1f}" fill="#d4b03c"/>'
            f'<circle cx="{via.at.x * S:.1f}" cy="{via.at.y * S:.1f}" '
            f'r="{via.drill * S / 2:.1f}" fill="#10141a"/>'
        )

    # airwires: chain pads of each still-unrouted net
    for name, pads in net_pads.items():
        if len(pads) < 2:
            continue
        for (x1, y1), (x2, y2) in zip(pads, pads[1:]):
            out.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#4fd1c5" stroke-width="0.7" opacity="0.55"/>'
            )

    out.append(
        f'<text x="{BOARD_W * S / 2}" y="-14" fill="#e8e0d0" font-size="14" '
        f'text-anchor="middle">split-flap driver v1 — 36x48mm — red=F.Cu blue=B.Cu</text>'
    )
    out.append("</svg>")
    (ROOT / "preview.svg").write_text("\n".join(out))
    print("wrote", ROOT / "preview.svg")




MOUNT_FP_LIB = "SPLITFLAP_MOUNT"

MOUNT_FP = """
	(footprint "{lib}:M3_NPTH"
		(layer "F.Cu")
		(uuid "{uuid}")
		(at {x} {y})
		(attr exclude_from_pos_files exclude_from_bom allow_missing_courtyard)
		(pad "" np_thru_hole circle
			(at 0 0)
			(size {d} {d})
			(drill {d})
			(layers "F&B.Cu" "F.Mask" "B.Mask")
			(uuid "{puid}")
		)
	)
"""


def strip_mount_holes(text):
    """Remove mount-hole footprints from a previous run, by paren matching.

    They are spliced in as raw s-expressions after the dump, so they carry no
    atopile_address and would otherwise trip fp_boxes() on the next run.
    """
    while True:
        i = text.find(f'"{MOUNT_FP_LIB}:')
        if i == -1:
            return text
        start = text.rindex("(footprint", 0, i)
        depth, j = 0, start
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        ls = text.rindex("\n", 0, start)
        text = text[:ls] + text[j:]


def add_mount_holes():
    """Emit the four M3 holes as real NPTH pads.

    As Edge.Cuts circles they were routed inner contours: the fab cuts them,
    but `kicad-cli export drill` produced an EMPTY non-plated drill file, so
    the fab package never actually declared them as holes. A routed 3.2mm
    contour also carries router tolerance rather than drill tolerance, which
    matters when an M3 screw head lands next to a 12V trace.
    """
    text = PCB.read_text().rstrip()
    assert text.endswith(")")
    block = "".join(
        MOUNT_FP.format(lib=MOUNT_FP_LIB, uuid=kicad.gen_uuid(), puid=kicad.gen_uuid(),
                        x=hx, y=hy, d=MOUNT_DIA)
        for hx, hy in MOUNT_HOLES
    )
    PCB.write_text(text[:-1] + block + ")\n")
    print(f"added {len(MOUNT_HOLES)} M3 NPTH pads ({MOUNT_DIA}mm)")


def set_mask_expansion():
    """Solder mask expansion, globally.

    pad_to_mask_clearance 0 makes every mask aperture exactly equal to its
    copper, so any registration error at all leaves mask creeping onto the
    pad. 0.05mm is the usual house value and is what the fabs assume.
    """
    want = 0.05
    text = PCB.read_text()
    new, n = re.subn(r"\(pad_to_mask_clearance [\d.]+\)",
                     f"(pad_to_mask_clearance {want})", text, count=1)
    assert n == 1, "pad_to_mask_clearance not found in the board setup block"
    PCB.write_text(new)
    print(f"set pad_to_mask_clearance to {want}mm")


if __name__ == "__main__":
    main()
