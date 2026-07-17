"""Two-tone glyph flap generator (issue #8).

Each flap carries its WHOLE character as a white inlay on ONE face (the
front); the back is blank card. Single-sided so the whole letter prints
with one finish — putting the top half on the top face and the bottom
half on the bed face (as an earlier split-across-faces version did) left
each character half-smooth, half-textured. Print the flap letter-face
down or up as you like; every flap matches.

Frame: x centred on the card, y=0 at the pivot edge, glyph on the +Z
(front) face. View it: `just cad dev flap-glyph`.
"""

from functools import lru_cache
from pathlib import Path

from build123d import (
    Compound,
    Location,
    Plane,
    Pos,
    Rot,
    Text,
    TextAlign,
    extrude,
    scale,
)

from .flap import flap
from .params import P

_FONT = Path(__file__).resolve().parent.parent / "fonts"

# The drum's character ring, in order. Position 0 = blank = homing slot.
# len == P.drum_flap_count (asserted in tests). Flap i shows CHARSET[i].
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
    """Glyph face with the baseline exactly at y=0 (default text_align
    vertically centres, which floats the baseline)."""
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


def _glyph_face(char: str):
    """The whole-character face for `char`, sized to glyph_cap_h, x-centred
    (squeezed to glyph_w_max if wider), and centred in the flap's visible
    band. None for a blank flap."""
    if not char.strip():
        return None
    g = _text(char, P.glyph_cap_h / _cap_ratio())
    bb = g.bounding_box()
    # centre horizontally; squeeze width if the glyph is too wide
    g = Pos(-(bb.min.X + bb.max.X) / 2, 0, 0) * g
    if bb.size.X > P.glyph_w_max:
        g = scale(g, by=(P.glyph_w_max / bb.size.X, 1, 1))
    # centre the glyph's full height (incl. descenders) in the visible band
    band_lo = P.glyph_bottom_margin
    band_hi = P.flap_h - P.glyph_top_keepout
    target = (band_lo + band_hi) / 2
    g = Pos(0, target - (bb.min.Y + bb.max.Y) / 2, 0) * g
    return g


def _inlay(face, z0: float):
    """Extrude a glyph face into an inlay solid, z0 .. z0+depth."""
    return extrude(Plane.XY.offset(z0) * face, amount=P.glyph_inlay_depth, dir=(0, 0, 1))


def glyph_flap(char: str):
    """(card, glyphs) two-tone flap: the whole `char` inlaid flush into
    the +Z (front) face of the card, back left blank. `glyphs` is a
    white-inlay Compound, or None for a blank flap."""
    card = flap()
    face = _glyph_face(char)
    if face is None:
        return card, None
    inlay = _inlay(face, P.flap_thick - P.glyph_inlay_depth)
    glyphs = Compound(children=list(inlay.solids()))
    return card - glyphs, glyphs


def flap_at(i: int):
    """The i-th flap of the ring, carrying CHARSET[i]."""
    return glyph_flap(CHARSET[i])


def export_flaps(out_dir: Path) -> list[Path]:
    """Write every flap as a two-body coloured 3MF (black card + white
    glyph inlay) into out_dir. Colours go on leaf Solids — Mesher drops
    colours set on a Compound."""
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


def flap_set_demo() -> dict:
    """Contact sheet of the whole ring: every flap front in a grid."""
    cols, dx, dy = 13, 48.0, 42.0
    cards, glyphs = [], []
    for i in range(len(CHARSET)):
        r, c = divmod(i, cols)
        card, g = flap_at(i)
        loc = Location(Pos(c * dx, -r * dy, 0))
        cards.extend((loc * card).solids())
        if g is not None:
            glyphs.extend((loc * g).solids())
    return dict(
        objects=[Compound(children=cards), Compound(children=glyphs)],
        names=["cards", "glyphs"],
        colors=["dimgray", "white"],
    )


def glyph_flap_demo() -> dict:
    """A few flaps: A, plus W/M (width squeeze) and Q/? (descender,
    multi-solid, counters)."""
    objects, names, colors = [], [], []

    def add(char, loc=Location()):
        card, glyphs = glyph_flap(char)
        objects.append(loc * card)
        names.append(f"{char_slug(char)}_card")
        colors.append("dimgray")
        if glyphs is not None:
            objects.append(loc * glyphs)
            names.append(f"{char_slug(char)}_glyphs")
            colors.append("white")

    for k, ch in enumerate("AWMQ?"):
        add(ch, Location(Pos(k * 48, 0, 0)))
    return dict(objects=objects, names=names, colors=colors)
