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
        "full unit: plate + motor + hall PCB + drum",
        "assembly",
    ),
    "unit": Model(
        "printable side plate with interconnect fins",
        "unit",
    ),
    "plate": Model("side plate only — no interconnect fins", "unit", "plate_scene"),
    "unit-nema": Model(
        "NEMA variant: plate + bridge + motor + drum ghosts",
        "unitnema",
    ),
    "plate-nema": Model(
        "NEMA side plate only — no fins/bridge", "unitnema", "plate_scene"
    ),
    "bridge-nema": Model(
        "NEMA bridge alone, local frame", "unitnema", "bridge_scene"
    ),
    "drum-byj": Model("drum outer + 28BYJ-bore inner, side by side", "drum"),
    "drum-nema": Model(
        "drum outer + NEMA-bore inner, side by side", "drum", "nema_scene"
    ),
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
    "motor-nema": Model("NEMA 14 pancake reference (ordered part)", "motor"),
    "fins": Model("parametric interconnect fins, alone", "fins"),
    "ipad-wall": Model(
        "SIDE QUEST iPad swivel-bar wall mount: wall + bracket + bar + iPad",
        "ipadwall",
    ),
    "ipad-bracket": Model(
        "SIDE QUEST two-piece bracket, exploded: channel body + full-face lid",
        "ipadwall",
        "two_piece_scene",
    ),
    "usb-grommet": Model(
        "SIDE QUEST 38mm USB wall-hole grommet, side slit",
        "usbgrommet",
    ),
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
    "unit-nema": Printable("unitnema", "full_unit_nema"),
    "bridge-nema": Printable("unitnema", "nema_bridge"),
    "holder": Printable("holder", "holder"),
    "flap": Printable("flap", "flap"),
    "drum-outer": Printable("drum", "drum_outer"),
    "drum-inner-byj": Printable("drum", "drum_inner_print"),
    "drum-inner-nema": Printable("drum", "drum_inner_nema_print"),
    "ipad-body": Printable("ipadwall", "bracket_body"),
    "ipad-lid": Printable("ipadwall", "bracket_lid"),
    "usb-grommet": Printable("usbgrommet", "usb_grommet"),
}
