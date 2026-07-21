"""2D deliverable drawings for the mirror backlight (mirrorlight.py).

Two PNGs, both drawn straight off the same params/layout the solids are
built from — no numbers retyped here:
- `render_layout` — front elevation: glass outline, inset contour, every
  spacer in place, the strip path, the slack spool.
- `render_section` — annotated cross-section through a straight spacer at
  a screw: standoff, groove, strip, counterbore, glass, light path.

Millimetres throughout; the labels carry the inch equivalents because the
mirror was measured with a tape.

Written by `python -m splitflap_cad render` into cad/export/.
"""

import math
from pathlib import Path

from .mirrorlight import arch_angles, layout, report
from .params import IN, P

FIG_DPI = 160
INK = "#1c1c1c"
GLASS = "#7fb2d6"
PART = "#e08a2e"
STRIP = "#f2c53d"
GHOST = "#9aa0a6"


def _mirror_outline(n: int = 200):
    """Tombstone outline as an (xs, ys) polyline, closed."""
    w, h = P.ml_mirror_w / 2, P.ml_mirror_side_h
    phi0 = math.degrees(math.acos(w / P.ml_arch_r))
    xs, ys = [-w, -w], [0.0, h]
    for i in range(n + 1):
        a = math.radians(180 - phi0 - i * (180 - 2 * phi0) / n)
        xs.append(P.ml_arch_r * math.cos(a))
        ys.append(P.ml_arch_cy + P.ml_arch_r * math.sin(a))
    xs += [w, -w]
    ys += [0.0, 0.0]
    return xs, ys


def _inset_contour(n: int = 200):
    """The lit path: up one side, round the arch, down the other."""
    x, r = P.ml_path_x, P.ml_path_r
    xs, ys = [-x, -x], [P.ml_inset, P.ml_path_junction_y]
    for i in range(n + 1):
        a = math.radians(180 - P.ml_path_phi - i * (180 - 2 * P.ml_path_phi) / n)
        xs.append(r * math.cos(a))
        ys.append(P.ml_arch_cy + r * math.sin(a))
    xs += [x, x]
    ys += [P.ml_path_junction_y, P.ml_inset]
    return xs, ys


def _dim(ax, p0, p1, text, offset=(0, 0), rot=0, fs=7):
    """A dimension line with arrows both ends and a centred label."""
    (x0, y0), (x1, y1) = p0, p1
    ax.annotate(
        "", xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8, shrinkA=0, shrinkB=0),
    )
    ax.text(
        (x0 + x1) / 2 + offset[0], (y0 + y1) / 2 + offset[1], text,
        ha="center", va="center", fontsize=fs, rotation=rot, color=INK,
        bbox=dict(fc="white", ec="none", pad=1.0),
    )


