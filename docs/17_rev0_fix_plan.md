# Rev 0 fix plan — exact steps

> **STATUS: blocks 1–6 executed 2026-08-14. This document is a historical record, not live
> guidance.** Two things in it were later corrected: Block 7 recommends sign-magnitude
> (superseded by unipolar 3-level, A14) with a **180°** interleave (corrected to **90°**).
> Current guidance is A14 in `09_design_sheet_rev0.md`.

Companion to `16_adversarial_review.md`. Work through the blocks in order. Save and run ERC
after each block; do not batch them. Every block is independent, so you can stop after any
one of them and still have a coherent schematic.

Total: **8 new part types, ~19 new components per board, ~3 hours.**

Nothing here redraws existing circuitry. Every change is an insertion, a value edit, or a
footprint edit.

---

## Before you start

1. Close KiCad, commit what you have now, reopen. You want a clean point to roll back to.
2. Order these so they arrive before you need them (all SOIC-14 / 0805 / standard):

| Ref | Part | Qty/board | Why |
|---|---|---|---|
| U6, U208 | **74HCT00** quad 2-input NAND, SOIC-14 | 2 | set-dominance + MCU enable |
| U5, U205 | **74HCT74** (replaces 74HC74) | 2 | RESET at 3.3 V |
| U4, U204 | **LM2903BDR** (replaces LM393DR) | 2 | temperature grade |
| U3, U203 | **INA240A2D** (replaces INA240A1D) | 2 | shunt derating |
| R11, R219 | **WSK2512L5000FEA** 0.5 mΩ 1 % (replaces 1 mΩ) | 2 | shunt derating |
| C101–C106 | **Rubycon ZLH 470 µF 100 V, Ø16 × 31.5** | 6 | Ø18 does not exist; 2.4 A ripple |
| D210 | **SS34** (same as D201/D202) | 1 | +3.3 V hold-up |
| J202 | **Molex 43025-1600**, 2×8 Micro-Fit 3.0 | 1 | 2 more pins + repin |

---

## Block 1 — the fault latch and the MCU enable · ~45 min · 1 IC + 4 passives

**Sheet: `power_channel.kicad_sch`.** This is the important one. It fixes findings 1, 3 and
10 with a single package.

### What you are building

```
   RESET ──┬──────────────► [U6A]  1,2 → 3    RESET_N
           │                       (both inputs tied = inverter)
           │
  FAULT_N ─┼───────────────► [U6B]  4 = RESET_N
           │                        5 = FAULT_N
           │                        6 → RESET_EFF ──► U5 pin 1 (/R)
           │
           │            U5 pin 6 (/Q) ──► [U6C]  9  = /Q
      EN ──┴─────────────────────────────►        10 = EN
                                                   8 → SD_N
                                          [U6D] 12,13 = SD_N (tied)
                                                  11 → SD_DRV
                                    SD_DRV ──[R26 3k3]──► SD net
```

`RESET_EFF = RESET OR NOT(FAULT_N)` — so the latch **cannot be cleared while a fault is
live**, which is finding 1.
`SD_DRV = /Q AND EN` — so the MCU can force shutdown, which is finding 3(c).

### Steps

1. Place **U6 = 74HCT00** (`74xx:74HCT00`, footprint `Package_SO:SOIC-14_3.9x8.7mm_P1.27mm`).
   Place it near U5.
2. Power it: pin 14 → `+5V`, pin 7 → `GND`. Add **C24 = 100 nF 0805 25 V** across them,
   right at the pin.
3. **Gate A (inverter).** Wire pin 1 and pin 2 together and label that node `RESET`
   (the existing hierarchical label already carries RESET onto this sheet — just attach).
   Label pin 3 `RESET_N`.
4. **Gate B.** Pin 4 → `RESET_N`. Pin 5 → `FAULT_N`. Pin 6 → new label `RESET_EFF`.
5. **Rewire U5 pin 1.** It currently sits on `RESET`. Delete that connection and connect it
   to `RESET_EFF` instead. *This is the only existing wire you delete in this whole plan.*
