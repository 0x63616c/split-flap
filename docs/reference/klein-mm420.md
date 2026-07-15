# Klein Tools MM420 multimeter — quick reference

Auto-ranging TRMS digital multimeter, 600V CAT III, 10A, 50MΩ. Full manual: [`klein-mm420-manual.pdf`](./klein-mm420-manual.pdf) (official PDF from [kleintools.com](https://data.kleintools.com/sites/all/product_assets/documents/instructions/klein/MM420%20Instructions_web.pdf)).

## Jacks (bottom of meter)

| Jack | Use |
|---|---|
| **COM** | Black lead — always |
| **VΩ** (right) | Red lead for voltage, resistance, continuity, mA/µA, everything except big current |
| **10A** (left) | Red lead only for current >400mA (e.g. whole stepper circuit draw) |

## Buttons

- **SEL** — toggles secondary function on current dial position (AC↔DC, Ω↔continuity, °F↔°C). White label = default, orange = SEL.
- **HOLD** — freeze reading. **RANGE** — manual range (hold 1s to go back to auto). **MAX/MIN** — track extremes.
- Auto power-off after 15 min — press any button to wake.

## The four things this project needs

### 1. DC voltage (check 5V VBUS, 3.3V rail)
Red → VΩ, dial → **V**, press **SEL** to get **DC** (defaults to AC — check LCD shows `DC`). Probe across rail and GND.

### 2. Continuity (breadboard wiring checks)
Red → VΩ, dial → **continuity/Ω** setting (speaker icon). Defaults to continuity; beeps <50Ω. Open circuit shows `OL`. **Circuit must be unpowered.**

### 3. Resistance
Same dial position, press **SEL** once for Ω mode. Unpowered circuit only.

### 4. DC current (stepper coil / total draw)
Meter goes **in series** (break the circuit, meter bridges the gap):
- Expected <400mA (one 28BYJ-48 ≈ 200–300mA): red → **VΩ** jack, dial → **mA**, SEL for DC.
- Could exceed 400mA (multiple motors): red → **10A** jack, dial → **10A**, SEL for DC.
- Fuses: 500mA on mA range, 10A on 10A range — wrong jack pops fuse.

## Gotchas

- Every measurement setting defaults to **AC**; press SEL for DC. LCD shows AC/DC.
- Stray few-mV readings with open leads in V mode = normal noise; touch leads together to zero.
- `-` sign = leads reversed polarity (harmless info in DC).
- Lead Alert LEDs light if red lead is in a jack that doesn't match the dial setting — heed them.
- Never measure resistance/continuity on a live circuit.

## Temperature / capacitance / frequency

Also on board (SEL variants): °F/°C via thermocouple, capacitance, Hz/duty-cycle. See manual pp. 12+ for details.
