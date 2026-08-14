# BOM caveats — where the schematic symbol is NOT the part to order

Rev 0 · 2026-08-14

KiCad's symbol libraries do not contain every part this design uses. In five places a
near-equivalent symbol was used and the **Value** and **MPN** fields carry the real part.
**Procurement must order by MPN, never by symbol name.** Three of these substitutions are
not cosmetic — ordering the symbol's part instead would break the design in a way that does
not show up until the board is powered.

| Ref | Symbol says | ORDER THIS | If you order the symbol's part instead |
|---|---|---|---|
| U6, U208 | `74xx:74LS132` | **74HCT132D,653** | **Breaks the safety interlock — see §1** |
| U4, U204 | `Comparator:LM393` | **LM2903BDR** | Part is only rated 0–70 °C on a 54 W board |
| U5, U205 | `74xx:74HCT74` ✓ | **74HCT74** | Do not accept a 74HC74 substitution — see §2 |
| U3, U203 | `Amplifier_Current:INA240A2D` ✓ | **INA240A2D** | Gain 50. An A1 (gain 20) makes every current reading 2.5× low |
| R11, R219 | `Device:R_Shunt`, value `0.5m` | **WSK2512L5000FEA** | 0.5 **milliohm**. A 0.5 Ω part would be a dead short's worth of error |

---

## 1. U6 / U208 — the one that matters most

The symbol is `74LS132` only because the KiCad library has no HCT variant of the quad
Schmitt NAND. **The part must be 74HCT132.**

74LS is bipolar TTL and its inputs *source* current when low: **I_IL = −0.4 mA**. R244, the
10 kΩ pulldown that makes the `EN` interlock default to OFF, cannot sink that:

    0.4 mA × 10 kΩ = 4 V

The pulldown would be completely defeated. **EN would float high, the board would power up
enabled, and the entire MCU shutdown interlock would be decorative.** The same current would
put 2 V across the RESET pull-up network and destroy the power-on-reset timing.

74HCT has ±1 µA input current, which is what makes 10 kΩ pulldowns and megohm-scale RC
timing work at all. It is also TTL-threshold (V_IH = 2.0 V), which is required because EN and
RESET arrive from a 3.3 V MCU into a 5 V-powered part.

**Do not accept 74HC132 either** — HC at 5 V needs V_IH = 0.7 × VCC = 3.5 V, above what a
3.3 V MCU delivers.

## 2. U5 / U205 — same threshold argument

74**HCT**74, not 74HC74. The design originally used HC and it was a finding: at VCC = 5 V an
HC part needs 3.5 V for a guaranteed HIGH, and the RESET line sits at 3.33 V.

## 3. U4 / U204 — temperature grade

The base LM393 is graded **0 °C to 70 °C**. This board dissipates ~54 W with eight TO-220s on
a common heatsink. LM2903B is pin-identical and graded −40 °C to +125 °C. The symbol name is
LM393 only because the library lacks an LM2903B entry.

Its supply is **+12 V, not +5 V** — that is deliberate. The LM2903B's input common-mode
ceiling is (V+ − 2.0 V) over temperature, and the 2.776 V trip threshold does not fit under a
5 V rail once the +5 V blocking diode's drop is counted. Outputs are open-drain and still
pull up to +5 V through R17, so nothing downstream changes.

## 4. R11 / R219 — read the value carefully

`0.5m` means **0.5 milliohm**, 4-terminal Kelvin, 1 %, 2512. This is a current-sense element
carrying the full coil current; a wrong value here is a wrong trip point and a wrong current
reading everywhere.

WSK2512 is rated **1.0 W at 70 °C** and dissipates 0.45 W at the 30 A design current.
**Do not substitute a 2-terminal part** such as WSLP2512 — the Kelvin connection is why the
board can use a 0.5 mΩ element at all.

---

## Connectors — board halves only; the harness needs its own line items

The schematic carries **only the PCB-side parts**. None of the mating hardware is in this BOM
and it must be added to the harness BOM or the boards arrive with nothing to plug into.

| Ref | Board part (in this BOM) | Harness side (NOT in this BOM) |
|---|---|---|
| J201 | Molex **43650-0400**, 1×4 Micro-Fit 3.0 header | 43645-0400 housing + 4 crimps |
| J202 | Molex **43045-1600**, 2×8 Micro-Fit 3.0 header | **43025-1600** housing + 16 crimps |
| J101, J203, J204 | Molex **38969-0002** ring-terminal block | ring lugs sized to the cable |

Note J202 changed from a 1×12 to a 2×8 on 2026-08-14. **Any harness already built to the old
12-way pinout is obsolete** — the pin assignment changed as well as the shell.

`43045` is the PCB header; `43025` is the wire-side receptacle housing. They are easy to
confuse and were confused once during this design.

---

## Capacitors

**C101–C106** — `100ZLH470MEFC16X31.5`, Rubycon ZLH, 470 µF 100 V, Ø16 × 31.5 mm.

The series matters. Rated ripple is **2.4 A rms at 105 °C / 100 kHz**, derating to about
**2.28 A at 16 kHz** by Rubycon's own frequency-correction table — roughly **13.7 A for the
bank of six**. A general-purpose series such as Nichicon UPW is only 1.31 A per can (7.9 A for
six), which does not cover the design. **Do not substitute on capacitance and voltage alone.**

There is no 470 µF / 100 V part in a Ø18 case in any mainstream series — that value only
exists at Ø16. Verify the **7.5 mm lead pitch** against Rubycon's own drawing before release;
it is the standard pitch for Ø16 but was not confirmed from the primary table.

All other capacitors carry a `Voltage` field. On a 60 V board that field is engineering
intent, not a purchasing detail — the bus bank and the bridge ceramics are ≥100 V and must
not be substituted downward.

## Resistors

R14, R15, R16 (and R218, R220, R221) set the over-current trip point and are specified
**1 %**. R11/R219 are 1 %. Do not accept 5 % substitutions on any of these six — they move
the trip point directly.

R101 is a **2512**, not a 1206. At 164 mW a 1206 sits at ~100 % of its derated rating beside
a hot heatsink, and a thick-film resistor at its limit fails **open, silently**, after which
the bus never bleeds.
