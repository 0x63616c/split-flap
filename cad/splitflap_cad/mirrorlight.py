"""Arched-mirror LED backlight — side quest, not part of the split-flap.

A 34 x 76in tombstone mirror hangs flat on the wall. Printed spacers screw
to the wall and hold it off by ml_standoff; a Hue Solo lightstrip lies in a
groove on their OUTER face, firing radially OUTWARD, so light leaves through
the wall/mirror gap and washes the wall — a halo, no fixture in sight. The
spacers sit ml_inset in from the mirror edge, hidden behind the glass.

Why the groove faces out and the strip's width runs along Z: a strip only
bends about its width axis. Following the arch curves the strip in the
mirror plane, so the width MUST lie along the wall normal — which is exactly
the pose that aims the emitting face radially outward. Easy bend, right
direction, one groove.

Arch geometry is derived, not measured: params holds width / side height /
overall height, and P.ml_arch_r + P.ml_arch_cy fall out of them.

World frame: wall = XY plane at z=0, +Z out of the wall, +Y up, X across,
origin on the mirror's bottom centreline.

Parts (all print wall-face-down, groove opening UP — no overhang over the
groove, screw bores run horizontally):
- `spacer_straight` — the sides. Local: outer face the x=0 plane facing +X,
  body to -X, length along Y centred, wall face z=0.
- `spacer_arch` — the arch, swept about the inset radius; every arch spacer
  is identical. Same local frame, curvature centre at (-P.ml_path_r, 0).
- `slack_spool` — the uncut roll is longer than the lit path; the surplus
  coils flat on this, hidden behind the glass. Local: base bottom at z=0.

View: `just cad view mirror-light` (also mirror-spacer / mirror-section).
"""

import math
from dataclasses import dataclass

from build123d import (
    Align,
    Axis,
    Box,
    Circle,
    Compound,
    Cylinder,
    Plane,
    Pos,
    Rectangle,
    Rot,
    extrude,
    revolve,
)

from .params import IN, P
from .viewer import Scene

# ---------------------------------------------------------------- layout


@dataclass(frozen=True)
class Run:
    """One straight or arch segment of the lit path, with its spacers laid
    out flush to the segment ends minus the reserved junction half-gaps.
    `at` is each spacer centre as arc length from the segment start."""

    name: str
    length: float  # full lit length of the segment
    lead: float  # reserved before the first spacer (half a junction gap)
    tail: float  # reserved after the last
    n: int
    gap: float  # gap between consecutive spacers, this segment

    @property
    def at(self) -> list[float]:
        pitch = P.ml_spacer_len + self.gap
        return [self.lead + P.ml_spacer_len / 2 + i * pitch for i in range(self.n)]


def _fit(length: float, lead: float, tail: float, name: str) -> Run:
    """Pick the spacer count whose resulting gap lands nearest P.ml_gap.
    Spacers sit flush to both ends of the usable span, so the count alone
    sets the gap — no free phase to slide, and nothing can drift into a
    junction because the lead/tail reserves are cut off the span first."""
    usable = length - lead - tail
    best = min(
        (n for n in range(2, 40) if n * P.ml_spacer_len < usable),
        key=lambda n: abs((usable - n * P.ml_spacer_len) / (n - 1) - P.ml_gap),
    )
    return Run(name, length, lead, tail, best, (usable - best * P.ml_spacer_len) / (best - 1))


def layout() -> list[Run]:
    """The three lit segments, bottom-left round to bottom-right.

    Junction handling: each side reserves half a gap at its top and the
    arch reserves half at both ends, so the straight->arch gap comes out at
    exactly P.ml_gap — never a collision, never a butt joint, and it reads
    the same as every other gap. The bottom ends start flush (a spacer
    right at the bottom of each side, where the mirror wants support)."""
    half = P.ml_gap / 2
    side = _fit(P.ml_side_run, 0.0, half, "side")
    arch = _fit(P.ml_arch_run, half, half, "arch")
    return [side, arch, side]


# ---------------------------------------------------------------- parts


def _groove(length: float) -> Box:
    """Strip channel cutter for a straight spacer: full length along Y,
    open on the +X (outer) face."""
    return Pos(0, 0, P.ml_groove_z0 + P.ml_groove_w / 2) * Box(
        2 * P.ml_groove_depth, length, P.ml_groove_w
    )


