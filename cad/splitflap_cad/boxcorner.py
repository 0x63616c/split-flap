"""Storage-box corner brace — side quest, same boxes as the lid clip.

Three square plates meeting at one vertex: take a 30mm cube, keep the
bottom, back and left faces, throw the rest away. Slipped over a box
corner it stops the walls splaying, which is the other half of why the
stack sags.

Local frame: the corner vertex at the origin, plates running +X (left
face), +Y (back face) and +Z (bottom face) — so the inside of the brace
faces the box. Prints straight off the bed on any one plate.

View: `just cad view box-corner`.
"""

from build123d import Box, Pos

from .params import P
from .viewer import Scene


def box_corner():
    """The three-plate corner."""
    s, t = P.bcnr_size, P.bcnr_t
    h = s / 2  # plate mid-span, for the two in-plane axes
    return (
        Pos(h, h, t / 2) * Box(s, s, t)   # bottom
        + Pos(h, t / 2, h) * Box(s, t, s)  # back
        + Pos(t / 2, h, h) * Box(t, s, s)  # left
    )


def scene() -> Scene:
    return Scene().add(box_corner(), "box-corner")
