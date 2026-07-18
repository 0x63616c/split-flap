"""Place footprints on the driver board and render an SVG preview.

Run with atopile's interpreter (it bundles faebryk):
    ~/.local/share/uv/tools/atopile/bin/python tools/place_and_render.py

Placement is by atopile_address, so it survives `ato build` designator
reshuffles. Rendering is pads + silk + edge + airwires — enough to sanity
check placement and connectivity without KiCad installed.
"""

import math
from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad

ROOT = Path(__file__).parent.parent
PCB = ROOT / "layouts/default/default.kicad_pcb"

# address -> (x, y, rot_deg)  origin top-left, y down, mm
# Board 36x48. XIAO socket rows 15.24mm apart, USB end at top edge.
PLACEMENT = {
    "xiao_left": (10.38, 10.5, 270),   # D0..D6, pin1 at top
    "xiao_right": (25.62, 10.5, 270),  # 5V..D7, pin1 at top
    "uln": (18.0, 30.0, 90),
    "c_hf": (24.7, 30.0, 90),
    "c_bulk": (30.5, 30.5, 90),
    "j_motor": (10.5, 43.0, 180),
    "j_hall": (27.0, 42.5, 0),
}
BOARD_W, BOARD_H = 36.0, 48.0


def rot(x, y, deg):
    a = math.radians(-deg)  # kicad rotation is CCW in a y-down world
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def main():
    pcb = kicad.loads(kicad.pcb.PcbFile, PCB.read_text())
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

    route(k)
    kicad.dumps(pcb, PCB)
    render(pcb)


# Routing ---------------------------------------------------------------------
# Hand-routed, 2 layers. Convention: long runs on B.Cu, stubs/fans on F.Cu.
# Each route: (from_pad, width, [(x, y), ...] waypoints incl. start/end).
# "via" entries switch layer at that point. Pads referenced as "addr.pin".
SIG, PWR = 0.4, 0.8
VIA_SIZE, VIA_DRILL = 0.6, 0.3

# d-signal vertical lanes on B.Cu between ULN and c_hf, one x per signal
ROUTES = [
    # dN: xiao_left pad (THT) -> B.Cu right + down lane -> via -> F.Cu stub to ULN input
    ("xiao_left.1", SIG, [("B", 10.38, 2.88), ("B", 23.75, 2.88), ("B", 23.75, 34.45), ("via",), ("F", 20.74, 34.45)]),
    ("xiao_left.2", SIG, [("B", 10.38, 5.42), ("B", 23.0, 5.42), ("B", 23.0, 33.17), ("via",), ("F", 20.74, 33.17)]),
    ("xiao_left.3", SIG, [("B", 10.38, 7.96), ("B", 22.25, 7.96), ("B", 22.25, 31.9), ("via",), ("F", 20.74, 31.9)]),
    ("xiao_left.4", SIG, [("B", 10.38, 10.5), ("B", 21.5, 10.5), ("B", 21.5, 30.63), ("via",), ("F", 20.74, 30.63)]),
    # OUTn: ULN output (SMD) -> F.Cu left + via -> B.Cu down to motor pad
    ("uln.16", SIG, [("F", 15.26, 34.45), ("F", 5.5, 34.45), ("via",), ("B", 5.5, 43.0)]),
    ("uln.15", SIG, [("F", 15.26, 33.17), ("F", 8.0, 33.17), ("via",), ("B", 8.0, 43.0)]),
    ("uln.14", SIG, [("F", 15.26, 31.9), ("F", 10.5, 31.9), ("via",), ("B", 10.5, 43.0)]),
    ("uln.13", SIG, [("F", 15.26, 30.63), ("F", 13.0, 30.63), ("via",), ("B", 13.0, 43.0)]),
    # 5V spine: xiao_right.1 -> right of headers -> down -> around j_hall -> under
    # connectors -> up into j_motor.5
    ("xiao_right.1", PWR, [("B", 25.62, 2.88), ("B", 28.8, 2.88), ("B", 28.8, 35.0), ("B", 31.6, 35.0), ("B", 31.6, 46.5), ("B", 15.5, 46.5), ("B", 15.5, 43.0)]),
    # 5V branch: bottom run up into j_hall.1
    ("j_hall.1", PWR, [("B", 24.5, 46.5), ("B", 24.5, 42.5)]),
    # 5V branch: via off spine -> F.Cu over the chip to COM (pin 9)
    ("uln.9", PWR, [("B", 28.8, 22.6), ("via",), ("F", 14.2, 22.6), ("F", 14.2, 25.55), ("F", 15.26, 25.55)]),
    # 5V branch: via off spine -> F.Cu left into c_hf.1
    ("c_hf.1", PWR, [("B", 28.8, 30.6), ("via",), ("F", 24.7, 30.7)]),
    # 5V branch: via on spine -> F.Cu right into c_bulk.POS
    ("c_bulk.1", PWR, [("B", 28.8, 33.17), ("via",), ("F", 30.5, 33.17)]),
    # GND spine: xiao_right.2 -> down -> j_hall.2
    ("xiao_right.2", PWR, [("B", 25.62, 5.42), ("B", 27.2, 5.42), ("B", 27.2, 40.0), ("B", 27.0, 42.5)]),
    # GND branch: via off spine -> F.Cu to ULN E (pin 8)
    ("uln.8", PWR, [("B", 27.2, 23.7), ("via",), ("F", 20.74, 23.7), ("F", 20.74, 25.55)]),
    # GND branch: via off spine -> F.Cu left to c_hf.2 and right to c_bulk.NEG
    ("c_hf.2", PWR, [("B", 27.2, 29.3), ("via",), ("F", 24.7, 29.3)]),
    ("c_bulk.2", PWR, [("F", 27.2, 29.3), ("F", 29.2, 27.83), ("F", 30.5, 27.83)]),
    # hall DO: xiao_right.6 (THT) -> F.Cu down the right edge into j_hall.3
    ("xiao_right.6", SIG, [("F", 25.62, 15.58), ("F", 34.4, 23.0), ("F", 34.4, 40.5), ("F", 29.5, 42.5)]),
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


if __name__ == "__main__":
    main()
