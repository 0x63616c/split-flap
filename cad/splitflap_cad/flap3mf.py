"""Bambu-Studio-native project 3MF export for the flap set.

Learned the hard way (reading BambuStudio's bbs_3mf.cpp): Bambu reads
per-part colour ONLY from Metadata/model_settings.config, and it splits
a multi-colour object into volumes by SEPARATE COMPONENT MESHES — one
mesh per volume — not by triangle ranges inside a single mesh. So the
structure that colours is exactly what Bambu's own "Save Project"
writes (verified against a reference save):

  3D/Objects/object_1.model   — every part as its own <object> mesh
  3D/3dmodel.model            — one composite <object> per flap whose
                                <components> reference those meshes;
                                <build> places each flap on the plate
  Metadata/model_settings.config — per composite object, one <part> per
                                component with key="extruder" (card=1
                                black, glyph=2 white)

Meshes come from build123d's Mesher pipeline (BRepMesh + orientation-
aware winding) and are vertex-welded, so they're manifold — a
non-manifold mesh makes Bambu drop the part structure on import.

No print-settings file is bundled: Bambu keeps the user's active P2S
profile and takes only the extruder assignment. Load with File > Open
(or drag) — model_settings.config is read on both paths.
"""

from pathlib import Path

from .glyphflap import CHARSET, flap_at, flap_slug
from .params import P
from .threemf import write_zip_entries

