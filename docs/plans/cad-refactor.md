# CAD refactor plan — abstractions + golden geometry harness

Goal: restructure `cad/splitflap_cad` for easier authoring with **provably
identical geometry**. Each phase = own commit(s), geometry tests green
between all of them.

## Findings driving this (review 2026-07-16)

1. **Parallel-list scene building** — `assembly.py`, `holder.py`,
   `glyphflap.py` (×2 demos), `catalog.py` all hand-maintain
   `objects/names/colors/alphas` lists; both glyphflap demos grew local
   `add()` helpers. Missing `Scene` abstraction.
2. **Repeated geometry idioms** — polar repeat
   (`for i in range(N): body -= Rot(0,0,i*360/N) * cutter`) in drum ×4 +
   holder; radial-profile-to-standing-plate
   (`Pos(0,±t/2,0) * Rot(90,0,0) * extrude(...)`) ×4 in drum, each with a
   winding-direction trap comment; slot-0 deboss triangle duplicated
   (`drum._slot0_marker` + `holder._slot0_marker`, both off
   `P.drum_mark_*`) → `geo.deboss_mark()`.
3. **Ad-hoc edge selectors** — drum bore mouth/rim, fin roots
   (`_diam_dist` + magic tolerances). Most fragile code in the package.
4. **Catalog boilerplate** — ten `_xxx()` lazy shims + separate
   `PRINTABLE` dict; part-module interface inconsistent
   (`*_show_args()` vs raw builders).
5. **Anonymous frames** — poses inline (`Pos(P.mount_x, P.byj_shaft_y,
   P.drum_z0)`); posing split between drum.py and assembly.py.
6. **params.py decay** — stranded fields (`pilot_clearance`,
   `drum_flat_clear`), duplicate deriveds (`drum_slot_pitch` ==
   `holder_slot_pitch`), inline chamfer magics (drum.py 0.6/0.5,
   holder.py 0.6, unit.py 0.3) despite the no-magic-numbers rule.

Deliberately **out of scope**: full params split into per-part
sub-dataclasses (`P.drum.ring_od`) — big churn, decide later. No `class
Drum`-style part classes — functions returning `Part` are the right
shape; the only new classes are small dataclasses (`Scene`, `Model`).

## Verification strategy (three layers)

