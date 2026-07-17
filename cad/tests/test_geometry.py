"""Golden-geometry guard: refactors must not change any part's shape.

Layers (see docs/plans/cad-refactor.md):
- fingerprint (default run): volume/area/bbox/COM vs tests/golden/
  fingerprints.json. Catches ~all accidental geometry changes, fast
  enough for every commit.
- XOR (-m slow): boolean symmetric difference vs the golden BREPs —
  definitive shape identity, independent of construction order. On
  failure the residual volume IS the diff.
- smoke (-m slow): every catalog model builds.

Intended change? Regenerate: `uv run python tests/regen_goldens.py`
(same commit as the change).
"""

import json
from pathlib import Path

import pytest
from golden_registry import (
    ABS_TOL,
    ALL_PARTS,
    BREP_PARTS,
    FINGERPRINTS_NAME,
    GOLDEN_DIR_NAME,
    REL_TOL,
    XOR_TOL,
    fingerprint,
)

GOLDEN = Path(__file__).parent / GOLDEN_DIR_NAME

_built: dict = {}


def build(name):
    """Build each part once per test session (fingerprint + XOR share)."""
    if name not in _built:
        _built[name] = ALL_PARTS[name]()
    return _built[name]


@pytest.fixture(scope="session")
def goldens() -> dict:
    fp = GOLDEN / FINGERPRINTS_NAME
    if not fp.exists():
        pytest.fail(f"{fp} missing — run: uv run python tests/regen_goldens.py")
    return json.loads(fp.read_text())


@pytest.mark.parametrize("name", list(ALL_PARTS))
def test_fingerprint(name, goldens):
    want = goldens.get(name)
    if want is None:
        pytest.fail(f"no golden fingerprint for {name} — regen goldens")
    got = fingerprint(build(name))
    for key in ("volume", "area"):
        assert got[key] == pytest.approx(want[key], rel=REL_TOL), (
            f"{name}.{key}: golden {want[key]:.6f} -> {got[key]:.6f} "
            f"(Δ {got[key] - want[key]:+.6f})"
        )
    for key in ("bbox_min", "bbox_max", "com"):
        assert got[key] == pytest.approx(want[key], abs=ABS_TOL), (
            f"{name}.{key}: golden {want[key]} -> {got[key]}"
        )


def _residual(a, b) -> float:
    d = a - b
    return 0.0 if d is None else abs(d.volume)


def _grid_mismatch(new, golden, cells: int = 8) -> float:
    """Fallback shape compare for parts where OCC's boolean breaks down
    on fully-coincident faces (signature: empty intersection + residual
    == full volume on both sides). `part & box` stays robust, so compare
    material per grid cell; returns the worst per-cell volume mismatch
    in mm³. A local edit that keeps every cell's volume identical to
    1e-3 mm³ is beyond any accidental refactor slip."""
    from build123d import Box, Pos

    bb = new.bounding_box()
    dx, dy, dz = (
        (bb.max.X - bb.min.X) / cells,
        (bb.max.Y - bb.min.Y) / cells,
        (bb.max.Z - bb.min.Z) / cells,
    )
    worst = 0.0
    for i in range(cells):
        for j in range(cells):
            for k in range(cells):
                cell = Pos(
                    bb.min.X + (i + 0.5) * dx,
                    bb.min.Y + (j + 0.5) * dy,
                    bb.min.Z + (k + 0.5) * dz,
                ) * Box(dx, dy, dz)
                vn = (new & cell).volume
                vg = (golden & cell).volume
                worst = max(worst, abs(vn - vg))
    return worst


@pytest.mark.slow
@pytest.mark.parametrize("name", list(BREP_PARTS))
def test_xor_vs_golden_brep(name):
    from build123d import import_brep

    path = GOLDEN / f"{name}.brep"
    if not path.exists():
        pytest.fail(f"{path} missing — run: uv run python tests/regen_goldens.py")
    golden = import_brep(str(path))
    new = build(name)
    extra, missing = _residual(new, golden), _residual(golden, new)
    if extra < XOR_TOL and missing < XOR_TOL:
        return
    # boolean breakdown (not a real diff): identical twins with fully
    # coincident faces can defeat BOPAlgo — residual comes back as the
    # WHOLE part on both sides while the intersection comes back empty.
    # A genuine geometry change never looks like that. Fall back to the
    # per-cell volume comparison.
    broke = (
        abs(extra - new.volume) < 1.0
        and abs(missing - golden.volume) < 1.0
        and (new & golden).volume < XOR_TOL
    )
    if broke:
        worst = _grid_mismatch(new, golden)
        assert worst < XOR_TOL, (
            f"{name} differs from golden (grid compare, XOR unusable): "
            f"worst cell mismatch {worst:.4f} mm³"
        )
        return
    pytest.fail(
        f"{name} geometry differs from golden: {extra:.4f} mm³ added, "
        f"{missing:.4f} mm³ removed (view: subtract golden/{name}.brep)"
    )


@pytest.mark.slow
def test_every_catalog_model_builds():
    from splitflap_cad.catalog import MODELS

    for name, m in MODELS.items():
        kwargs = m.build()
        assert kwargs.get("objects"), f"{name} built no objects"