6. **Gate C.** Pin 9 → `SD_Q` (a new label on U5 pin 6 — see step 8). Pin 10 → `EN`.
   Pin 8 → new label `SD_N`.
7. **Gate D.** Wire pins 12 and 13 together → `SD_N`. Pin 11 → new label `SD_DRV`.
8. **Break the old SD net.** U5 pin 6 currently connects straight to the `SD` net. Detach it
   and label U5 pin 6 as `SD_Q` instead. The `SD` net now has: R19 (10 k to GND), U1 pin 2,
   U2 pin 2 — and gets its drive from step 9.
9. Place **R26 = 3.3 k 0805** between `SD_DRV` and `SD`. With R19 = 10 k to GND this divides
   5 V down to **3.76 V**, which is inside the IR2184's 4 V recommended input maximum and
   1.06 V above its 2.7 V threshold. That is finding 10.
10. Add a hierarchical label **`EN`**, type **input**, and attach it to the `EN` node.

### Check before moving on
- U5 pin 1 goes to U6 pin 6, **not** to RESET.
- U5 pin 6 goes to U6 pin 9 only.
- The SD net has exactly four things on it: R19, R26, U1.2, U2.2.
- U5 pin 5 (Q) is now unconnected. That is intentional — Block 4 takes the status readback
  from SD_DRV instead, because that also reads back the enable path.

---

## Block 2 — stop the gate drivers floating · ~20 min · 4 passives

Finding 4. Two parts on each sheet.

**On `power_channel.kicad_sch`:**

1. **R24 = 10 k 0805** from the `PWM_A` net to `GND`, placed at U1 pin 1.
2. **R25 = 10 k 0805** from the `PWM_B` net to `GND`, placed at U2 pin 1.

These have to be on *this* sheet, at the driver. R201–R204 on IO_PROTECT are on the far side
of the buffer and do nothing when the buffer loses its 3.3 V supply.

**On `io_protect.kicad_sch`:**

3. Break `J201` pin 3 off the `+3.3V` net. Label J201 pin 3 `+3V3_IN`.
4. **D210 = SS34** (`Diode_SMD:D_SMA_Handsoldering`), anode on `+3V3_IN`, cathode on `+3.3V`.
   Same orientation as D201 and D202 — copy one of them.
5. **C232 = 220 µF 25 V** (`Capacitor_THT:CP_Radial_D8.0mm_P3.50mm`), + on `+3.3V`, − on
   `GND`. Same part as C201/C202.

Now all three rails have identical blocking-diode-plus-hold-up treatment.

---

## Block 3 — the sense chain · ~30 min · 4 passives, 4 value changes

Findings 7, 11, 12, and the RESET level (finding 2).

**Value and part swaps** — these are property edits, no rewiring:

| Ref | From | To | Why |
|---|---|---|---|
| R11 | `1m` | **`0.5m`** · MPN `WSK2512L5000FEA` | 0.90 W → 0.45 W |
| U3 | `INA240A1D` | **`INA240A2D`** | gain 20 → 50, restores the trip point |
| R15 | `24k` | **`43k`** 1 % | see the arithmetic below |
| U4 | `LM393` · `LM393DR` | **`LM2903B`** · `LM2903BDR` | 0–70 °C → −40/+125 °C |
| U5 | `74HC74` | **`74HCT74`** | belt and braces on the RESET level |

**The threshold arithmetic, so you can check me.** 0.5 mΩ × gain 50 = **25 mV/A**, not the
20 mV/A you have now. For the trip to stay at ±45 A you need ±1.125 V around the 1.65 V
mid-point, i.e. VTH_HI = 2.775 V and VTH_LO = 0.525 V. With R14 = R16 = 10 k and R15 = 43 k,
total 63 k:

    VTH_LO = 3.3 × 10/63 = 0.524 V   →  (1.65 − 0.524)/0.025 = 45.05 A
    VTH_HI = 3.3 × 53/63 = 2.776 V   →  (2.776 − 1.65)/0.025 = 45.05 A

Full scale becomes ±66 A instead of ±82 A — a better match to the 60 A device ceiling, and
inside the INA240's real guaranteed output swing.

