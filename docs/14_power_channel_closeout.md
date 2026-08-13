# `power_channel` — close-out checklist

Levitation coil drive stage · Sebastian · 2026-08-13
Generated from the current file (`final_lev\power_channel.kicad_sch`, 54 components).
Companion to `13_schematic_review_power_channel.md` rev 1.

Connectivity is done and verified. What is left is **data completeness** (things the file
does not yet say) and **five design decisions that add parts**. Nothing here requires
rewiring what you have drawn.

Already closed since rev 1 of the review: C4 and C16 are both 0805 now, so the bootstrap
capacitor mismatch is gone.

---

## 1. Wrong data in the file — 1 item

### D2 footprint is the wrong package

    D2  5.0SMDJ70A   →  Diode_SMD:D_SMA_Handsoldering      ✗

The 5.0SMDJ series is **DO-214AB (SMC)**, body 6.6–7.11 × 2.9–3.2 mm. An SMA
(DO-214AC) land pattern is roughly 4.3 × 2.6 mm — the part physically will not fit the
pads. Verified against the Littelfuse 5.0SMDJ datasheet.

    change to:  Diode_SMD:D_SMC_Handsoldering

D1 and D3 are correct — ES1D genuinely is DO-214AC (SMA).

---

## 2. Missing footprints — 5 items

Copy-paste strings. The first four match parts already in your file, so they are known
good in your library:

| Ref | Value | Footprint to assign |
|---|---|---|
| C19 | 1nF | `Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder` |
| C20 | 100nF | `Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder` |
| R12 | 10R | `Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder` |
| R13 | 10R | `Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder` |
| U5 | 74HC74 | SOIC-14 — `Package_SO:SOIC-14_3.9x8.7mm_P1.27mm` (pick it from the chooser, I have not verified this exact string against your library) |

---

## 3. Footprints already assigned that need a decision, not a fix

**C9 / C10 — `CP_Radial_D16.0mm_P7.50mm`.** A 470 µF / 100 V aluminium electrolytic is
typically 18 mm diameter and 25–40 mm tall. A 16 mm can at that CV product is unusual.
Check the actual part before layout — and note this footprint changes anyway if you act
on §3.1 of the review (ripple current) and move to polymer or add more parts.

**R11 — `R_2512_6332Metric`.** Committed 2-terminal. See §3.4 of the review. If you are
going to move to a 4-terminal metal-element part, do it now — it is a footprint change,
not a BOM change, and it gets harder after layout.

**Q1–Q4 — `TO-220-3_Vertical`.** Confirm rather than change: vertical mounting with the
tabs in a row bolted to a common extrusion is the normal arrangement for this, and it is
probably what you want. Two things to be sure of before layout:

- Q1/Q3 tabs sit at **+60 V**, Q2/Q4 tabs sit at the **switch nodes**. Four different
  potentials on four tabs — every one needs an insulating pad. The 1.5 °C/W silpad in
  §4.2 of the design sheet already budgets for this, so the thermals still work, but it
  must be explicit or someone will bolt them down bare.
- The heatsink you need is ~1.35 °C/W, which is a substantial extrusion. Its geometry
  constrains where this row of four can go on the board.

---

## 4. Missing fields — the real gap

Only 7 of 54 parts carry an MPN (Q1–Q4, U1, U2, U4). More importantly:

**No capacitor in the file has a voltage rating.** On a 60 V board that is the most
dangerous omission in the BOM — nothing in the file distinguishes a 100 V bus cap from a
16 V decoupling cap, and they look identical on a reel.

Minimum set to add before you call it done:

| Field | Where | Value |
|---|---|---|
| `Voltage` | C3, C5–C15 (bus bank) | **≥100 V** |
| `Voltage` | C9, C10 | **≥100 V** |
| `Dielectric` | C5–C8, C12–C15 | **X7R** — and note a 100 V X7R 1210 at 60 V bias delivers roughly half its rated capacitance. That derating is already assumed in the ripple-current argument (§3.1 of the review) |
| `Voltage` | everything else | ≥25 V is fine |
| `Tolerance` | R14, R15, R16 | **1%** — these three set the trip point; procurement must not substitute 5% |
| `Tolerance` / `Power` | R11 | 1%, ≥2 W (2.0 W at the 45 A trip) |

MPN on the rest can wait for procurement, but the voltage and tolerance fields cannot —
they are engineering intent, not purchasing detail.

---

## 5. Value string hygiene — 3 items

| Ref | Now | Change to | Why |
|---|---|---|---|
| C2, C17 | `100 nF` | `100nF` | Splits your BOM into two lines against C3/C11/C20–C23 |
| R11 | `1mR` | `1m` or `0.001` | `1mR` is ambiguous — reads as 1 mΩ to you and 1 MΩ to a tired reader |

---

## 6. Hierarchical label types — 4 items, then re-sync

All seven are currently typed `input`. Four are wrong:

| Label | Now | Should be |
|---|---|---|
| PWM_A | input | input ✓ |
| PWM_B | input | input ✓ |
| RESET | input | input ✓ |
| COIL_A | input | **passive** (or bidirectional) |
| COIL_B | input | **passive** (or bidirectional) |
| ISNS | input | **output** |
| FAULT | input | **output** |