def render_layout(out: Path) -> Path:
    """Front elevation, looking at the wall through the glass."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle, Wedge

    side, arch, _ = layout()
    fig, ax = plt.subplots(figsize=(7.2, 13.5), dpi=FIG_DPI)

    ax.fill(*_mirror_outline(), color=GLASS, alpha=0.18, zorder=0)
    ax.plot(*_mirror_outline(), color=GLASS, lw=1.6, zorder=2, label="mirror edge")
    ax.plot(
        *_inset_contour(), color=STRIP, lw=2.2, zorder=3,
        label=f"strip path ({P.ml_path_len / IN / 12:.2f} ft)",
    )

    t, L = P.ml_spacer_t, P.ml_spacer_len
    for sign in (1, -1):
        for s in side.at:
            y = P.ml_inset + s
            x0 = sign * P.ml_path_x - (t if sign > 0 else 0)
            ax.add_patch(
                Rectangle((x0, y - L / 2), t, L, fc=PART, ec=INK, lw=0.5, zorder=4)
            )
    for a in arch_angles():
        ax.add_patch(
            Wedge(
                (0, P.ml_arch_cy), P.ml_path_r,
                a - P.ml_spacer_dphi / 2, a + P.ml_spacer_dphi / 2,
                width=t, fc=PART, ec=INK, lw=0.5, zorder=4,
            )
        )
    ax.add_patch(Rectangle((0, 0), 0, 0, fc=PART, ec=INK, label="spacer (3 in)"))

    sy = P.ml_inset + P.ml_spool_coil_od / 2 + P.ml_spool_wall
    ax.add_patch(
        Circle((0, sy), P.ml_spool_coil_od / 2 + P.ml_spool_wall,
               fc="none", ec=PART, lw=1.4, zorder=4)
    )
    ax.add_patch(
        Circle((0, sy), P.ml_spool_hub_d / 2, fc="none", ec=STRIP, lw=1.2, zorder=4)
    )
    ax.text(
        0, sy - P.ml_spool_coil_od / 2 - 26,
        f"slack spool — {P.ml_slack / IN:.1f} in coiled",
        ha="center", va="center", fontsize=7, color=INK,
    )

    # feed end + dark bottom edge
    ax.plot([-P.ml_path_x], [P.ml_inset], "o", color=INK, ms=5, zorder=6)
    ax.annotate(
        "strip start (feed)", xy=(-P.ml_path_x, P.ml_inset),
        xytext=(-P.ml_mirror_w / 2 - 40, -70), fontsize=7, color=INK,
        arrowprops=dict(arrowstyle="->", lw=0.8, color=INK),
    )
    ax.plot(
        [-P.ml_path_x, P.ml_path_x], [P.ml_inset * 0.5] * 2,
        ls=(0, (2, 3)), color=GHOST, lw=1.2,
    )
    ax.text(
        0, -46, "bottom edge unlit", ha="center",
        fontsize=7, color=GHOST,
    )

    # dimensions
    w2, h = P.ml_mirror_w / 2, P.ml_mirror_side_h
    _dim(ax, (-w2, -110), (w2, -110), f'34" ({P.ml_mirror_w:.0f} mm)')
    _dim(ax, (w2 + 120, 0), (w2 + 120, h), f'60" side', rot=90)
    _dim(ax, (w2 + 210, 0), (w2 + 210, P.ml_mirror_h), f'76" overall', rot=90)
    _dim(
        ax, (P.ml_path_x, P.ml_path_junction_y + 8), (w2, P.ml_path_junction_y + 8),
        f'2.2"', offset=(0, 34), fs=6.5,
    )
    g0 = P.ml_inset + side.at[0] + L / 2
    _dim(
        ax, (-P.ml_path_x - 46, g0), (-P.ml_path_x - 46, g0 + side.gap),
        f"gap {side.gap / IN:.2f}\"", rot=90, fs=6.5,
    )
    _dim(
        ax, (-P.ml_path_x - 46, P.ml_path_junction_y - side.tail),
        (-P.ml_path_x - 46, P.ml_path_junction_y + arch.lead),
        f"junction gap {P.ml_gap / IN:.2f}\"", rot=90, fs=6.5, offset=(-24, 0),
    )
    ax.plot(
        [-P.ml_mirror_w / 2 - 60, P.ml_mirror_w / 2],
        [P.ml_path_junction_y] * 2, ls=(0, (4, 4)), color=GHOST, lw=0.7,
    )
    ax.text(
        -P.ml_mirror_w / 2 + 120, P.ml_path_junction_y + 12,
        f"straight/arch junction  y={P.ml_path_junction_y / IN:.1f}\"",
        fontsize=6.5, color=GHOST,
    )

    ax.set_title(
        "Arched mirror backlight — layout (front elevation, mm)\n"
        + f"{2 * side.n + arch.n} spacers · arch R {P.ml_arch_r:.1f} mm "
        f"({P.ml_arch_r / IN:.3f} in) · strip 16.4 ft, "
        f"{P.ml_slack / IN:.1f} in slack",
        fontsize=9,
    )
    ax.legend(loc="lower right", fontsize=7, framealpha=0.9)
    ax.set_aspect("equal")
    ax.set_xlim(-w2 - 300, w2 + 300)
    ax.set_ylim(-190, P.ml_mirror_h + 90)
    ax.grid(alpha=0.12)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def render_section(out: Path) -> Path:
    """Cross-section through a straight spacer at a screw.

    Horizontal = out of the wall (+Z), vertical = radial, 0 at the spacer's
    outer face and +radial toward the mirror edge."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig = plt.figure(figsize=(13.5, 7.6), dpi=FIG_DPI)
    ax = fig.add_axes([0.02, 0.02, 0.60, 0.88])
    t, H = P.ml_spacer_t, P.ml_standoff
    gz0, gw, gd = P.ml_groove_z0, P.ml_groove_w, P.ml_groove_depth

    ax.add_patch(
        Rectangle((-26, -t - 34), 26, t + 34 + P.ml_inset + 34, fc="#e9e4dc",
                  ec=INK, hatch="///", lw=0.8)
    )
    ax.text(-13, P.ml_inset + 22, "WALL", ha="center", fontsize=8, color=INK)

    spacer = Rectangle((0, -t), H, t, fc=PART, ec=INK, lw=1.1, zorder=3)
    ax.add_patch(spacer)
    ax.add_patch(Rectangle((gz0, -gd), gw, gd, fc="white", ec=INK, lw=0.9, zorder=4))
    ax.add_patch(
        Rectangle(
            (gz0 + P.ml_groove_clear, -gd + P.ml_groove_over),
            P.ml_strip_w, P.ml_strip_t, fc=STRIP, ec=INK, lw=0.8, zorder=5,
        )
    )
    ax.annotate(
        f"Hue Solo sleeve {P.ml_strip_w:.1f} x {P.ml_strip_t:.1f}\n"
        f"emitting face {P.ml_groove_over:.1f} shy of the mouth",
        xy=(gz0 + gw / 2, -gd / 2), xytext=(H + 46, 34), fontsize=7,
        color=INK, ha="center",
        arrowprops=dict(arrowstyle="->", lw=0.8, color=INK),
    )

    # glass: back face on the spacer top, running out past the inset
    ax.add_patch(
        Rectangle((H, -t - 34), P.ml_mirror_t, t + 34 + P.ml_inset,
                  fc=GLASS, ec=INK, alpha=0.45, lw=1.0, zorder=3)
    )
    ax.text(
        H + P.ml_mirror_t + 4, -t - 4, "mirror\n(back face)",
        fontsize=7.5, color=INK, va="top",
    )

    # screw: counterbore + through-hole + shank into the stud
    yc = -t + P.ml_screw_r
    ax.add_patch(
        Rectangle((0, yc - P.ml_screw_d / 2), H, P.ml_screw_d, fc="white",
                  ec=INK, lw=0.8, zorder=6)
    )
    ax.add_patch(
        Rectangle((H - P.ml_cbore_depth, yc - P.ml_screw_head_d / 2),
                  P.ml_cbore_depth, P.ml_screw_head_d, fc="white", ec=INK,
                  lw=0.8, zorder=6)
    )
    ax.add_patch(
        Rectangle((-26, yc - 4.17 / 2), 26 + P.ml_screw_meat, 4.17,
                  fc="#b8bcc2", ec=INK, lw=0.7, zorder=7)
    )
    ax.add_patch(
        Rectangle((P.ml_screw_meat - 3.5, yc - 7.9 / 2), 3.5, 7.9,
                  fc="#b8bcc2", ec=INK, lw=0.7, zorder=7)
    )
    ax.annotate(
        f"#8 head, buried {P.ml_cbore_depth:.1f} deep\n"
        f"(bore {P.ml_screw_head_d:.1f}, through {P.ml_screw_d:.1f})",
        xy=(P.ml_screw_meat - 1, yc), xytext=(H + 26, yc - 26), fontsize=7,
        color=INK, ha="center",
        arrowprops=dict(arrowstyle="->", lw=0.8, color=INK),
    )

    # light out of the gap, washing the wall
    for dz in (-5, 1, 7):
        ax.annotate(
            "", xy=(gz0 + gw / 2 + dz, P.ml_inset + 24),
            xytext=(gz0 + gw / 2 + dz, -gd + P.ml_strip_t + 1),
            arrowprops=dict(arrowstyle="-|>", color="#d9a400", lw=1.4),
        )
    ax.text(
        gz0 + gw / 2 + 1, P.ml_inset + 30, "light out through the gap,\n"
        "washing the wall", ha="center", fontsize=8, color="#a87b00",
    )

    _dim(ax, (0, -t - 14), (H, -t - 14), f'standoff {H:.1f} (1.5in)', offset=(0, -4.5))
    _dim(ax, (-34, -t), (-34, 0), f"{t:.0f} thick", rot=90)
    _dim(ax, (gz0, 8), (gz0 + gw, 8), f"groove {gw:.1f}", offset=(0, 3.6), fs=7)
    _dim(ax, (gz0 - 7, -gd), (gz0 - 7, 0), f"{gd:.1f}", rot=90, fs=7)
    _dim(
        ax, (H - P.ml_cbore_depth, -t - 6), (H, -t - 6),
        f"counterbore {P.ml_cbore_depth:.1f}", offset=(0, -4.4), fs=7,
    )
    _dim(
        ax, (0, -t + 2), (P.ml_screw_meat, -t + 2),
        f"{P.ml_screw_meat:.0f} under the head", offset=(-2, -4.6), fs=7,
    )
    _dim(ax, (H + 8, 0), (H + 8, P.ml_inset), 'inset 2.2"', rot=90, fs=7)
    ax.plot([0, H + 34], [P.ml_inset] * 2, ls=(0, (4, 4)), color=GHOST, lw=0.7)
    ax.text(H + 34, P.ml_inset + 3, "mirror edge", fontsize=7, color=GHOST)

    ax.set_title(
        "Spacer cross-section (straight variant, cut at a screw) — mm\n"
        "prints wall-face-down: groove opens up, screw bores run horizontal",
        fontsize=9,
    )
    ax.set_aspect("equal")
    ax.set_xlim(-42, H + 78)
    ax.set_ylim(-t - 34, P.ml_inset + 46)
    ax.axis("off")
    fig.text(
        0.635, 0.90, "\n".join(report()), fontsize=6.8, family="monospace",
        va="top", color=INK,
    )
    fig.savefig(out)
    plt.close(fig)
    return out


RENDERS = {
    "mirror-light-layout": render_layout,
    "mirror-light-section": render_section,
}
