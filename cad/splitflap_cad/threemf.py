"""Deterministic 3MF output — identical geometry must give identical
bytes, so `git diff cad/export/` is a real signal (docs/plans/
cad-refactor.md, verification L1).

Two nondeterminism sources, two fixes:
- our own zip writes stamp wall-clock entry dates -> write_zip_entries
  pins every entry to 1980-01-01 (DOS epoch).
- lib3mf (build123d Mesher) generates fresh random p:UUIDs per run ->
  canonicalize_3mf rewrites them as a deterministic sequence in order
  of first appearance and repacks the zip with pinned dates.
"""

import re
import zipfile
from pathlib import Path

_EPOCH = (1980, 1, 1, 0, 0, 0)
_UUID_RE = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def write_zip_entries(path: Path, entries: list[tuple[str, str | bytes]]) -> None:
    """Write a zip whose bytes depend only on `entries` (pinned dates,
    fixed order, one compression level)."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in entries:
            info = zipfile.ZipInfo(name, date_time=_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, content)


def canonicalize_3mf(path: Path) -> None:
    """Rewrite a just-written 3MF in place: every UUID replaced by a
    deterministic sequence (stable while the model structure is stable),
    zip entry dates pinned. Geometry bytes untouched."""
    with zipfile.ZipFile(path) as z:
        entries = [(i.filename, z.read(i.filename)) for i in z.infolist()]

    seen: dict[bytes, bytes] = {}

    def stamp(m: re.Match) -> bytes:
        u = m.group(0)
        if u not in seen:
            n = len(seen)
            seen[u] = f"{n:08x}-0000-4000-8000-000000000000".encode()
        return seen[u]

    entries = [(name, _UUID_RE.sub(stamp, data)) for name, data in entries]
    write_zip_entries(path, entries)
