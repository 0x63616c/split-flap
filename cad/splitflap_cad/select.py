"""Named edge selectors — the fragile part of every fillet/chamfer.

Selection by geometric predicate breaks silently when nearby geometry
moves; naming the predicates keeps the intent readable and the magic
tolerances in one place. All selectors preserve exact predicates (the
golden geometry tests pin their behaviour).
"""

from build123d import Axis, GeomType


def bottom_edges(part) -> list:
    """The edge group on the part's lowest-Z face."""
    return list(part.edges().group_by(Axis.Z)[0])


def reach_under(edges, x: float) -> list:
    """Edges whose +X bounding-box reach stays under x — e.g. the bore
    mouth loop on a bottom face (arcs of an origin-centred circle reach
    exactly their radius)."""
    return [e for e in edges if e.bounding_box().max.X < x]


def reach_over(edges, x: float) -> list:
    """Edges whose +X bounding-box reach exceeds x — e.g. a bottom
    face's outer rim."""
    return [e for e in edges if e.bounding_box().max.X > x]


def vertical_edges_near_radius(part, r: float, tol: float = 0.3, z_below: float = 0.0) -> list:
    """Vertical (Z-parallel) edges whose centre sits within tol of
    radius r about the Z axis, below z_below — e.g. the seams where fin
    plates meet a hub wall."""
    return [
        e
        for e in part.edges().filter_by(Axis.Z)
        if abs((e.center().X**2 + e.center().Y**2) ** 0.5 - r) < tol
        and e.center().Z < z_below
    ]


def diametral_edges_at_z(
    part, z: float, half_t: float, r_max: float, z_tol: float = 0.1
) -> list:
    """Straight edges at height z (±z_tol) lying within half_t of a
    diametral plane (line-to-axis distance), inside radius r_max — e.g.
    the radial roots where fin faces meet a web. r_max keeps other
    near-diametral lines (like flap-slot sides out in the ring band)
    out of the selection."""

    def diam_dist(e):
        c, d = e.center(), e.tangent_at(0)
        return abs(c.X * d.Y - c.Y * d.X)

    return [
        e
        for e in part.edges().filter_by(GeomType.LINE)
        if abs(e.center().Z - z) < z_tol
        and diam_dist(e) < half_t
        and (e.center().X**2 + e.center().Y**2) ** 0.5 < r_max
    ]
