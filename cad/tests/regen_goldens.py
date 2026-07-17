"""Regenerate the golden geometry snapshots in tests/golden/.

    cd cad && uv run python tests/regen_goldens.py [PART ...]

No PART = all. Run this ONLY when a geometry change is intended; commit
the regenerated goldens in the same commit as the change, so `git log
tests/golden/` reads as the history of every deliberate shape change.
"""

import json
import sys
import time
from pathlib import Path

from golden_registry import (
    ALL_PARTS,
    BREP_PARTS,
    FINGERPRINTS_NAME,
    GOLDEN_DIR_NAME,
    fingerprint,
)

GOLDEN = Path(__file__).parent / GOLDEN_DIR_NAME


def main(names: list[str]) -> None:
    from build123d import export_brep

    targets = names or list(ALL_PARTS)
    unknown = [n for n in targets if n not in ALL_PARTS]
    if unknown:
        sys.exit(f"unknown part(s) {unknown} — have: {', '.join(ALL_PARTS)}")

    GOLDEN.mkdir(exist_ok=True)
    fp_file = GOLDEN / FINGERPRINTS_NAME
    prints = json.loads(fp_file.read_text()) if fp_file.exists() else {}

    for name in targets:
        t0 = time.monotonic()
        part = ALL_PARTS[name]()
        prints[name] = fingerprint(part)
        line = f"{name}: fingerprint"
        if name in BREP_PARTS:
            out = GOLDEN / f"{name}.brep"
            export_brep(part, str(out))
            line += f" + {out.name} ({out.stat().st_size / 1024:.0f} KiB)"
        print(f"{line}  [{time.monotonic() - t0:.1f}s]")

    fp_file.write_text(json.dumps(prints, indent=1, sort_keys=True) + "\n")
    print(f"wrote {fp_file}")


if __name__ == "__main__":
    main(sys.argv[1:])