**New parts** — the comparator blanking, finding 11:

6. **C25 = 100 nF 0805** from `VTH_HI` to `GND`, at U4 pin 3.
7. **C26 = 100 nF 0805** from `VTH_LO` to `GND`, at U4 pin 6.
   (Those two nodes are 7.7 kΩ Thévenin with nothing on them today, next to a 60 V bridge.)
8. **R27 = 1 k 0805** in series between U3 pin 5 and the comparator inputs. Concretely:
   U3 pin 5 keeps the `ISNS` label — that is what goes out to the connector, unfiltered.
   R27 goes from `ISNS` to a new label `ISNS_F`. Move U4 pin 2 and U4 pin 5 onto `ISNS_F`.
9. **C27 = 4.7 nF 0805 50 V** from `ISNS_F` to `GND`.

R27/C27 gives 4.7 µs of blanking. The coil takes **2.3 ms** to climb from the 45 A trip to
the 60 A ceiling, so this costs you 0.03 A of overshoot and buys immunity to every switching
edge on the board.

### Check before moving on
- `ISNS` (to the connector) taps at U3 pin 5, **before** R27.
- `ISNS_F` feeds only U4 pin 2 and U4 pin 5.

---

## Block 4 — the connector and the status readback · ~45 min · 1 connector + 6 passives

**Sheet: `io_protect.kicad_sch`.** Findings 8, 9, 19, and the EN pins Block 1 needs.

### Why the connector changes

You need two more pins (EN1, EN2). Single-row Micro-Fit 3.0 stops at 12 circuits, so 13 is
not available in the family. Going to **2×8 (43025-1600)** gets you the pins and lets you put
a ground return next to every fast edge, which is finding 19.

If you would rather not change the connector, the fallback is one board-level EN instead of
two and merging the two status lines — that fits in 12 pins. You lose per-channel enable.
I would take the 16-way.

### New pinout

```
    1  GND        2  GND
    3  PWM_A1     4  PWM_A2
    5  PWM_B1     6  PWM_B2
    7  GND        8  GND
    9  EN1       10  EN2
   11  RESET     12  OK1
   13  GND       14  OK2
   15  ISNS1     16  ISNS2
```

Five grounds. Every PWM line has a ground neighbour. RESET is no longer next to a ground pin,
and even if it shorts to one, Block 1 means the latch can still set on a fault — it just
stops holding. Known remaining weakness: ISNS1 and ISNS2 are adjacent, so a short between
them makes both channels read the same current. Detectable in firmware (identical readings
on two channels is not physical); accepted for rev 0.

### Steps

1. Replace the J202 symbol: `Connector_Generic:Conn_01x12` →
   **`Connector_Generic:Conn_02x08_Odd_Even`**. Footprint → the Micro-Fit 3.0 **2×08**
   horizontal entry in `Connector_Molex` (pick it from the chooser and paste me the exact
   string; I have not verified it against your library). MPN `43025-1600`.
2. Rewire to the pinout above.
3. **Status readback, replacing the FAULT output.** Per channel, the source moves from
   U5 pin 5 (Q) to the `SD_DRV` node from Block 1, and the hierarchical label `FAULT`
   becomes **`OK`** (output). Rename it on both `power_channel` and the root sheet.
   - `R206`: 100 R → **10 k**
   - New **`R233` = 15 k 0805** from `OK1_OUT` to `GND`
   - Same for channel 2: `R207` → 10 k, new **`R234` = 15 k**

   The divider turns 5 V into **3.0 V** at the MCU, which fixes the 9–19 mA injection
   (finding 9). More importantly it inverts the failure sense: **HIGH means healthy.** Board
   unpowered, wire broken, connector unplugged, +5 V lost — all pull the line low through the
   15 k, and all read as *not healthy*. That is finding 8, for two resistors.

   Ask firmware to enable an internal pulldown on that pin so a broken wire also reads low.

