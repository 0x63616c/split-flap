"""PROTOTYPE — two-tone glyph flap generator (issue #8 follow-up).

Recipe from docs/research/charset-artwork.md: draw the character once at
full size (spanning two flaps), split at cap_height/2, push the halves
apart by the gap compensation. Top half lands on the FRONT of flap N,
upright; bottom half of the NEXT character lands on the BACK via a 180°
rotation about X (one transform = correct after the flip). Glyphs are
flush white inlays pocketed into the black card, glyph_inlay_depth per
face.

Display frame here: x centred on the glyph, split line at y=0. That maps
straight onto the card frame (x centred, y=0 pivot edge) because the
pivot edge sits at the drum axis = the visible split line.

View it: `just cad dev flap-glyph`.
"""

from functools import lru_cache
from pathlib import Path

from build123d import (
    Compound,
    Location,
    Plane,
    Pos,
    Rectangle,
    Rot,
    Text,
    TextAlign,
    extrude,
    scale,
)

from .flap import flap
from .params import P

_FONT = Path(__file__).resolve().parent.parent / "fonts"
_BIG = 1000.0  # half-plane rectangle size for the split booleans

# The drum's character ring, in flip order. Position 0 = blank = homing
# slot. len == P.drum_flap_count (asserted in tests). Character i is
# displayed by flap i's front (top half) + flap i+1's back (bottom half).
CHARSET = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:.-?!$£#%°'&/+,"

# filename-safe slugs for the non-alphanumeric flaps
_SLUG = {
    " ": "blank", ":": "colon", ".": "period", "-": "hyphen", "?": "qmark",
    "!": "bang", "$": "dollar", "£": "gbp", "#": "hash", "%": "pct",
    "°": "deg", "'": "apos", "&": "amp", "/": "slash", "+": "plus",
    ",": "comma",
}


def char_slug(ch: str) -> str:
    return _SLUG.get(ch, ch)


@lru_cache
def _font_path() -> str:
    p = _FONT / P.glyph_font
    if not p.is_file():
        raise FileNotFoundError(f"glyph font missing: {p}")
    return str(p)


def _text(char: str, font_size: float):
    """Glyph faces with the baseline exactly at y=0 (see research doc:
    default text_align vertically centres, which floats the baseline)."""
    return Text(
        char,
        font_size=font_size,
        font_path=_font_path(),
        align=None,
        text_align=(TextAlign.CENTER, TextAlign.BOTTOM),
    )


@lru_cache
def _cap_ratio() -> float:
    """Cap height / em size for the bundled font (font_size is em, not caps)."""
    return _text("H", 100).bounding_box().max.Y / 100


def _glyph_halves(char: str):
    """(top, bottom) faces of `char` in display coords, or (None, None).

    Drawn at cap height 2*glyph_half_h, x-centred (squeezed to
    glyph_w_max if wider), split at cap/2 which lands exactly on y=0 —
    flush with the card's pivot edge. The letter's halves end up pushed
    apart by the *physical* hinge gap when displayed; no artwork offset.
    """
    if not char.strip():
        return None, None
    cap = 2 * P.glyph_half_h
    g = _text(char, cap / _cap_ratio())
    bb = g.bounding_box()
    g = Pos(-(bb.min.X + bb.max.X) / 2, 0, 0) * g
    if bb.size.X > P.glyph_w_max:
        g = scale(g, by=(P.glyph_w_max / bb.size.X, 1, 1))
    split = cap / 2
    # Descenders (Q , /) can reach past the keepout at the flap tip once
    # flipped to the back — lift the whole glyph just enough, spending
    # the top half's slack. Asserted to fit in tests.
    budget = P.flap_h - P.glyph_top_keepout
    lift = max(0.0, (split - bb.min.Y) - budget)
    if lift:
        g = Pos(0, lift, 0) * g
    top = g & Pos(0, split + _BIG / 2, 0) * Rectangle(_BIG, _BIG)
    bottom = g & Pos(0, split - _BIG / 2, 0) * Rectangle(_BIG, _BIG)
    # low glyphs (e.g. '.') can leave a half empty — return None for it
    def place(half):
        try:
            if not half.faces():
                return None
            return Pos(0, -split, 0) * half
        except AssertionError:  # empty boolean result has no wrapped shape
            return None

    return place(top), place(bottom)


def _inlay(face, z0: float):
    """Extrude a glyph face into an inlay solid, z0 .. z0+depth."""
    return extrude(Plane.XY.offset(z0) * face, amount=P.glyph_inlay_depth, dir=(0, 0, 1))


def glyph_flap(front_char: str, back_char: str):
    """(card, glyphs) two-tone flap.

    Front face (z=flap_thick) carries the top half of front_char; back
    face (z=0) carries the bottom half of back_char rotated 180° about X
    so it reads correctly once the flap has flipped down. `glyphs` is a
    white-inlay Compound, or None when both faces are blank.
    """
    card = flap()
    inlays = []
    top, _ = _glyph_halves(front_char)
    if top is not None:
        inlays.append(_inlay(top, P.flap_thick - P.glyph_inlay_depth))
    _, bottom = _glyph_halves(back_char)
    if bottom is not None:
        inlays.append(_inlay(Rot(180, 0, 0) * bottom, 0))
    if not inlays:
        return card, None
    glyphs = Compound(children=[s for i in inlays for s in i.solids()])
    return card - glyphs, glyphs


def flap_at(i: int):
    """The i-th flap of the ring: front = top of CHARSET[i], back =
    bottom of CHARSET[i+1] (wrapping)."""
    return glyph_flap(CHARSET[i], CHARSET[(i + 1) % len(CHARSET)])


def export_flaps(out_dir: Path) -> list[Path]:
    """Write every flap as a two-body colored 3MF (black card + white
    glyph inlays) into out_dir. Bambu Studio maps body colors to
    filaments on import. Colors go on leaf Solids — Mesher drops colors
    set on a Compound."""
    from build123d import Color, Mesher

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for i, ch in enumerate(CHARSET):
        card, glyphs = flap_at(i)
        path = out_dir / f"flap_{i:02d}_{char_slug(ch)}.3mf"
        m = Mesher()
        for s in card.solids():
            s.color = Color("black")
            s.label = "card"
            m.add_shape(s)
        if glyphs is not None:
            for s in glyphs.solids():
                s.color = Color("white")
                s.label = "glyph"
                m.add_shape(s)
        m.write(str(path))
        written.append(path)
    return written


def glyph_flap_demo() -> dict:
    """show() kwargs: assembled 'A' (top flap + flipped-down next flap)
    plus loose demo flaps — W/M (width squeeze) and Q/? (multi-solid,
    counters)."""
    objects, names, colors = [], [], []

    def add(pair, name, loc=Location()):
        card, glyphs = pair
        objects.append(loc * card)
        names.append(f"{name}_card")
        colors.append("dimgray")
        if glyphs is not None:
            objects.append(loc * glyphs)
            names.append(f"{name}_glyphs")
            colors.append("white")

    add(glyph_flap("A", "B"), "top_A")  # standing, front visible
    # flipped down, back visible, dropped by the physical hinge gap
    add(
        glyph_flap("B", "A"),
        "bottom_A",
        Location(Pos(0, -2 * P.glyph_gap_comp, 0)) * Location(Rot(180, 0, 0)),
    )
    add(glyph_flap("W", "M"), "wide_WM", Location(Pos(55, 0, 0)))
    add(glyph_flap("Q", "?"), "multi_Q?", Location(Pos(110, 0, 0)))
    return dict(objects=objects, names=names, colors=colors)
