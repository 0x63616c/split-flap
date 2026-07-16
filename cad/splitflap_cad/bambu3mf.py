"""Bambu-Studio-native project 3MF export for the flap set.

Generic 3MFs (Mesher) carry display colors only — Bambu ignores them
for filament mapping. This writes the full BambuStudio package instead
(structure reverse-engineered from a Bambu 2.5 "Save Project" of one
flap): meshes in 3D/Objects/, composite objects + build items in
3D/3dmodel.model, and per-part extruder assignments in
Metadata/model_settings.config. Cards go to filament 1 (black), glyph
inlays to filament 2 (white). The vendored project_settings.config
carries Calum's P2S 0.4 profile so plates open slice-ready.

Layout: 5x5 flaps per 256mm plate -> 3 files for the 52-flap ring.
"""

import zipfile
from pathlib import Path

from .glyphflap import CHARSET, char_slug, flap_at
from .params import P

_DATA = Path(__file__).resolve().parent / "bambu"

_XML_HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n'
_MODEL_ATTRS = (
    'unit="millimeter" xml:lang="en-US" '
    'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
    'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
    'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
    'requiredextensions="p"'
)

_RELS = (
    _XML_HEAD
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
    "</Relationships>"
)

_MODEL_RELS = (
    _XML_HEAD
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    ' <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
    "</Relationships>"
)

_CONTENT_TYPES = (
    _XML_HEAD
    + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
    ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
    ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
    "</Types>"
)

# stable made-up UUIDs, varied per object/component by formatting in ids
_UUID = "{:08x}-abcd-4ef0-9d28-80fed5dfa1dc"

_TESS_TOL = 0.02  # mm chord tolerance — glyph curves stay crisp


def _f(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".")


def _mesh_object_xml(obj_id: int, solids, center) -> tuple[str, int]:
    """One 3MF mesh <object> from a list of solids (merged, possibly
    disjoint shells), centred on `center`. Returns (xml, face_count)."""
    cx, cy, cz = center
    vparts, tparts, off = [], [], 0
    for s in solids:
        verts, tris = s.tessellate(_TESS_TOL)
        vparts.extend(
            f'     <vertex x="{_f(v.X - cx)}" y="{_f(v.Y - cy)}" z="{_f(v.Z - cz)}"/>'
            for v in verts
        )
        tparts.extend(
            f'     <triangle v1="{a + off}" v2="{b + off}" v3="{c + off}"/>'
            for a, b, c in tris
        )
        off += len(verts)
    xml = (
        f'  <object id="{obj_id}" p:UUID="{_UUID.format(obj_id)}" type="model">\n'
        "   <mesh>\n    <vertices>\n" + "\n".join(vparts) + "\n    </vertices>\n"
        "    <triangles>\n" + "\n".join(tparts) + "\n    </triangles>\n"
        "   </mesh>\n  </object>"
    )
    return xml, len(tparts)


def export_bambu_plates(out_dir: Path, per_plate: int = 25) -> list[Path]:
    """Write plate-batched BambuStudio project 3MFs for all flaps."""
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = (_DATA / "project_settings.config").read_bytes()
    n = len(CHARSET)
    plates = [list(range(i, min(i + per_plate, n))) for i in range(0, n, per_plate)]
    written = []
    for pnum, idxs in enumerate(plates, start=1):
        path = out_dir / f"flaps_plate_{pnum}.3mf"
        _write_plate(path, idxs, settings)
        written.append(path)
    return written