4. **EN inputs.** Per channel, mirroring how RESET is done today:
   - **R235 = 100 R** in series from J202 pin 9 → `EN1`
   - **R237 = 10 k** from `EN1` to `GND` ← this is the part that matters. Unplugged,
     unbooted, or crashed MCU means EN low means genuine tri-state.
   - Same for channel 2: **R236 = 100 R**, **R238 = 10 k**, J202 pin 10 → `EN2`
5. Add hierarchical labels `EN1` / `EN2` (output from this sheet's point of view — they leave
   IO_PROTECT and enter the channels via the root).

---

## Block 5 — root sheet · ~10 min

1. Open the root sheet, click each of the CH1 and CH2 sheet symbols, **Update sheet pins**
   (right-click → Import Sheet Pin, or the sync command) so the new `EN` pin appears.
2. Draw the stubs and local labels exactly as the existing ones: `EN1` to CH1's EN pin,
   `EN2` to CH2's EN pin, matching labels on the IO_PROTECT sheet symbol.
3. Same for the renamed `OK` pin, which replaces `FAULT` on both channels.

---

## Block 6 — BUS sheet · ~10 min · footprint and value edits only

1. **C101–C106 footprint** → `Capacitor_THT:CP_Radial_D16.0mm_P7.50mm`. Confirm the exact
   string in the chooser. Add MPN for a Rubycon ZLH 470 µF 100 V (Ø16 × 31.5, **2.4 A rms**).
   The 2.4 A part rather than a 1.3 A part is what gives the bank 14.4 A instead of 7.9 A,
   which is the difference between margin and no margin — see Block 7.
2. **R101 footprint** → `Resistor_SMD:R_2512_6332Metric`. Value stays 22 k. At 164 mW a 1206
   is at 100 % of its derated rating next to a hot heatsink and fails **open, silently**,
   after which the bus never bleeds. A 2512 runs it at ~16 %.
3. Optional but recommended: a bus-present LED — 60 V → 100 k → LED → GND, ~0.5 mA, 36 mW.
   Two parts, and it means nobody has to trust that the bleed resistor is still alive before
   putting a spanner on the ring terminals.

---

## Block 7 — the decision that is not a schematic edit · ~5 min

**Commit to a modulation scheme and write it down.** This is finding 5, and it is the one
thing on this list that costs nothing and changes the most.

- **Sign-magnitude with the two channels interleaved 180°** → bus ripple ≈ 0, the six cans
  have large margin, and switching loss roughly halves.
- **Locked antiphase, channels in phase** → 52 A of bus ripple against a bank that can do
  14 A at best. The bank has to become polymer or film.

Take sign-magnitude interleaved unless controls give you a specific reason not to. Then add
it to the assumption register in `09_design_sheet_rev0.md` §2 as **A14**, and put it in the
title block, because two sheets of this design currently depend on the answer.

---

## After all blocks

1. **Annotate** → "Keep existing annotations", so only the new parts get numbers.
2. **Expect the `#PWR` duplicate errors again.** U6 brings new power symbols, and per-instance
   power references still do not get made unique by "keep existing." Send me the ERC output
   and I will patch CH2's path references in the file the way we did on 08-13.
3. **ERC.** Expect zero errors. The SW_B/COIL_B naming warning stays.
4. **Update PCB from Schematic (F8).** Expect ~19 more footprints per channel-side, so about
   **194 total**, and zero missing.
5. Tell me and I will re-run the independent netlist cross-check against the new file.
6. Commit.

---

## What is deliberately NOT in this plan

| Item | Why deferred |
|---|---|
| Dead-time margin (finding 16) | Measure on the first board. The escape hatch is an IR21844, so lay out the SOIC-14 land if you want the option for free |
| VS series resistors + Schottkys (finding 15) | Real, standard practice, 8 parts. Add it if you have the appetite — it is the item I would most like to see promoted into this list |
| Bus voltage sense, heatsink NTC (finding 14) | Needs spare MCU pins and a firmware conversation first |
| TVS / FET voltage class (finding 13) | Needs the slow-decay decision, which is a design task not an edit |
| Reverse-polarity protection (finding 18) | System-level; belongs with the harness and the pack |
| Watchdog, isolation, DC-link current sense | Rev 1 |
