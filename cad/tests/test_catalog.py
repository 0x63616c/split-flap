"""The catalog is the single registry — keep it honest without building
geometry (builders are lazy; nothing here should touch build123d)."""

from pathlib import Path

from splitflap_cad.catalog import MODELS, PRINTABLE, RENDERS, SRC_TO_MODEL

SRC = Path(__file__).parent.parent / "splitflap_cad"


def test_every_model_documented():
    for name, m in MODELS.items():
        assert m.help.strip(), f"{name} needs a help line"


def test_every_src_is_a_real_module():
    for name, m in MODELS.items():
        assert (SRC / f"{m.src}.py").exists(), f"{name}: no module {m.src}.py"


def test_src_map_covers_all_models():
    # models may share a src (unit/plate); the map keeps the first, and
    # every mapped name must be a real model
    assert set(SRC_TO_MODEL.values()) <= set(MODELS)
    assert set(SRC_TO_MODEL) == {m.src for m in MODELS.values()}


def test_printable_builders_exist():
    assert set(PRINTABLE) == {
        "unit",
        "unit-nema",
        "bridge-nema",
        "flap",
        "drum-outer",
        "drum-inner-byj",
        "drum-inner-nema",
        "holder",
        "ipad-body",
        "ipad-lid",
        "grommet-usb",
        "grommet-bathroom",
        "poop-bucket",
        "mirror-spacer-straight",
        "mirror-spacer-arch",
        "mirror-spacer-corner",
    }


def test_render_registry_points_at_real_modules():
    for name, entry in RENDERS.items():
        assert (SRC / f"{entry.src}.py").exists(), f"{name}: no module {entry.src}.py"
