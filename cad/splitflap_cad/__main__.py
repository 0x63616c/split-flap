"""splitflap_cad CLI — one entrypoint for the whole viewer/export flow.

    python -m splitflap_cad list                # catalog: every model + printable
    python -m splitflap_cad show NAME [--port]  # build + push one model
    python -m splitflap_cad sync [FILE]         # assembly -> :3939, focus -> :3940
    python -m splitflap_cad pin [NAME|--clear]  # pin/unpin the focus model
    python -m splitflap_cad export [NAME]       # write STL(s); no NAME = all
                                                # + flap 3MFs/Bambu plates;
                                                # NAME "flaps" = artwork only

Normally driven by `just cad` (viewers + cmux panes + save watcher); see
tools/cad/up.sh. Two viewers: :3939 always shows the full assembly, :3940
shows the focus model — the pinned one, else the model of the last-saved
file (sync FILE), else the last focus.
"""

import argparse
import json
import sys
from pathlib import Path

from .catalog import MODELS, PRINTABLE, SRC_TO_MODEL

ASSEMBLY_PORT = 3939
FOCUS_PORT = 3940
STATE_FILE = Path(__file__).parent.parent / ".viewer-state.json"
EXPORT_DIR = Path(__file__).parent.parent / "export"


def _state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(st):
    STATE_FILE.write_text(json.dumps(st) + "\n")


def _push(name, port):
    from ocp_vscode import show

    kwargs = MODELS[name].build()
    objects = kwargs.pop("objects")
    try:
        show(*objects, port=port, **kwargs)
    except Exception as exc:  # viewer down, most likely
        sys.exit(f"push {name} -> :{port} failed ({exc}); viewer up? try `just cad`")
    print(f"pushed {name} -> :{port}")


def _check(name, pool=MODELS):
    if name not in pool:
        sys.exit(f"unknown model {name!r} — have: {', '.join(pool)}")


def cmd_list(_args):
    print("models (just cad dev NAME):")
    for name, m in MODELS.items():
        print(f"  {name:<12} {m.help}")
    print("printable (just cad export NAME):")
    for name in PRINTABLE:
        print(f"  {name}")


def cmd_show(args):
    _check(args.name)
    _push(args.name, args.port)


def cmd_pin(args):
    st = _state()
    if args.clear:
        st.pop("pin", None)
        print("pin cleared — focus follows the last-saved file")
    else:
        _check(args.name)
        st["pin"] = args.name
        print(f"pinned focus: {args.name}")
    _save_state(st)


def cmd_sync(args):
    st = _state()
    focus = st.get("pin")
    if not focus and args.file:
        focus = SRC_TO_MODEL.get(Path(args.file).stem)
    if not focus:
        focus = st.get("last", "assembly")
    st["last"] = focus
    _save_state(st)
    _push("assembly", ASSEMBLY_PORT)
    _push(focus, FOCUS_PORT)


def _export_flap_artwork():
    """The flap set: per-flap colored 3MFs + plate projects that drag
    into Bambu Studio already two-coloured (PrusaSlicer format)."""
    from .glyphflap import export_flaps
    from .prusa3mf import export_prusa_plates

    for out in export_flaps(EXPORT_DIR / "flaps"):
        print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB)")
    for out in export_prusa_plates(EXPORT_DIR / "plates"):
        print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB)")


def cmd_export(args):
    from build123d import export_stl

    # "flaps" = the glyph card set (3MFs, not a PRINTABLE STL entry)
    if args.name == "flaps":
        _export_flap_artwork()
        return
    names = [args.name] if args.name else list(PRINTABLE)
    for name in names:
        _check(name, PRINTABLE)
    EXPORT_DIR.mkdir(exist_ok=True)
    for name in names:
        out = EXPORT_DIR / f"{name}.stl"
        export_stl(PRINTABLE[name](), str(out))
        print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KiB)")
    if not args.name:
        _export_flap_artwork()


def main():
    p = argparse.ArgumentParser(prog="splitflap_cad")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="every model + printable part")

    s = sub.add_parser("show", help="build + push one model to a viewer")
    s.add_argument("name")
    s.add_argument("--port", type=int, default=FOCUS_PORT)

    s = sub.add_parser("pin", help="pin the focus model (bottom pane)")
    s.add_argument("name", nargs="?")
    s.add_argument("--clear", action="store_true")

    s = sub.add_parser("sync", help="push assembly + focus (watcher entrypoint)")
    s.add_argument("file", nargs="?")

    s = sub.add_parser(
        "export",
        help="write STLs to cad/export/ (no NAME = all + flap 3MFs/plates; 'flaps' = artwork only)",
    )
    s.add_argument("name", nargs="?")

    args = p.parse_args()
    if args.cmd == "pin" and not args.clear and not args.name:
        p.error("pin needs a NAME or --clear")
    {
        "list": cmd_list,
        "show": cmd_show,
        "pin": cmd_pin,
        "sync": cmd_sync,
        "export": cmd_export,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
