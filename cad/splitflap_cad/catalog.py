"""THE model registry — single source of truth for every viewable model
and printable part. Everything reads from here: `just cad list`, the
viewer push CLI (__main__.py), ctl's save→model auto-focus
(src_to_model in `list --json`), and STL export.

Pure data: a Model is (help, module stem, scene attr); a Printable is
(module stem, part attr). Modules import lazily on build, so listing
the catalog never builds geometry. Convention: every part module
exports `scene()` (extra views get their own attr, e.g. plate_scene)
and plain part builders for printables.

Adding a part = its module + one Model entry (+ a Printable entry if it
prints).
"""

from dataclasses import dataclass
from importlib import import_module


def _attr(src: str, name: str):
    return getattr(import_module(f".{src}", __package__), name)


@dataclass(frozen=True)
class Model:
    help: str  # one line; powers `just cad list` and the docs
    src: str  # module stem that builds it — maps saved file -> model
    scene: str = "scene"  # module attr returning a viewer.Scene

    def build(self):
        return _attr(self.src, self.scene)()


@dataclass(frozen=True)
class Printable:
    src: str  # module stem
    part: str  # module attr returning the printable solid

    def build(self):
        return _attr(self.src, self.part)()


MODELS = {
    "assembly": Model(
        "full unit: plate + motor + hall PCB + drum, vendor ghost overlaid",
        "assembly",
    ),
    "unit": Model(
        "printable side plate (+ vendor fins/towers when STEP on disk)",
        "unit",
    ),
    "plate": Model("side plate only — no vendor fins/towers", "unit", "plate_scene"),
    "drum": Model("drum outer + inner, side by side", "drum"),
    "holder": Model(
        "PROTOTYPE flap-loading jig: ring + radial slots, drum ghost",
        "holder",
    ),
    "flap": Model("single flap card", "flap"),
    "flap-set": Model(
        "contact sheet: all 52 flap fronts + backs (backs flipped as displayed)",
        "glyphflap",
        "flap_set_demo",
    ),
    "flap-glyph": Model(
        "PROTOTYPE two-tone glyph flaps: assembled A + W/M + Q/? demos",
        "glyphflap",
        "glyph_flap_demo",
    ),
    "motor-byj": Model("28BYJ-48 stepper (the real motor)", "stepper28byj"),
    "motor-nema": Model("NEMA 14 reference (possible later swap)", "motor"),
    "vendor": Model("vendor unit STEP, aligned to our frame", "vendor"),
}

# saved file stem -> model name, for ctl's save auto-focus.
# First entry wins on shared src (unit.py saves focus the full unit,
# not the plate-only view).
SRC_TO_MODEL: dict = {}
for _name, _m in MODELS.items():
    SRC_TO_MODEL.setdefault(_m.src, _name)


# --- printable solids (STL export) ---

PRINTABLE = {
    "unit": Printable("unit", "full_unit"),
    "holder": Printable("holder", "holder"),
    "flap": Printable("flap", "flap"),
    "drum-outer": Printable("drum", "drum_outer"),
    "drum-inner": Printable("drum", "drum_inner_print"),
}