- **L1 exports**: `just cad export` + git diff on `cad/export/` — byte
  churn possible from tessellation even when geometry identical; signal,
  not judge. 3MFs currently churn on EVERY export (commit 3958b40):
  `zipfile.writestr` stamps wall-clock time into entries. Phase 0 fixes
  this — write via `ZipInfo` with fixed `date_time=(1980,1,1,0,0,0)` in
  `flap3mf.py` (and glyphflap's Mesher output if it embeds dates), making
  3MFs deterministic and L1 meaningful for them.
- **L2 fingerprint** (fast, every commit): per part volume / area / bbox
  / centre-of-mass vs JSON golden, rel tol ~1e-6.
- **L3 XOR** (slow, definitive, per phase): golden BREP per part;
  `(new - golden).volume < 1e-6` and `(golden - new).volume < 1e-6`.
  Residual solid IS the diff — pushable to viewer for review.
- Intentional geometry change: overlay review (golden ghost at alpha
  0.4), then regenerate goldens in the same commit — `git log` on
  `cad/tests/golden/` = shape-change history.

## Coordination with the ctl TUI plan (2026-07-16-ctl-cad-tui.md)

STATUS 2026-07-16: TUI plan fully landed (Tasks 1–8, incl. `list
--json`, pin/sync deletion, CLAUDE.md rewrite) — **Phase 3 is
unblocked**; `cad/tests/test_cli.py` exists and is the contract gate.
Original rules kept for the record:

- **Phases 0–2 are parallel-safe** (part modules, new geo/select/viewer
  modules; only `__main__._push` touched, which the TUI plan never
  edits).
- **Phase 3 BLOCKS on TUI Tasks 1+7**: both rewrite `__main__.py`
  (`list --json` added; `pin`/`sync`/state deleted). After they land:
  - `list --json` output shape `{models, printable, src_to_model}` is a
    contract with Go `loadCatalog` — keep it byte-compatible when
    `PRINTABLE` folds into `Model.printable` (derived views). TUI's
    `test_cli.py` is the Phase 3 gate.
  - Drop this plan's `sync`/`pin` re-testing (commands deleted); re-test
    `just cad view` watcher path instead (`src_to_model` still consumed
    by Go).
- **Phase 5 CLAUDE.md edit goes after TUI Task 7's** CAD-section
  rewrite; viewer eyeball step uses `just cad view MODEL` (per-pane,
  dynamic ports), not the fixed :3939/:3940 pair.

## Phase 0 — safety net

1. Golden harness in `cad/tests/`: generator writes BREP + fingerprint
   JSON per part into `cad/tests/golden/` (all `PRINTABLE` +
   `drum_inner` unrotated, motor, hall mock). Fingerprint pytest (fast)
   + XOR pytest marked `slow`.
2. Catalog smoke test: every `MODELS` entry builds; every `PRINTABLE`
   has volume.
2b. Deterministic 3MFs: fixed `ZipInfo` timestamps in `flap3mf.py` +
   check `glyphflap.export_flaps` (Mesher) for embedded dates — kills
   the perpetual export churn, upgrades L1.
3. Run → green.
4. **Prove RED** (temporary, uncommitted sabotage; three failure classes):
   - param nudge (`drum_ring_t` 1.6→1.7) → fingerprint + XOR fail
   - pure 0.5 mm feature translation (volume ~unchanged) → bbox/COM or
     XOR fail (proves layer roles)
   - chamfer edge-selection drift in drum → XOR fail (the refactor's
     actual risk profile)
5. Confirm failure output useful (names part, residual volume).
6. Revert sabotage, green, commit harness — paste RED run output into
   the commit message body as proof the net works.

## Phase 1 — geometry helpers

7. `geo.py`: `polar()`, `radial_plate()` (symmetric extrude — winding
   never matters). Swap call sites one at a time: `drum._cut_slots`,
   drum notches/rails/fins, `holder`. Fingerprint after each swap; XOR
   at phase end.
8. `select.py`: named edge selectors (`edges_at_radius`,
   `bottom_face_edges`, `diametral_edges_at_z`). Swap drum bore
   mouth/rim/fin-root + unit chamfer selections.

## Phase 2 — Scene builder

9. `viewer.py` with `Scene` dataclass (`.add(obj, name, color, alpha,
   loc)`, `.show_args()`). Convert assembly, holder, both glyphflap
   demos, catalog shims, `__main__._push`. No geometry risk — smoke test
   + push each model to viewer once.

## Phase 3 — catalog pure-data

10. Standard part-module interface: `part()` builders + `scene()`.
    `Model` holds string attrs (module stem, scene attr, optional
    printable attr); generic lazy loader; `PRINTABLE` folds into
    `Model.printable`; delete the ten shims. Re-test `just cad list`,
    `sync`, `pin`, `export`, watcher auto-focus (`SRC_TO_MODEL`).

## Phase 4 — frames + params tidy

11. Named locations (`DRUM_IN_UNIT`, `MOTOR_IN_UNIT`, …) in one place;
    part modules build local-frame only; assembly composes.
12. params cheap reorder: contiguous groups, deriveds beside groups,
    rehome stranded fields, kill `holder_slot_pitch` dup, promote inline
    chamfer magics (or bless documented exception: edge breaks ≤1 mm may
    inline). No renames — zero call-site churn.

## Phase 5 — close out

13. Full run: fingerprint + XOR + all tests + `just cad export`; expect
    clean `cad/export/` (any byte churn adjudicated by XOR).
14. Push every model to both viewers, eyeball.
15. Update CLAUDE.md conventions: new part = module with `part()` +
    `scene()` + one catalog line. Final commit.

End state: identical geometry (proven), duplication sites deleted,
one-line part registration, golden harness guarding all future work.
