"""PrusaSlicer-style 3MF export — the format David Kingsman's flaps use,
confirmed to drag-and-drop into Bambu Studio already two-coloured.

Why not the Bambu-native package (bambu3mf.py): Bambu only reads its own
Metadata/model_settings.config on the *project-open* path; a plain
Import/drag strips it and everything lands on filament 1. PrusaSlicer's
Metadata/Slic3r_PE_model.config, by contrast, Bambu honours on the
generic load path — so these files come in coloured however you open
them.

Structure (one flap = one object):
  - 3D/3dmodel.model: a single merged mesh per flap (card triangles
    first, then glyph triangles), vertices already in object space.
    Build items place each flap on the plate.
  - Metadata/Slic3r_PE_model.config: per object, one <volume
    firstid=.. lastid=..> per part with an `extruder` value. Card = 1
    (black), glyphs = 2 (white). ids are inclusive triangle indices.

No print-settings file: Bambu keeps the user's active P2S profile and
only takes the extruder assignment.
"""

import zipfile
from pathlib import Path

from .glyphflap import CHARSET, char_slug, flap_at
from .params import P

_XML = '<?xml version="1.0" encoding="UTF-8"?>\n'
_MODEL_OPEN = (
    '<model unit="millimeter" xml:lang="en-US" '
    'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
    'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">\n'
)
_RELS = (
    _XML
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
    "</Relationships>"
)
_CONTENT_TYPES = (
    _XML
    + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
    ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
    ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
    "</Types>"
)

_LIN_TOL = 0.02  # mm chord tolerance — keeps glyph curves crisp
_ANG_TOL = 0.2   # radians
_WELD_TOL = 1e-5  # mm — merge coincident tessellation vertices


def _f(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".")


def _mesh_part(shape, center):
    """(vertices, triangles) for one part (a Compound of solids), meshed
    as a whole so shared edges tessellate consistently, then welded by
    position into a manifold mesh. Uses build123d's Mesher pipeline
    (BRepMesh + orientation-aware winding) — raw Shape.tessellate leaves
    reversed faces mis-wound and the mesh non-manifold. vertices are
    (x,y,z) tuples offset so `center` maps to the origin; triangles are
    (i,j,k) index tuples."""
    from build123d.mesher import Mesher

    cx, cy, cz = center
    raw_v, raw_t = Mesher._mesh_shape(shape, _LIN_TOL, _ANG_TOL)
    idx, verts, remap = {}, [], {}
    for i, (x, y, z) in enumerate(raw_v):
        key = (round(x / _WELD_TOL), round(y / _WELD_TOL), round(z / _WELD_TOL))
        if key not in idx:
            idx[key] = len(verts)
            verts.append((x - cx, y - cy, z - cz))
        remap[i] = idx[key]
    tris = [(remap[a], remap[b], remap[c]) for a, b, c in raw_t]
    return verts, tris


def _flap_object(obj_id: int, i: int, center):
    """(model_xml, config_xml, name) for one flap: a merged mesh plus the
    volume ranges naming card (extruder 1) and glyph (extruder 2)."""
    card, glyphs = flap_at(i)
    name = f"flap_{i:02d}_{char_slug(CHARSET[i])}"

    # Merge card + glyph into ONE mesh (each a manifold shell); record
    # each part's inclusive triangle-index range for the config file.
    parts = [("card", card, 1)]
    if glyphs is not None:
        parts.append(("glyph", glyphs, 2))

    verts, tris, volumes = [], [], []
    for pname, shape, ext in parts:
        vbase, tbase = len(verts), len(tris)
        vv, tt = _mesh_part(shape, center)
        verts.extend(vv)
        tris.extend((a + vbase, b + vbase, c + vbase) for a, b, c in tt)
        volumes.append((tbase, len(tris) - 1, pname, ext))

    vlines = "\n".join(f'     <vertex x="{_f(x)}" y="{_f(y)}" z="{_f(z)}"/>' for x, y, z in verts)
    tlines = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    model_xml = (
        f'  <object id="{obj_id}" type="model">\n   <mesh>\n'
        "    <vertices>\n" + vlines + "\n    </vertices>\n"
        "    <triangles>\n" + tlines + "\n    </triangles>\n"
        "   </mesh>\n  </object>"
    )

    vol_xml = "\n".join(
        f'  <volume firstid="{a}" lastid="{b}">\n'
        f'   <metadata type="volume" key="name" value="{name}_{pname}"/>\n'
        f'   <metadata type="volume" key="volume_type" value="ModelPart"/>\n'
        f'   <metadata type="volume" key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
        f'   <metadata type="volume" key="extruder" value="{ext}"/>\n'
        "  </volume>"
        for a, b, pname, ext in volumes
    )
    config_xml = (
        f'  <object id="{obj_id}" instances_count="1">\n'
        f'  <metadata type="object" key="name" value="{name}"/>\n' + vol_xml + "\n </object>"
    )
    return model_xml, config_xml, name


def export_prusa_plates(out_dir: Path, per_plate: int = 25) -> list[Path]:
    """Write plate-batched PrusaSlicer-style project 3MFs for all flaps."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(CHARSET)
    plates = [list(range(i, min(i + per_plate, n))) for i in range(0, n, per_plate)]
    written = []
    for pnum, idxs in enumerate(plates, start=1):
        path = out_dir / f"flaps_plate_{pnum}.3mf"
        _write_plate(path, idxs)
        written.append(path)
    return written


def _write_plate(path: Path, idxs: list[int]) -> None:
    center = (0.0, P.flap_h / 2, P.flap_thick / 2)
    cols, pitch_x, pitch_y = 5, 48.0, 42.0
    model_objs, config_objs, items = [], [], []
    for k, i in enumerate(idxs):
        obj_id = k + 1
        m_xml, c_xml, _ = _flap_object(obj_id, i, center)
        model_objs.append(m_xml)
        config_objs.append(c_xml)
        r, c = divmod(k, cols)
        x = 128 + (c - 2) * pitch_x
        y = 128 + (2 - r) * pitch_y
        items.append(
            f'  <item objectid="{obj_id}" '
            f'transform="1 0 0 0 1 0 0 0 1 {_f(x)} {_f(y)} {_f(P.flap_thick / 2)}" printable="1"/>'
        )

    model = (
        _XML + _MODEL_OPEN
        + ' <metadata name="slic3rpe:Version3mf">1</metadata>\n'
        ' <metadata name="Application">split-flap-cad</metadata>\n'
        " <resources>\n" + "\n".join(model_objs) + "\n </resources>\n"
        " <build>\n" + "\n".join(items) + "\n </build>\n</model>"
    )
    config = _XML + "<config>\n" + "\n".join(config_objs) + "\n</config>"

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/Slic3r_PE_model.config", config)
