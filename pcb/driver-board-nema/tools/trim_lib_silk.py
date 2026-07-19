"""Clip silkscreen back out of pads, in the vendored footprint libraries.

    ~/.local/share/uv/tools/atopile/bin/python tools/trim_lib_silk.py

Several EasyEDA footprints draw their outline — and on the electrolytic, its
polarity marking — straight across their own pads, which KiCad's DRC flags as
silk-over-copper. This trims the library files rather than the board so that
the board stays in parity with its libraries; `ato build` then picks up the
already-clean footprints.

Idempotent: re-running finds nothing left to trim.
"""

import math
from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad

PARTS = Path(__file__).parent.parent / "parts"
MARGIN = 0.3    # keep silk this far clear of copper
MIN_KEEP = 0.5  # drop leftover stubs shorter than this — short ones end up too
                # close to the neighbouring segment they were cut away from


def pad_rects(fp):
    rects = []
    for pad in fp.pads:
        w, h = pad.size.w, (pad.size.h or pad.size.w)
        if round((pad.at.r or 0) % 180) == 90:
            w, h = h, w
        rects.append((pad.at.x - w / 2 - MARGIN, pad.at.y - h / 2 - MARGIN,
                      pad.at.x + w / 2 + MARGIN, pad.at.y + h / 2 + MARGIN))
    return rects


def trim(path: Path) -> int:
    fp_file = kicad.loads(kicad.footprint.FootprintFile, path.read_text())
    fp = fp_file.footprint
    rects = pad_rects(fp)
    if not rects:
        return 0
    before = sum(1 for ln in fp.fp_lines if "SilkS" in str(ln.layer))

    def clear(x, y):
        return not any(a <= x <= c and b <= y <= d for a, b, c, d in rects)

    changed = 0
    for ln in fp.fp_lines:
        if "SilkS" not in str(ln.layer):
            continue
        x1, y1, x2, y2 = ln.start.x, ln.start.y, ln.end.x, ln.end.y
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            continue
        n = max(2, int(length / 0.02))
        # longest contiguous run of clear samples
        best = cur = None
        for i in range(n + 1):
            t = i / n
            if clear(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t):
                cur = (t if cur is None else cur[0], t) if cur else (t, t)
            else:
                if cur and (best is None or cur[1] - cur[0] > best[1] - best[0]):
                    best = cur
                cur = None
        if cur and (best is None or cur[1] - cur[0] > best[1] - best[0]):
            best = cur
        if best == (0.0, 1.0) or (best and best[0] == 0 and best[1] == 1):
            continue
        if best is None or (best[1] - best[0]) * length < MIN_KEEP:
            # Buried in copper with nothing worth keeping. Leave it be: moving
            # it off the silk layer would need `layer` and `layers` kept in
            # sync, and atopile reads the plural one when it works out a
            # footprint's silk bbox — desync it and the build dies in
            # Geometry.bbox on an empty point list.
            continue
        ln.start.x, ln.start.y = x1 + (x2 - x1) * best[0], y1 + (y2 - y1) * best[0]
        ln.end.x, ln.end.y = x1 + (x2 - x1) * best[1], y1 + (y2 - y1) * best[1]
        changed += 1

    changed += snap_corners(fp)
    # Never strip a footprint bare: atopile needs at least one silk outline to
    # compute a courtyard, and a part with no outline is unplaceable by hand.
    # On the smallest chips the pads leave no clear silk at all, so in that case
    # keep the original artwork and accept it as-is.
    assert sum(1 for ln in fp.fp_lines if "SilkS" in str(ln.layer)) == before
    if changed:
        kicad.dumps(fp_file, path)
    return changed


def snap_corners(fp, tol=0.4):
    """Close silk corners that nearly-but-don't-quite meet.

    EasyEDA draws chip outlines as separate strokes whose corners stop ~0.2mm
    apart. That gap is under KiCad's silk-to-silk clearance, so it reads as a
    violation between two segments of the same part. Snapping the endpoints
    together makes it one continuous outline, which is what was intended.
    """
    ends = []
    for ln in fp.fp_lines:
        if "SilkS" not in str(ln.layer):
            continue
        ends.append((ln, "start"))
        ends.append((ln, "end"))

    changed = 0
    for i, (la, ea) in enumerate(ends):
        pa = getattr(la, ea)
        for lb, eb in ends[i + 1:]:
            if lb is la:
                continue
            pb = getattr(lb, eb)
            d = math.hypot(pa.x - pb.x, pa.y - pb.y)
            if 0 < d <= tol:
                mx, my = (pa.x + pb.x) / 2, (pa.y + pb.y) / 2
                pa.x, pa.y = mx, my
                pb.x, pb.y = mx, my
                changed += 1
    return changed


def main():
    total = 0
    for mod in sorted(PARTS.glob("*/*.kicad_mod")):
        n = trim(mod)
        total += n
        if n:
            print(f"  {mod.parent.name}/{mod.name}: trimmed {n} silk segment(s)")
    print(f"trimmed {total} silk segment(s)")


if __name__ == "__main__":
    main()
