# Split-flap design conventions and common dimensions

Prior-art survey for designing a 3D-printed split-flap module driven by a 28BYJ-48 + ULN2003, homed with an A3144 hall sensor, controlled by an ESP32-C6. Resolves [#3](https://github.com/0x63616c/split-flap/issues/3).

Projects surveyed:

- **scottbez1/splitflap** — the canonical open-source design; laser-cut MDF, CR80 PVC-card flaps, direct drive. [Repo](https://github.com/scottbez1/splitflap)
- **David Kingsman split-flap** — the canonical *fully-printed-flap* design; direct drive, 45 flaps. [Printables](https://www.printables.com/model/69464-split-flap-display) · [Repo](https://github.com/davidkingsman/split-flap) · [Manual PDF](https://github.com/JonnyBooker/split-flap/blob/master/Instructions/SplitFlapInstructions.pdf)
- **Morgan Manly (2025)** — most compact all-printed design; **37 glyphs (A–Z 0–9 blank), A3144 hall, 5 V 28BYJ-48, geared, ESP32-C3** — closest match to our parts bin. [Instructables](https://www.instructables.com/Split-Flap-Display-3D-Printed-Modular-Compact-Encl/) · [Repo](https://github.com/ManlyMorgan/Split-Flap-Display)
- Supporting: [tinkermax build notes](https://tinkerwithtech.net/split-flap-display-brings-back-memories), [Jason Winfield planetary/encoder design](https://hackaday.com/2026/06/28/accurate-split-flap-display-can-be-3d-printed/), [jonas digit module](https://hackaday.io/project/163725-split-flap-display), [gregerw blog](https://splitflap.home.blog/), [Parts Not Included](https://www.partsnotincluded.com/building-diy-split-flap-displays/).

## Quick comparison

| | scottbez1 v2 | Kingsman | Morgan Manly |
|---|---|---|---|
| Flap count | 52 | 45 | **37** |
| Flap material | CR80 PVC card | FDM printed | FDM printed |
| Flap W×H (mm) | 54 × 43 | ~similar, 1.0 thick | 33.1 × 21.75 |
| Flap thickness | 0.762 mm | 1.0 mm | **0.6 mm** |
| Drum OD | ~60 mm | ~similar | 50 mm |
| Drive | direct | direct | geared (2 spur gears) |
| Motor | 12 V 28BYJ-48 | 12 V only ("5 V lacks torque") | **5 V 28BYJ-48** |
| Homing | hall + magnet in spool | KY-003 hall + magnet | **A3144 + glued magnet** |
| Module pitch | ~82 mm wide | ~51.3 mm | **37.9 mm** |
| Controller | ESP32 + shift registers | Nano/module + ESP-01 I2C | ESP32-C3 + PCF8575 I2C per module |

Key takeaway: Morgan Manly proves 5 V motors work **if geared**; direct-drive designs (scottbez1, Kingsman) insist on the 12 V variant for torque. Our inventory has 5 V units → gear stage strongly indicated (it also fixes the shaft-offset problem, below).

## Flaps

- Printed flap thickness in the wild: **0.6–1.0 mm**. Morgan: 0.6 mm (0.1 mm layers ×6); Kingsman/jonas: 1.0 mm. Thinner = lighter stack, less torque needed, crisper flip.
- Two-tone glyphs: standard trick is a filament swap at the last 2 layers (white glyph on black body, 0.1 mm layers → white portion is exactly 2 layers). 0.2 mm nozzle gives noticeably crisper glyph edges; 0.4 works. Needs a well-levelled bed; flaps are "the most challenging part to print" (Kingsman).
- Letterform: glyph split top-half/bottom-half; **back of flap N carries the bottom half of flap N+1's glyph**. Kingsman font: Expressway Condensed Bold.
- Flap pin convention (scottbez1, load-bearing numbers): pin is what remains after notching the flap corner — pin width **1.4 mm**, notch depth **3.2 mm per side**, notch height ~15 mm. Morgan's printed flaps flex-snap into drum holes instead.
- scottbez1 flap: 54 × 43 mm, corner radius 3.1 mm (cosmetic).

## Drum / spool

- Pitch radius from flap count: `pitch_r = flaps × (hole_dia + hole_separation) / 2π`. scottbez1: hole Ø2.2 mm (0.8 mm diametral clearance over the 1.4 mm pin), edge-to-edge separation 1.2 mm → 52 flaps = pitch_r 28.14 mm (~60 mm drum); 40 flaps = pitch_r 21.65 mm. Morgan (37 flaps): 50 mm OD drum.
- **Pin-in-hole running clearance 0.8 mm diametral** — the single most load-bearing tolerance for free flap fall.
- Flap side-play 0.5 mm between drum cheeks (`flap_width_slop`).
- Construction: Kingsman = two press-together halves, flaps loaded by lifting outer half a few at a time; Morgan = single drum, flaps flexed into holes; scottbez1 = two disks + struts. Last few flaps are always the hardest to insert.
- Enclosure sizing: collapsed-flap exclusion radius = `sqrt(flap_height² + pitch_r²)`; extended = `pitch_r + flap_height + 2 mm`. Keep ≥5 mm above swept circle, 1 mm below.
- Magnet mount in drum cheek: press-fit pocket with ~0.05 mm interference (scottbez1, Ø4 magnet) or superglue (Morgan). **tinkermax: thin spokes around the magnet recess snap — reinforce the pocket area.**

## Drive: 28BYJ-48 realities

- **Real gear ratio is not 64:1.** Tooth counts (32/9)×(22/11)×(26/9)×(31/10) = 25792/405 = **63.68395:1** → **2037.89 full steps/rev** (4075.77 half-steps), not 2048/4096. But it *varies by batch/manufacturer* — some 12 V units measure exactly 2048; some units have different tooth sets entirely. Never trust the nominal figure; per-rev homing absorbs the error (scottbez1 hardcodes 2048 and lets the hall sensor fix it every revolution).
- Assuming 2048 when the true count is 2037.89 drifts ~1.79°/rev → a full flap of error in ~5 revs at 37–40 flaps. **Per-revolution hall re-sync is mandatory**; open-loop counting alone fails (tinkermax confirmed on 12 units).
- **Backlash ~1° on direction reversal** → split-flaps rotate one direction only, always approach every flap from the same direction. Never reverse.
- Torque: 5 V unit ~300–380 gf·cm max at ≤333 pps full-step, falls with speed; practical ceiling 300–500 pps loaded. 12 V variant has materially more torque — hence direct-drive designs demand it. Alternatives for 5 V units: gear it down/across (Morgan), or bipolar-convert (cut red wire, A4988 @125 mA) like tinkermax.
- Drive scheme: scottbez1 uses full-step two-phase-on (4-pattern) via ULN2003; ~625 steps/s peak with a 200 ms linear accel ramp. Parts Not Included had to slow min step period to 1400 µs to stop stalls.
- Physical quirks everyone hits:
  - **Shaft is offset 8 mm from chassis center** → motor body eats module width in direct drive; Morgan/Jason add a gear stage to re-center; Kingsman just makes the module wide.
  - **Shaft not perfectly perpendicular to body** — Kingsman shims one side of the motor mount 0.4 mm; without it flaps hang non-vertical.
  - **0.5–1.5 mm axial shaft slop** — nylon washers as thrust bearings.
  - Double-D shaft: Ø5 mm, flats 3 mm across × 6 mm long; scottbez1 uses −0.08 mm radial interference on the D-slot for press fit. Mount holes Ø4.2 mm on 35 mm centers.
  - Continuous rotation overheats the motor; scottbez1-style two-phase-on holds current at idle — de-energize coils when parked (tinkermax used SLEEP to save 0.35 W/motor).

## Homing: hall + magnet

- Universal convention: magnet embedded in drum cheek, sensor fixed to frame at matching radius; sensor trigger = step 0; **per-unit calibration offset from home to flap 0 stored in flash** (typ. ~100 steps; scottbez1 adjusts in tenths-of-a-flap via web UI and persists to ESP32 flash).
- scottbez1 placement: magnet at 17.5 mm radius (= motor mount-hole radius), 90° ahead of the home flap; sensor PCB clamped under a motor bolt. Morgan: magnet at the blank flap, next flap = A.
- **A3144 specifics**: unipolar, non-latching switch; **south pole facing the branded face** triggers it; open-collector output needs a pull-up. Rated 4.5–24 V — at 3.3 V it's out of spec (clones often work anyway). Canonical ESP32 wiring: **VCC = 5 V, output pulled up to 3.3 V** (open-collector only sinks, so this is safe), 100 nF decoupling at the sensor. LOW = magnet present. Operate point 70–350 G — with a 6×3 mm N35 disc, reliable at a 2–5 mm gap; verify per unit, spread is wide.
- **Test magnet polarity on the breadboard before gluing/pressing it in** (unipolar sensor; wrong pole = no trigger). Mark the pole.
- Low-power/sampling hall ICs miss the fast magnet pass — use always-on parts like A3144 (scottbez1 warns about this class of bug).
- Firmware error-handling conventions (scottbez1): ignore home blip within ~5 flaps after home; blip elsewhere = "unexpected home" → recalibrate; expected home not seen within ¼-flap margin = "missed home" → recalibrate; home search at ~1/8 speed; give up after flaps+2 worth of steps. tinkermax saw physical **double-triggers** on 2 of 12 units — firmware must tolerate and re-home.

## Flap hold/release

- scottbez1 has **no separate vane part**: the front panel itself retains the flap stack. Front panel plane sits at `pitch_r + flap_thickness/2` ahead of the axis; the window's top edge overhangs the flap tips by **1 mm** — the drum drags each flap tip past that lip and it falls. Bottom window edge cut so falling flaps clear it.
- That 1 mm lip + the 0.8 mm pin clearance are the two numbers that make release reliable.

## FDM tolerances (translating scottbez1's laser-cut fits)

- Running fit (flap pin in hole): 0.8 mm diametral.
- Press/interference fits: magnet pocket −0.05 mm; motor D-shaft −0.08 mm radial.
- Slip fits: ~0.10 mm (laser); FDM typically needs 0.2–0.3 mm — print one of each mating part first and verify (gregerw's advice).
- Printed gear axles wear — Morgan ecosystem's "metal dowel mod" swaps them for metal pins; jonas used 625ZZ bearings (16×5×5 mm) under the drum.
- Frame parts: 0.6 mm nozzle / 0.3 mm layers fine for structure; flaps want 0.2 mm nozzle / 0.1 mm layers.

## Common failure modes (design against these)

1. Double-flapping / dropped flaps — drift or low torque → per-rev homing + torque margin.
2. Hall double-trigger → firmware tolerance + re-home.
3. Magnet-recess spokes cracking → reinforce.
4. Motor mounts twisting off when bolted → captive-nut design (slide-in M3 nuts / heat-set inserts).
5. Flaps sticking at release → keep pin clearance ≥0.8 mm and lip overhang ~1 mm.
6. Jamming from overtightened enclosure screws (Morgan) — don't preload the mechanism.
7. ULN2003 board LEDs leak light in an enclosure (Morgan pried them off); wire looms snag flaps → add a guide.
8. Idle coil heating → de-energize when parked; thermal shutdown if running continuously.

## Implications for our module (37 glyphs, 5 V 28BYJ-48, A3144, 6×3 magnets, ESP32-C6, P2S)

- Morgan Manly's design is the closest prior art on nearly every axis — study it first when fixing geometry in [#7](https://github.com/0x63616c/split-flap/issues/7).
- Our 5 V motors → plan a gear stage (also re-centers the offset shaft and shrinks module pitch), or accept a wide Kingsman-style module and risk torque limits.
- 37 flaps at scottbez1's hole spacing → pitch_r ≈ 20 mm, drum OD ≈ 45–50 mm — Morgan's 50 mm confirms the ballpark.
- Firmware: forward-only rotation, per-rev hall re-sync, flash-persisted home offset, target step computed as `flap × steps_per_rev / 37` per move (never incremental), de-energize at idle, tolerate double-triggers.
- A3144 on ESP32-C6: power at 5 V (VBUS), pull output to 3.3 V. Breadboard polarity test before committing magnet placement.
- Print a tolerance coupon (pin/hole, magnet pocket, D-shaft slot) on the P2S before printing full parts.