def _screw_cutter():
    """One screw: through-hole the whole standoff, plus the counterbore
    sunk from the mirror-side face. Axis +Z, at the origin."""
    through = Pos(0, 0, P.ml_standoff / 2) * Cylinder(P.ml_screw_d / 2, 2 * P.ml_standoff)
    cbore = Pos(0, 0, P.ml_standoff - P.ml_cbore_depth / 2) * Cylinder(
        P.ml_screw_head_d / 2, P.ml_cbore_depth
    )
    return through + cbore


def spacer_straight():
    """Straight spacer for the mirror's vertical sides."""
    t, L = P.ml_spacer_t, P.ml_spacer_len
    body = Pos(-t / 2, 0, P.ml_standoff / 2) * Box(t, L, P.ml_standoff)
    body -= _groove(2 * L)
    for dy in (-P.ml_screw_pitch / 2, P.ml_screw_pitch / 2):
        body -= Pos(-t + P.ml_screw_r, dy, 0) * _screw_cutter()
    return body


def spacer_arch():
    """Arch spacer: the same section swept about the inset arch radius.
    All arch spacers are identical — the arch is a single circular arc."""
    r, t, dphi = P.ml_path_r, P.ml_spacer_t, P.ml_spacer_dphi
    sec = Plane.XZ * Pos(r - t, 0) * Rectangle(
        t, P.ml_standoff, align=(Align.MIN, Align.MIN)
    )
    body = revolve(sec, axis=Axis.Z, revolution_arc=dphi)
    # groove: annular channel open on the outer face
    ring = Pos(0, 0, P.ml_groove_z0) * Cylinder(
        r + 1, P.ml_groove_w, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    ring -= Pos(0, 0, P.ml_groove_z0) * Cylinder(
        r - P.ml_groove_depth, P.ml_groove_w, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    body -= ring
    # screws on the same arc, +-half the screw pitch measured along it
    for s in (-P.ml_screw_pitch / 2, P.ml_screw_pitch / 2):
        a = dphi / 2 + math.degrees(s / r)
        body -= Rot(0, 0, a) * Pos(r - t + P.ml_screw_r, 0, 0) * _screw_cutter()
    # local frame: outer face midpoint at the origin, +X radially out
    return Pos(-r, 0, 0) * Rot(0, 0, -dphi / 2) * body


def slack_spool():
    """Flat spool for the leftover strip: hub, base, retaining rim, vents.
    Two screws to the wall; the whole stack clears the mirror easily."""
    hub_r, wall = P.ml_spool_hub_d / 2, P.ml_spool_wall
    rim_r = P.ml_spool_coil_od / 2
    base_t, rim_h = P.ml_spool_base_t, P.ml_spool_rim_h
    base = Cylinder(
        rim_r + wall, base_t, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    up = (Align.CENTER, Align.CENTER, Align.MIN)
    hub = Pos(0, 0, base_t) * (
        Cylinder(hub_r, rim_h, align=up) - Cylinder(hub_r - wall, rim_h, align=up)
    )
    rim = Pos(0, 0, base_t) * (
        Cylinder(rim_r + wall, rim_h, align=up) - Cylinder(rim_r, rim_h, align=up)
    )
    spool = base + hub + rim
    # vents through hub + base: a coiled strip has nowhere to dump heat
    vent_w = 2 * math.pi * (hub_r - wall / 2) / (2 * P.ml_spool_vent_n)
    for i in range(P.ml_spool_vent_n):
        v = Pos(hub_r, 0, base_t + rim_h / 2) * Box(4 * wall, vent_w, rim_h)
        spool -= Rot(0, 0, i * 360 / P.ml_spool_vent_n) * v
    for dx in (-hub_r / 2, hub_r / 2):
        spool -= Pos(dx, 0, base_t / 2) * Cylinder(P.ml_screw_d / 2, 4 * base_t)
    return spool


# ------------------------------------------------------------- placement


def side_poses(sign: int) -> list:
    """Locations for one straight side's spacers. sign=+1 is the right
    side (+X); the left is the same part turned 180 about Z."""
    run = layout()[0]
    rot = Rot(0, 0, 0) if sign > 0 else Rot(0, 0, 180)
    return [
        Pos(sign * P.ml_path_x, P.ml_inset + s, 0) * rot for s in run.at
    ]


def arch_angles() -> list[float]:
    """Polar angle (deg from +X, about the arch centre) of each arch
    spacer's mid-point. Walking the arc from the LEFT junction round to
    the right, so the strip runs up the left side and over the top."""
    run = layout()[1]
    return [
        180 - P.ml_path_phi - math.degrees(s / P.ml_path_r) for s in run.at
    ]


def arch_poses() -> list:
    """Locations for the arch spacers, swept round the inset arc."""
    return [
        Pos(0, P.ml_arch_cy, 0) * Rot(0, 0, a) * Pos(P.ml_path_r, 0, 0)
        for a in arch_angles()
    ]


def spool_pose():
    """Slack spool: bottom centre, behind the glass, clear of the bottom
    spacers and of the strip runs up both sides."""
    return Pos(0, P.ml_inset + P.ml_spool_coil_od / 2 + P.ml_spool_wall, 0)


def posed_spacers() -> list:
    straight, arch = spacer_straight(), spacer_arch()
    out = [loc * straight for loc in side_poses(1) + side_poses(-1)]
    return out + [loc * arch for loc in arch_poses()]


# ------------------------------------------------------------- reference


def mirror_ghost():
    """The glass itself: tombstone outline, back face on the spacer tops."""
    w, h = P.ml_mirror_w, P.ml_mirror_side_h
    face = Pos(0, h / 2) * Rectangle(w, h)
    cap = Pos(0, P.ml_arch_cy) * Circle(P.ml_arch_r)
    cap &= Pos(0, h + P.ml_arch_rise / 2) * Rectangle(w, P.ml_arch_rise)
    return Pos(0, 0, P.ml_standoff) * extrude(face + cap, amount=P.ml_mirror_t)


def strip_solids() -> list:
    """The lightstrip as laid: two straight runs and the arch, sitting on
    the groove floors. Three solids because the path kinks slightly at the
    junction — same as the real strip."""
    w, t = P.ml_strip_w, P.ml_strip_t
    z = P.ml_groove_z0 + P.ml_groove_w / 2
    out = []
    for sign in (1, -1):
        x = sign * (P.ml_path_x - P.ml_groove_depth + t / 2)
        out.append(
            Pos(x, P.ml_inset + P.ml_side_run / 2, z) * Box(t, P.ml_side_run, w)
        )
    r = P.ml_path_r - P.ml_groove_depth
    band = Pos(0, 0, z - w / 2) * (
        Cylinder(r + t, w, align=(Align.CENTER, Align.CENTER, Align.MIN))
        - Cylinder(r, w, align=(Align.CENTER, Align.CENTER, Align.MIN))
    )
    wedge = revolve(
        Plane.XZ * Pos(0, z - w / 2) * Rectangle(
            r + t, w, align=(Align.MIN, Align.MIN)
        ),
        axis=Axis.Z,
        revolution_arc=180 - 2 * P.ml_path_phi,
    )
    arc = Pos(0, P.ml_arch_cy, 0) * Rot(0, 0, P.ml_path_phi) * (band & wedge)
    out.append(arc)
    return out


def strip_slack_coil():
    """The surplus strip, coiled on the spool: a ghost annulus of the
    right cross-section and radial build, not a real helix."""
    r0 = P.ml_spool_hub_d / 2
    r1 = P.ml_spool_coil_od / 2
    up = (Align.CENTER, Align.CENTER, Align.MIN)
    z = P.ml_spool_base_t
    return spool_pose() * Pos(0, 0, z) * (
        Cylinder(r1, P.ml_strip_w, align=up) - Cylinder(r0, P.ml_strip_w, align=up)
    )


def assembly():
    """Everything, posed, as one compound — this is what goes to STEP."""
    parts = posed_spacers() + [spool_pose() * slack_spool()]
    parts += strip_solids() + [strip_slack_coil(), mirror_ghost()]
    return Compound(children=parts)


# ---------------------------------------------------------------- scenes


def scene() -> Scene:
    """Full wall view: glass ghost, spacers, strip, slack spool."""
    s = Scene()
    s.add(mirror_ghost(), "mirror", "lightblue", 0.25)
    for i, sp in enumerate(posed_spacers()):
        s.add(sp, f"spacer{i:02d}", "orange")
    for i, st in enumerate(strip_solids()):
        s.add(st, f"strip{i}", "yellow")
    s.add(spool_pose() * slack_spool(), "slack-spool", "orange")
    s.add(strip_slack_coil(), "slack-coil", "yellow", 0.6)
    return s


def spacer_scene() -> Scene:
    """The two printable spacers side by side, strip ghost in the groove."""
    w, t = P.ml_strip_w, P.ml_strip_t
    z = P.ml_groove_z0 + P.ml_groove_w / 2
    strip = Pos(-P.ml_groove_depth + t / 2, 0, z) * Box(t, P.ml_spacer_len, w)
    s = Scene()
    s.add(spacer_straight(), "spacer-straight", "orange")
    s.add(strip, "strip-straight", "yellow", 0.6)
    off = Pos(0, 2.2 * P.ml_spacer_len, 0)
    s.add(off * spacer_arch(), "spacer-arch", "steelblue")
    s.add(off * strip, "strip-arch", "yellow", 0.6)
    return s


def spool_scene() -> Scene:
    return (
        Scene()
        .add(slack_spool(), "slack-spool", "orange")
        .add(Pos(0, 0, 0) * (spool_pose().inverse() * strip_slack_coil()),
             "slack-coil", "yellow", 0.5)
    )


# ---------------------------------------------------------------- report


def report() -> list[str]:
    """The numbers worth reading before ordering screws or hanging glass."""
    side, arch, _ = layout()
    n = 2 * side.n + arch.n
    lines = [
        f"arch: R {P.ml_arch_r:.1f}mm ({P.ml_arch_r / IN:.3f}in), centre "
        f"{P.ml_arch_cy:.1f}mm up ({P.ml_arch_cy / IN:.2f}in), "
        f"sweep {180 - 2 * P.ml_path_phi:.2f}deg",
        f"inset contour: sides x=+-{P.ml_path_x:.1f}mm, arch R "
        f"{P.ml_path_r:.1f}mm, junction y {P.ml_path_junction_y:.1f}mm",
        f"lit path: side {P.ml_side_run / IN:.1f}in x2 + arch "
        f"{P.ml_arch_run / IN:.1f}in = {P.ml_path_len / IN:.1f}in "
        f"({P.ml_path_len / IN / 12:.2f}ft)",
        f"strip {P.ml_strip_len / IN / 12:.2f}ft -> slack "
        f"{P.ml_slack / IN:.1f}in ({P.ml_slack / IN / 12:.2f}ft) on the spool "
        f"({P.ml_slack / (math.pi * P.ml_spool_hub_d):.1f}+ turns, "
        f"coil OD {P.ml_spool_coil_od:.0f}mm)",
        f"spacers: {side.n} per side + {arch.n} arch = {n} total",
        f"gaps: side {side.gap / IN:.2f}in, arch {arch.gap / IN:.2f}in, "
        f"junction {(side.tail + arch.lead) / IN:.2f}in (target "
        f"{P.ml_gap / IN:.2f}in)",
        f"groove: {P.ml_groove_w:.1f} x {P.ml_groove_depth:.1f}mm for a "
        f"{P.ml_strip_w:.1f} x {P.ml_strip_t:.1f}mm sleeve "
        f"({P.ml_groove_over:.1f}mm shy of the mouth)",
        f"screws: 2 x #8 per spacer, cbore {P.ml_screw_head_d:.1f} x "
        f"{P.ml_cbore_depth:.1f} deep -> {P.ml_screw_meat:.1f}mm "
        f"({P.ml_screw_meat / IN:.2f}in) under the head",
        f"  into a stud through 1/2in drywall: {P.ml_screw_meat:.0f} + 12.7 "
        f"+ 25 embed = {P.ml_screw_meat + 12.7 + 25:.0f}mm -> buy #8 x 2-1/2in",
        f"  total screws: {2 * n} + 2 for the spool",
    ]
    return lines
