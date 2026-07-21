"""splitflap_cad CLI — geometry side of the `just cad` tooling.

    python -m splitflap_cad list [--json]       # catalog: models + printables
    python -m splitflap_cad show NAME [--port]  # build + push one model to a viewer
    python -m splitflap_cad export [NAME]       # write STL(s) + STEP(s); no
                                                # NAME = all + flap 3MFs/Bambu
                                                # plates; "flaps" = artwork only
    python -m splitflap_cad render [NAME]       # write drawing PNGs

Driven by tools/ctl (Go): `just cad view [model]` runs a viewer + save
watcher in the current pane and calls `show` on every source change.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from .catalog import MODELS, PRINTABLE, RENDERS, SRC_TO_MODEL, STEP

FOCUS_PORT = 3940
EXPORT_DIR = Path(__file__).parent.parent / "export"
RENDER_DIR = EXPORT_DIR / "renders"


def _push(name, port):
    from ocp_vscode import show

    kwargs = MODELS[name].build().show_args()
    objects = kwargs.pop("objects")
    try:
        show(*objects, port=port, **kwargs)
    except Exception as exc:  # viewer down, most likely
        sys.exit(f"push {name} -> :{port} failed ({exc}); viewer up? try `just cad`")
    print(f"pushed {name} -> :{port}")


def _check(name, pool=MODELS):
    if name not in pool:
        sys.exit(f"unknown model {name!r} — have: {', '.join(pool)}")


def cmd_list(args):
    if args.json:
        print(
            json.dumps(
                {
                    "models": {name: m.help for name, m in MODELS.items()},
                    "printable": list(PRINTABLE),
                    "src_to_model": SRC_TO_MODEL,
                }
            )
        )
        return
    print("models (just cad view NAME):")
    for name, m in MODELS.items():
        print(f"  {name:<12} {m.help}")
    print("printable (just cad export NAME):")
    for name in PRINTABLE:
        print(f"  {name}{'  [+STEP]' if name in STEP else ''}")
    print("STEP only:")
    for name in STEP:
        if name not in PRINTABLE:
            print(f"  {name}")
    print("renders (python -m splitflap_cad render NAME):")
    for name in RENDERS:
        print(f"  {name}")


def cmd_show(args):
    _check(args.name)
    _push(args.name, args.port)


def _export_flap_artwork():
    """The flap set: per-flap colored 3MFs + plate projects that drag
    into Bambu Studio already two-coloured (PrusaSlicer format).
    Returns [(name, seconds)] timings."""
    from .flap3mf import export_plates
    from .glyphflap import export_flaps

    timings = []
    t0 = time.perf_counter()
    for out in export_flaps(EXPORT_DIR / "flaps"):
        print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB)")
    timings.append(("flaps", time.perf_counter() - t0))
    t0 = time.perf_counter()
    for out in export_plates(EXPORT_DIR / "plates"):
        print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB)")
    timings.append(("plates", time.perf_counter() - t0))
    return timings


def _print_timings(timings):
    print("timings:")
    for name, t in timings:
        print(f"  {name:<12} {t:6.1f}s")
    if len(timings) > 1:
        print(f"  {'total':<12} {sum(t for _, t in timings):6.1f}s")


def _wrote(out: Path):
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB)")


def cmd_export(args):
    from build123d import export_step, export_stl

    # "flaps" = the glyph card set (3MFs, not a PRINTABLE STL entry)
    flap_art = "flaps" in args.name
    names = [n for n in args.name if n != "flaps"] or (
        [] if flap_art else list(PRINTABLE) + [n for n in STEP if n not in PRINTABLE]
    )
    for name in names:
        _check(name, {**PRINTABLE, **STEP})
    EXPORT_DIR.mkdir(exist_ok=True)
    timings = []
    if flap_art:
        timings += _export_flap_artwork()
    for name in names:
        t0 = time.perf_counter()
        if name in PRINTABLE:
            out = EXPORT_DIR / f"{name}.stl"
            export_stl(PRINTABLE[name].build(), str(out))
            _wrote(out)
        if name in STEP:
            out = EXPORT_DIR / f"{name}.step"
            export_step(STEP[name].build(), str(out))
            _wrote(out)
        timings.append((name, time.perf_counter() - t0))
    if not args.name:  # bare `export` = everything, artwork included
        timings += _export_flap_artwork()
    _print_timings(timings)


def cmd_render(args):
    names = args.name or list(RENDERS)
    for name in names:
        _check(name, RENDERS)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    timings = []
    for name in names:
        t0 = time.perf_counter()
        _wrote(RENDERS[name].draw(RENDER_DIR / f"{name}.png"))
        timings.append((name, time.perf_counter() - t0))
    _print_timings(timings)


def main():
    p = argparse.ArgumentParser(prog="splitflap_cad")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="every model + printable part")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("show", help="build + push one model to a viewer")
    s.add_argument("name")
    s.add_argument("--port", type=int, default=FOCUS_PORT)

    s = sub.add_parser(
        "export",
        help="write STLs to cad/export/ (no NAME = all + flap 3MFs/plates; 'flaps' = artwork only)",
    )
    s.add_argument("name", nargs="*")

    s = sub.add_parser("render", help="write drawing PNGs to cad/export/renders/")
    s.add_argument("name", nargs="*")

    args = p.parse_args()
    {
        "list": cmd_list,
        "show": cmd_show,
        "export": cmd_export,
        "render": cmd_render,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