_XML = '<?xml version="1.0" encoding="UTF-8"?>\n'
_MODEL_ATTRS = (
    'unit="millimeter" xml:lang="en-US" '
    'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
    'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
    'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
    'requiredextensions="p"'
)
_RELS = (
    _XML
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
    "</Relationships>"
)
_MODEL_RELS = (
    _XML
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    ' <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" '
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

_LIN_TOL = 0.02   # mm chord tolerance — keeps glyph curves crisp
_ANG_TOL = 0.2    # radians
_WELD_TOL = 1e-5  # mm — merge coincident tessellation vertices
_UUID = "{:08x}-abcd-4ef0-9d28-80fed5dfa1dc"


def _f(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".")


def _mesh_part(shape, center):
    """(vertices, triangles) for one part (a Compound of solids), meshed
    as a whole so shared edges tessellate consistently, then welded by
    position into a manifold mesh. Raw Shape.tessellate leaves reversed
    faces mis-wound and non-manifold, which makes Bambu discard the part
    structure — so use Mesher's BRepMesh + orientation-aware winding.
    Vertices are (x,y,z) tuples offset so `center` maps to the origin."""
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


def _mesh_object_xml(mesh_id: int, shape, center) -> tuple[str, int]:
    """A 3MF <object> mesh for one part. Returns (xml, face_count)."""
    verts, tris = _mesh_part(shape, center)
    vlines = "\n".join(f'     <vertex x="{_f(x)}" y="{_f(y)}" z="{_f(z)}"/>' for x, y, z in verts)
    tlines = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    xml = (
        f'  <object id="{mesh_id}" p:UUID="{_UUID.format(mesh_id)}" type="model">\n'
        "   <mesh>\n    <vertices>\n" + vlines + "\n    </vertices>\n"
        "    <triangles>\n" + tlines + "\n    </triangles>\n   </mesh>\n  </object>"
    )
    return xml, len(tris)


def export_plates(out_dir: Path, per_plate: int = 13) -> list[Path]:
    """Write plate-batched Bambu-native project 3MFs for all flaps."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # Drop stale plates from a prior run with a different per_plate, else a
    # smaller batch count leaves orphaned flaps_plate_N.3mf behind.
    for stale in out_dir.glob("flaps_plate_*.3mf"):
        stale.unlink()
    n = len(CHARSET)
    plates = [list(range(i, min(i + per_plate, n))) for i in range(0, n, per_plate)]
    written = []
    for pnum, idxs in enumerate(plates, start=1):
        path = out_dir / f"flaps_plate_{pnum}.3mf"
        _write_plate(path, idxs)
        written.append(path)
    return written


def export_flaps(out_dir: Path) -> list[Path]:
    """Per-flap Bambu-native project 3MFs — same two-tone extruder
    structure as the plates (single flap = one-flap plate), so each drags
    in already coloured. Named flap_<i>_<front><back> to show BOTH faces
    it carries (front = top of CHARSET[i], back = bottom of CHARSET[i+1])."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # Drop old names (single-char slugs, or stale wrap pairs) before rewrite.
    for stale in out_dir.glob("flap_*.3mf"):
        stale.unlink()
    written = []
    for i in range(len(CHARSET)):
        path = out_dir / f"flap_{i:02d}_{flap_slug(i)}.3mf"
        _write_plate(path, [i])
        written.append(path)
    return written


def _write_plate(path: Path, idxs: list[int]) -> None:
    center = (0.0, P.flap_h / 2, P.flap_thick / 2)
    # 5 columns x up-to-6 rows, grid centred on the 256mm bed.
    cols, pitch_x, pitch_y = 5, 48.0, 42.0
    rows = (len(idxs) + cols - 1) // cols
    bed = 128.0

    mesh_xmls, comp_objs, items, cfg_objs, instances = [], [], [], [], []
    mesh_id = 0
    for k, i in enumerate(idxs):
        card, glyphs = flap_at(i)
        name = f"flap_{i:02d}_{flap_slug(i)}"
        parts = [("card", card, 1)]
        if glyphs is not None:
            parts.append(("glyph", glyphs, 2))

        comps, cfg_parts = [], []
        for pname, shape, extruder in parts:
            mesh_id += 1
            xml, faces = _mesh_object_xml(mesh_id, shape, center)
            mesh_xmls.append(xml)
            comps.append(
                f'    <component p:path="/3D/Objects/object_1.model" objectid="{mesh_id}" '
                f'p:UUID="{_UUID.format(0x10000 + mesh_id)}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
            )
            cfg_parts.append(
                f'    <part id="{mesh_id}" subtype="normal_part">\n'
                f'      <metadata key="name" value="{name}_{pname}"/>\n'
                f'      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                f'      <metadata key="extruder" value="{extruder}"/>\n'
                f'      <mesh_stat face_count="{faces}" edges_fixed="0" degenerate_facets="0" '
                f'facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n'
                "    </part>"
            )

        obj_id = 1000 + i
        comp_objs.append(
            f'  <object id="{obj_id}" p:UUID="{_UUID.format(obj_id)}" type="model">\n'
            "   <components>\n" + "\n".join(comps) + "\n   </components>\n  </object>"
        )
        r, c = divmod(k, cols)
        x = bed + (c - (cols - 1) / 2) * pitch_x
        y = bed + ((rows - 1) / 2 - r) * pitch_y
        # Character i spans flap i's front + flap i+1's back. Printing
        # odd flaps front-down and even flaps back-down puts both halves
        # of every character on the SAME plate side (each char gets one
        # uniform finish on a textured bed). 180° about X through the
        # mesh centre keeps the footprint in place.
        rot = "1 0 0 0 -1 0 0 0 -1" if i % 2 else "1 0 0 0 1 0 0 0 1"
        items.append(
            f'  <item objectid="{obj_id}" p:UUID="{_UUID.format(0x20000 + obj_id)}" '
            f'transform="{rot} {_f(x)} {_f(y)} {_f(P.flap_thick / 2)}" printable="1"/>'
        )
        cfg_objs.append(
            f'  <object id="{obj_id}">\n'
            f'    <metadata key="name" value="{name}"/>\n'
            f'    <metadata key="extruder" value="1"/>\n' + "\n".join(cfg_parts) + "\n  </object>"
        )
        instances.append(
            "    <model_instance>\n"
            f'      <metadata key="object_id" value="{obj_id}"/>\n'
            '      <metadata key="instance_id" value="0"/>\n'
            f'      <metadata key="identify_id" value="{100 + i}"/>\n'
            "    </model_instance>"
        )

    objects_model = (
        _XML + f"<model {_MODEL_ATTRS}>\n"
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        " <resources>\n" + "\n".join(mesh_xmls) + "\n </resources>\n"
        f' <build p:UUID="{_UUID.format(0x30000)}"/>\n</model>'
    )
    main_model = (
        _XML + f"<model {_MODEL_ATTRS}>\n"
        ' <metadata name="Application">BambuStudio-02.05.00.66</metadata>\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        " <resources>\n" + "\n".join(comp_objs) + "\n </resources>\n"
        f' <build p:UUID="{_UUID.format(0x40000)}">\n' + "\n".join(items) + "\n </build>\n</model>"
    )
    model_settings = (
        _XML + "<config>\n" + "\n".join(cfg_objs) + "\n"
        "  <plate>\n"
        '    <metadata key="plater_id" value="1"/>\n'
        '    <metadata key="plater_name" value=""/>\n'
        '    <metadata key="locked" value="false"/>\n'
        '    <metadata key="filament_map_mode" value="Auto For Flush"/>\n'
        '    <metadata key="filament_maps" value="1 1"/>\n'
        + "\n".join(instances)
        + "\n  </plate>\n</config>"
    )
    write_zip_entries(
        path,
        [
            ("[Content_Types].xml", _CONTENT_TYPES),
            ("_rels/.rels", _RELS),
            ("3D/3dmodel.model", main_model),
            ("3D/_rels/3dmodel.model.rels", _MODEL_RELS),
            ("3D/Objects/object_1.model", objects_model),
            ("Metadata/model_settings.config", model_settings),
        ],
    )
