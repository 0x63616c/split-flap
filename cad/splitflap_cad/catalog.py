"""THE model registry — single source of truth for every viewable model
and printable part. Everything reads from here: `just cad list`, the
viewer push CLI (__main__.py), the watcher's save→model auto-focus, and
STL export.

Adding a part = one Model entry (plus a PRINTABLE entry if it prints).
Builders import lazily so listing the catalog never builds geometry.

Each builder returns kwargs for ocp_vscode.show(): at minimum
dict(objects=[...], names=[...]), optionally colors/alphas.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Model:
    help: str  # one line; powers `just cad list` and the docs
    src: str  # module stem that builds it — maps saved file -> model
    build: Callable[[], dict]


def _assembly():
    from .assembly import assembly_show_args

    return assembly_show_args()


def _unit():
    from .unit import full_unit, unit_plate

    try:
        u = full_unit()
    except FileNotFoundError:
        u = unit_plate()
    return dict(objects=[u], names=["unit"])


def _plate():
    from .unit import unit_plate

    return dict(objects=[unit_plate()], names=["plate"])


def _drum():
    from build123d import Pos, Rot

    from .drum import drum_inner, drum_outer

    return dict(
        objects=[drum_outer(), Pos(90, 0, 0) * Rot(180, 0, 0) * drum_inner()],
        names=["drum_outer", "drum_inner"],
        colors=["orange", "steelblue"],
    )


def _flap():
    from .flap import flap

    return dict(objects=[flap()], names=["flap"])


def _motor_byj():
    from .stepper28byj import stepper28byj

    return dict(objects=[stepper28byj()], names=["stepper28byj"])


def _motor_nema():
    from .motor import motor

    return dict(objects=[motor()], names=["motor_nema14"])


def _vendor():
    from .vendor import reference

    return dict(objects=[reference()], names=["vendor_unit"], alphas=[0.6])


MODELS = {
    "assembly": Model(
        "full unit: plate + motor + hall PCB + drum, vendor ghost overlaid",
        "assembly",
        _assembly,
    ),
    "unit": Model(
        "printable side plate (+ vendor fins/towers when STEP on disk)",
        "unit",
        _unit,
    ),
    "plate": Model("side plate only — no vendor fins/towers", "unit", _plate),
    "drum": Model("drum outer + inner, side by side", "drum", _drum),
    "flap": Model("single flap card", "flap", _flap),
    "motor-byj": Model("28BYJ-48 stepper (the real motor)", "stepper28byj", _motor_byj),
    "motor-nema": Model("NEMA 14 reference (possible later swap)", "motor", _motor_nema),
    "vendor": Model("vendor unit STEP, aligned to our frame", "vendor", _vendor),
}

# saved file stem -> model name, for the watcher's auto-focus.
# First entry wins on shared src (unit.py saves focus the full unit,
# not the plate-only view).
SRC_TO_MODEL: dict = {}
for _name, _m in MODELS.items():
    SRC_TO_MODEL.setdefault(_m.src, _name)


# --- printable solids (STL export) ---


def _p_unit():
    from .unit import full_unit

    return full_unit()


def _p_flap():
    from .flap import flap

    return flap()


def _p_drum_outer():
    from .drum import drum_outer

    return drum_outer()


def _p_drum_inner():
    from build123d import Rot

    from .drum import drum_inner

    # drum_inner's own frame hangs hub/barrel/fins into -Z (below the bed).
    # Flip so the web sits flat on the bed and the barrel points up.
    return Rot(180, 0, 0) * drum_inner()


PRINTABLE = {
    "unit": _p_unit,
    "flap": _p_flap,
    "drum-outer": _p_drum_outer,
    "drum-inner": _p_drum_inner,
}