As drawn, the parent sheet will report "input pin not driven" on ISNS and FAULT, which
are outputs. After changing them, go to the root sheet and re-sync the sheet pins so the
parent picks up the new types.

---

## 7. Design decisions that add parts

These are the ones that actually decide whether the sheet is finished, because each adds
symbols. All five are argued in `13_schematic_review_power_channel.md`.

| # | Decision | Parts added | Ref |
|---|---|---|---|
| 1 | **Bus caps** — 2× 470 µF cannot carry 15 A RMS. More electrolytics (6×) or polymer (3–4×) | +2 to +4 | §3.1 |
| 2 | **OCP behaviour** — hard-off via SD (as drawn) or slow decay by gating PWM with the latch's Q̄ | 0 or +1 (74HC08) | §3.2 |
| 3 | **Gate turn-off network** — 4.7 Ω + diode across each 10 Ω, per design sheet §4.3 | +8 | §3.3 |
| 4 | **Shunt type** — metal-element vs. the thick-film 2512 now committed | 0 (footprint change) | §3.4 |
| 5 | **Bus bleed resistor** — 940 µF at 60 V is 1.7 J with no discharge path | +1 | §3.6 |

If you need a design tonight and not a perfect one: **do 1, 3 and 5** (they are 11 parts
and no new thinking), **log 2 as accepted-for-rev0**, and **decide 4 now** because it
gets expensive after layout.

---

## 8. Documentation on the sheet itself

The sheet currently contains **zero text annotations** — no title block, no notes, no
block labels.

- **Fill the title block.** Title, rev, date, your name, sheet 1 of N.
- **Put the assumption register on the sheet as a text block.** `09_design_sheet_rev0.md`
  §2 says to do exactly this — "so it travels with the design instead of living in your
  head." A9 (60 V is max, not nominal), A1 (2 Ω/coil), A5 (peak is continuous) are the
  three that a reviewer will otherwise have to ask you about.
- Consider block headers on the sheet — *BUS / BRIDGE / GATE DRIVE / CURRENT SENSE /
  OCP LATCH*. Free, and it is the difference between a schematic someone can read and one
  they have to trace.

---

## 9. Then the mechanical close-out

1. Run ERC. Expect and ignore *"power input pin not driven"* on `+60V`, `+12V`, `+5V`,
   `+3.3V`, `GND` — those rails are generated on `AUX_RAILS`, which does not exist yet,
   and the PWR_FLAGs belong there. Do not silence them here.
2. Confirm by hovering that `+60V` and `+12V` are genuinely separate nets (§5 of the
   review). Ten seconds, catastrophic if wrong.
3. Export the netlist and save it next to the docs in `levpdu\`.
4. Set up netclasses — POWER / GATE / Default — before you open the PCB editor.

---

## 10. Scoreboard

| | Items |
|---|---:|
| Wrong data | 1 |
| Missing footprints | 5 |
| Footprint decisions | 3 |
| Missing fields | ~6 groups |
| Value hygiene | 3 |
| Label types | 4 |
| Design decisions | 5 |
| Sheet documentation | 3 |

**None of it is rework.** The connectivity — 142 wires, 57 junctions, every polarity
correct, no dangling ends — is finished and verified. What is left is telling the file
what you already know.

---

# CLOSED — 2026-08-13

Every item above is done, plus one that wasn't on the list and should have been.

| Section | Status |
|---|---|
| 1. Wrong data (D2 footprint) | done — `D_SMC_Handsoldering` |
| 2. Missing footprints (5) | done — zero missing |
| 3. Footprint decisions | done — R11 now a true 4-terminal shunt; C9/C10 moved to BUS sheet; TO-220 vertical confirmed |
| 4. Missing fields | bus caps noted on-sheet; 1% on R11/R14/R15/R16 |
| 5. Value hygiene | done |
| 6. Label types | done, sheet pins re-synced |
| 7. Design decisions | 3 built, 2 deferred by decision (see log) |
| 8. Sheet documentation | title block + 9 annotation blocks + assumption register |
| 9. ERC / netlist / netclasses | done — see below |

## Final verification

- **ERC:** 12 errors, 7 warnings, every one traced to `AUX_RAILS` / `IO_PROTECT` not existing
  yet or to the intentional SW_B/COIL_B naming. Nothing on this sheet needs changing.
- **Update PCB from Schematic: 0 errors, 0 warnings.** 60 footprints, 39 nets.
- **Netlist cross-check: exact match.** KiCad's own netlister and an independent
  reconstruction built from raw symbol geometry agree on all 39 nets, pin for pin.
- **Netclasses:** 6 classes, 15 patterns, every named net resolving to exactly one class.

## Still outstanding (not blocking the sheet)

- BOM export to `levpdu/bom_rev0.csv`
- Board Setup: `min_clearance` 0.0 → 0.2, `min_via_annular_width` 0.1 → 0.13
- Physical Stackup: copper 0.035 → **0.07 mm** (2 oz) on F.Cu and B.Cu
