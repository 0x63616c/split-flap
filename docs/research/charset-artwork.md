# Charset artwork: glyph generation software + how glyphs get onto flaps

Resolves [#8](https://github.com/0x63616c/split-flap/issues/8). How the 37-glyph flap artwork gets generated, and how it physically lands on 3D-printed flaps. Builds on [cad-tool-choice.md](cad-tool-choice.md) (build123d) and [split-flap-conventions.md](split-flap-conventions.md).

## Recommendation

**Write our own flap generator in build123d** — no external artwork tool. One Python module in `cad/` emits, per flap, a two-body model (black flap card + white glyph inlays) straight into the existing build123d → 3MF → Bambu Studio pipeline. Feasibility of every step was empirically verified with build123d 0.11.1 (test scripts run during research; details below).

Physical method — **branches on one unknown: AMS**.

- **With AMS (plan A): flush two-color inlay.** White glyph solids occupy the top 2 and bottom 2 layers of the flap; black body elsewhere. Prints flat, both faces smooth (no raised text to snag adjacent flaps), standard multi-color keycap/sign technique. Flap = **0.8 mm (4 layers @ 0.2)** or 1.0 mm for a guaranteed black core. The popular filament-swap-at-layer trick does **not** work here: a swap recolors the whole layer, so the bottom face would come out solid white — double-sided glyphs need true multi-body two-filament printing.
- **Without AMS (plan B): white vinyl stickers on black flaps.** scottbez1's proven path (Dave Madison cut Oracal 631 matte white on a Cameo). Generator emits per-flap glyph SVGs instead of white bodies; flaps print single-color black. Needs a vinyl cutter or hand-cutting — meaningfully worse workflow at 74 glyph halves.
- Rejected: embossed/raised text (unprintable on the underside without supports, snags neighbouring flaps), debossed + paint pen (fiddly, 74 cavities), swap-at-layer (above).

AMS availability is a fact only Calum can settle → tracked as its own ticket.

## The generator (what to build, verified facts)

Core recipe, ~30 lines per flap in build123d:

1. `Text(char, font_size, font_path=..., align=None, text_align=(TextAlign.CENTER, TextAlign.BOTTOM))` — baseline lands exactly at y=0 for **every** glyph (verified: A, g, O, '-' all consistent). Always pass `font_path`, not a font name — OCCT name lookup can silently fall back to a default font ([build123d#1235](https://github.com/gumyr/build123d/issues/1235)). Note `font_size` = em size, not cap height (Helvetica cap height ≈ 0.717 em); measure cap height in CAD via `Text("H").bounding_box().max.Y`.
2. Draw the glyph once at full size (spanning two flap heights), **split at cap_height/2** with a boolean `&` against a half-plane rectangle, or `face.split(Plane.XZ, keep=Keep.BOTH)` — both verified; counter holes (O, 0, A…) survive splitting cleanly.
3. **Front of flap N = top half of glyph N, upright. Back of flap N = bottom half of glyph N+1, rotated 180° about the horizontal (X) axis** — one rotation both moves it to the back face and orients it correctly after the flip.
4. **Gap compensation** (scottbez1's numbers): push the two halves apart by half the hinge gap each (scottbez1: flap_gap = 2.0 mm → ±1.0 mm rigid offset, not a stretch) so the assembled letter reads continuous across the physical gap between top and bottom flaps. Our exact gap comes out of the geometry ticket ([#7](https://github.com/0x63616c/split-flap/issues/7)); make it a parameter. Also respect scottbez1's **top keepout** (~3.7 mm of flap top hidden behind the resting stack — scaled to our geometry).
5. Extrude: black card body with glyph footprints subtracted; white glyph inlays filling those pockets top and bottom.
6. Export: set `.color`/`.label` **on leaf Solids, not on the `Part`/`Compound` wrapper** — Mesher silently drops color set on a Compound (verified trap; `extrude()` returns a Compound). Multi-solid glyphs (`?`, `Q`+tail etc.) need color applied per solid: iterate `.solids()`.
7. One colored 3MF per flap (or plate) via `Mesher`. Bambu Studio's "Standard 3MF Color Parsing" dialog auto-maps body colors to loaded filaments. Known-good fallback (zero risk, verified workflow docs): export the two bodies as STLs, import together, answer "load as single object with multiple parts?" → Yes, assign filaments — bodies share one coordinate system so they register perfectly.

Font metrics: build123d alone suffices (baseline alignment + measured cap height). `fontTools` only if we later want optical tweaks/fixed advances.

## Font choice

**Epilogue Medium (OFL)** — scottbez1's official v2 flap font, with published tuning numbers we can reuse (height 0.7 × flap height, per-letter width overrides for W/M/@/&…). Bundle the TTF in `cad/fonts/` (OFL permits redistribution).

Alternative if a more condensed/transport look is wanted: **Roboto Condensed Bold** (Apache 2.0, also scottbez1-preset-proven). Kingsman's Expressway Condensed Bold is Typodermic freeware (rendered output fine, but no redistribution — can't commit the TTF). Real Solari boards use Helvetica/Gill Sans Bold (commercial); Arimo/Liberation Sans are metric-compatible free stand-ins if we ever want that look.

Stroke width is a non-issue: even on Morgan-scale flaps (~33×22 mm, glyph ~15 mm) a bold sans has ~2 mm strokes vs 0.4 mm nozzle minimum; 0.2 mm nozzle only buys crisper edges. Keep counters/gaps ≥0.4 mm.

## What prior art does (survey)

| Project | Artwork tool | Physical method |
|---|---|---|
| scottbez1 | OpenSCAD `text()` + Python drivers (`flap.scad`, `generate_fonts.py`, `generate_3d_print_flaps.py`) — the only fully-scripted, numbers-documented pipeline | vinyl stickers on CR80 cards (main); 3-body STLs for printed flaps (0.3 mm letter extrusion) |
| David Kingsman | none — manual Fusion 360, static STLs | two-tone print via filament swap (raised text, single-sided trick per face pair) |
| Morgan Manly | none — manual Fusion 360; per-flap folders of 3 STL bodies (Flap / Front Text / Rear Text) | separate-body color (AMS) or modified filament-change gcode |
| Thom Koopman Flap Customiser | MakerWorld parametric app (OpenSCAD) — auto-generates flap set from font + charset | printed two-tone |
| dennis9819/split-flap-generator | Python + OpenSCAD template + YAML; per-flap SVG artwork support | 2 STLs per flap, optional multi-filament 3MF via Orca CLI |
| ToonVanEyck OpenFlap | Inkscape extension → per-flap SVGs | glyphs on PCB flaps |

Our build123d generator is the same architecture as scottbez1's (glyph → split → flip → gap-comp → per-color bodies), in the CAD tool we already chose, with his tuning numbers as starting values.

## Decisions this locks in

- Artwork software = **self-written build123d flap generator** in `cad/` (parameters: charset order, font path, flap dims, hinge gap, keepout, inlay depth); emits colored 3MF (plan A) or STL pairs + SVGs (plan B).
- Font = **Epilogue Medium**, bundled, Roboto Condensed Bold as fallback preset.
- Glyph-onto-flap = **flush two-color inlay if AMS available**, else vinyl stickers — resolved in follow-up ticket.
- Flap thickness gets a floor from artwork: **≥0.8 mm** for opaque two-layer inlays both faces (feeds geometry ticket #7; prior-art printed flaps run 0.6–1.0 mm).
