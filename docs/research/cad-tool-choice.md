# Code-first CAD tool choice

Resolves [#2 — Choose code-first CAD tool Claude Code can drive](https://github.com/0x63616c/split-flap/issues/2).
Research date: 2026-07-14. Candidates: OpenSCAD (nightly + Manifold + BOSL2), build123d, CadQuery.

## Recommendation: build123d

Python, OCCT B-rep kernel, `pip install build123d` (works on Apple Silicon). Current release 0.11.1 (2026-07-02), very active.

### Why it wins for this project

1. **Geometry introspection → testable CAD.** `part.volume`, `part.bounding_box()`, `faces().filter_by(...)`, `is_valid()` — dimensional and clearance checks become plain pytest asserts. This is the strongest possible feedback loop for Claude-driven design; OpenSCAD has *zero* geometry querying (its biggest weakness — verification there is PNGs and hand-carried arithmetic only).
2. **Native fillets/chamfers** on selected edges (real B-rep). OpenSCAD needs BOSL2 mask workarounds; painful on complex intersections like drum-to-spoke blends.
3. **Export pipeline fits Bambu exactly.** build123d's `Mesher` writes multi-shape 3MF with per-shape color and quality controls. Bambu Studio imports generic 3MF as "geometry only" but keeps objects + standard-3MF colors, and lets you assign filament per object. This directly serves two-tone (white/black) flap printing later. CadQuery notably *cannot* do per-part-color 3MF (open feature request, CQ #1345).
4. **Joints for the mechanism.** `RigidJoint`/`RevoluteJoint` etc. with `connect_to()` — drum-on-axle, flap-pivot relationships expressible in code (placement, not a constraint solver — fine for this).
5. **Agent ecosystem is converging on it.** build123d-mcp (top of CADGenBench 06/2026), cad-khana (interference/wall-thickness/overhang diagnostics for print-oriented agent loops), published Claude Code skills. Mitigates the one LLM weakness (pre-1.0 API churn) by keeping current docs/cheatsheet in context and pinning the version.
6. **Plain Python** — headless export is just `python export.py`; runs in CI; no special CLI.

### Why not the others

- **OpenSCAD**: last stable release 2021.01 — must run nightly. Fast now (Manifold backend, default in nightlies) and best-in-class LLM training data, plus BOSL2 gears/hinges library is genuinely great. But: no geometry introspection at all, fillets are labor, multi-color 3MF export is functional-but-flaky (lazy-union is officially temporary; known color-loss bugs). Kept as fallback; scottbez1/splitflap's OpenSCAD sources remain readable prior art regardless.
- **CadQuery** (2.8.0): same OCCT kernel, still maintained, has a real assembly constraint solver — but slower development, fluent API is worse for generated code, no per-part-color 3MF export, narrower Python support. build123d is its community-acknowledged successor by a former CadQuery contributor.

## Pipeline into Bambu Studio

```
cad/*.py (build123d)
  └─ python -m cad.export        # headless; runs in CI too
       ├─ export/*.3mf           # multi-body, per-shape color → print files
       └─ export/*.stl           # single-material fallback / interchange
Bambu Studio: File → Import → "not from Bambu Lab, load geometry only" → OK
  → objects + colors survive → assign filament per object (AMS) → slice
```

- **3MF over STL**: 3MF carries units, multiple bodies, colors; STL is bare mesh. STL exported only as universal fallback.
- **Two-color flaps without AMS**: single-toolhead P2S (base, no AMS) can only do layer-based manual filament swap ("Change Filament" at a layer — works when colors separate by Z, e.g. embossed glyphs). Per-object color needs AMS. Detail deferred to the charset/flap-artwork ticket.
- **Bambu Studio CLI** exists on macOS (`--slice`, `--export-3mf`) but is rough (preset JSON wrangling, GUI still needed to send prints). Not part of the standard loop; GUI slicing is fine.

## Repo layout & environment (for the scaffold ticket)

```
cad/
  pyproject.toml        # pins python + build123d (pre-1.0 churn!)
  splitflap_cad/        # one module per part: drum.py, flap.py, housing.py, …
    params.py           # every dimension a named parameter, positions derived
  tests/                # pytest: volumes, bboxes, clearances, is_valid()
  export.py             # writes export/*.3mf + *.stl
export/                 # generated, gitignored or committed per release
```

- Pin Python to a version the current `cadquery-ocp` wheel supports (wheels lag new Python releases).
- **Viewer for Calum**: ocp_vscode (VS Code extension or standalone `python -m ocp_vscode` browser viewer, port 3939) — live model view while iterating.
- **Visual check for Claude**: headless PNG render via `f3d --output out.png part.stl` (or build123d-f3d-render); multi-angle renders each iteration. `ocp_vscode.save_screenshot()` exists but needs a live viewer.
- Consider cad-khana / build123d-mcp once real part design starts.

## Sources

Full agent research summaries (OpenSCAD state, build123d/CadQuery state, Bambu import pipeline) with per-claim URLs are preserved in issue [#2](https://github.com/0x63616c/split-flap/issues/2) comments. Key refs:

- build123d: <https://pypi.org/project/build123d/> · <https://build123d.readthedocs.io/en/latest/import_export.html> · joints tutorial <https://build123d.readthedocs.io/en/latest/tutorial_joints.html>
- CadQuery color-3MF gap: <https://github.com/CadQuery/cadquery/issues/1345>
- Bambu generic-3MF import: <https://forum.bambulab.com/t/the-3mf-is-not-from-bambu-lab-load-geometry-data-only/2352> · color parsing <https://wiki.bambulab.com/en/bambu-studio/Standard-3MF-File-Color-Parsing>
- Multi-color without AMS: <https://wiki.bambulab.com/en/software/bambu-studio/multi-color-printing>
- OpenSCAD nightly/Manifold: <https://github.com/openscad/openscad/releases> · BOSL2 <https://github.com/BelfrySCAD/BOSL2/>
- Agent tooling: <https://github.com/pzfreo/build123d-mcp> · <https://github.com/cyberchitta/cad-khana> · <https://github.com/bernhard-42/vscode-ocp-cad-viewer>
- Prior art: <https://github.com/scottbez1/splitflap>
