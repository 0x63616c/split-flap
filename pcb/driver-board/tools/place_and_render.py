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
    "c_bulk": (24.5, 30.0, 90),
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

    kicad.dumps(pcb, PCB)
    render(pcb)


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

    net_pads = {}
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
            if pad.net and pad.net.number:
                net_pads.setdefault(pad.net.name, []).append((px, py))
        # reference + address label
        out.append(
            f'<text x="{fx * S:.1f}" y="{(fy) * S - 4:.1f}" fill="#e8e0d0" '
            f'font-size="11" text-anchor="middle">{ref} {addr}</text>'
        )

    # airwires: chain pads of each net
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
        f'text-anchor="middle">split-flap driver v1 — 36x48mm — unrouted (airwires)</text>'
    )
    out.append("</svg>")
    (ROOT / "preview.svg").write_text("\n".join(out))
    print("wrote", ROOT / "preview.svg")


if __name__ == "__main__":
    main()