def _write_plate(path: Path, idxs: list[int], settings: bytes) -> None:
    center = (0.0, P.flap_h / 2, P.flap_thick / 2)
    mesh_xmls, comp_objs, items, cfg_objs, instances = [], [], [], [], []
    mesh_id = 0
    cols, pitch_x, pitch_y = 5, 48.0, 42.0
    for k, i in enumerate(idxs):
        card, glyphs = flap_at(i)
        name = f"flap_{i:02d}_{char_slug(CHARSET[i])}"
        parts, cfg_parts, face_total = [], [], 0
        part_specs = [("card", card.solids(), 1)]
        if glyphs is not None:
            part_specs.append(("glyph", glyphs.solids(), 2))
        for pname, solids, extruder in part_specs:
            mesh_id += 1
            xml, faces = _mesh_object_xml(mesh_id, solids, center)
            mesh_xmls.append(xml)
            face_total += faces
            parts.append(
                f'    <component p:path="/3D/Objects/object_1.model" objectid="{mesh_id}" '
                f'p:UUID="{_UUID.format(0x10000 + mesh_id)}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
            )
            cfg_parts.append(
                f'    <part id="{mesh_id}" subtype="normal_part">\n'
                f'      <metadata key="name" value="{pname}"/>\n'
                f'      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                f'      <metadata key="extruder" value="{extruder}"/>\n'
                f'      <mesh_stat face_count="{faces}" edges_fixed="0" degenerate_facets="0" '
                f'facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n'
                "    </part>"
            )
        obj_id = 1000 + i
        comp_objs.append(
            f'  <object id="{obj_id}" p:UUID="{_UUID.format(obj_id)}" type="model">\n'
            "   <components>\n" + "\n".join(parts) + "\n   </components>\n  </object>"
        )
        r, c = divmod(k, cols)
        x = 128 + (c - 2) * pitch_x
        y = 128 + (2 - r) * pitch_y
        items.append(
            f'  <item objectid="{obj_id}" p:UUID="{_UUID.format(0x20000 + obj_id)}" '
            f'transform="1 0 0 0 1 0 0 0 1 {_f(x)} {_f(y)} {_f(P.flap_thick / 2)}" printable="1"/>'
        )
        cfg_objs.append(
            f'  <object id="{obj_id}">\n'
            f'    <metadata key="name" value="{name}"/>\n'
            f'    <metadata key="extruder" value="1"/>\n'
            f'    <metadata face_count="{face_total}"/>\n' + "\n".join(cfg_parts) + "\n  </object>"
        )
        instances.append(
            "    <model_instance>\n"
            f'      <metadata key="object_id" value="{obj_id}"/>\n'
            '      <metadata key="instance_id" value="0"/>\n'
            f'      <metadata key="identify_id" value="{100 + i}"/>\n'
            "    </model_instance>"
        )

    objects_model = (
        _XML_HEAD + f"<model {_MODEL_ATTRS}>\n"
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        " <resources>\n" + "\n".join(mesh_xmls) + "\n </resources>\n"
        f' <build p:UUID="{_UUID.format(0x30000)}"/>\n</model>'
    )
    main_model = (
        _XML_HEAD + f"<model {_MODEL_ATTRS}>\n"
        ' <metadata name="Application">BambuStudio-02.05.00.66</metadata>\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        " <resources>\n" + "\n".join(comp_objs) + "\n </resources>\n"
        f' <build p:UUID="{_UUID.format(0x40000)}">\n' + "\n".join(items) + "\n </build>\n</model>"
    )
    model_settings = (
        _XML_HEAD + "<config>\n" + "\n".join(cfg_objs) + "\n"
        "  <plate>\n"
        '    <metadata key="plater_id" value="1"/>\n'
        '    <metadata key="plater_name" value=""/>\n'
        '    <metadata key="locked" value="false"/>\n'
        '    <metadata key="filament_map_mode" value="Auto For Flush"/>\n'
        '    <metadata key="filament_maps" value="1 1"/>\n'
        + "\n".join(instances)
        + "\n  </plate>\n</config>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", main_model)
        z.writestr("3D/_rels/3dmodel.model.rels", _MODEL_RELS)
        z.writestr("3D/Objects/object_1.model", objects_model)
        z.writestr("Metadata/model_settings.config", model_settings)
        z.writestr("Metadata/project_settings.config", settings)
