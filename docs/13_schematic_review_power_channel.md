# Schematic Review — `power_channel` sheet

Levitation coil drive stage · Sebastian · rev 1, 2026-08-13
Reviewed against `09_design_sheet_rev0.md`.

> **Rev 1 corrects rev 0's headline finding.** Rev 0 reported the LM393 as powered
> backwards. It is not. See §1 for the retraction and the root cause. Everything from
> §2 onward is unchanged.

**Method — read this first.** I did not eyeball the screenshot. I read the actual
`.kicad_sch` file, rebuilt the connection graph from the raw geometry (symbol origins,
library pin offsets, KiCad's rotation/mirror transforms, wire segments, junctions,
labels, power symbols) and extracted the netlist myself. Every claim below is a
statement about the file, not about a picture of it. Where I could not resolve
something from the file alone, I say so.

Sheet contents: **54 components** (23 C, 19 R, 4 Q, 3 D, 5 U) + 32 power symbols,
142 wires, 57 junctions, 36 labels, 2 no-connect flags, A3 paper.

---

## 0. Geometric hygiene — clean

These are the errors that normally hide in a hand-drawn sheet. The file has none of them:

| Check | Result |
|---|---|
| Wire endpoints ending in mid-air | **none** |
| Labels sitting on nothing | **none** |
| Wires crossing without a junction where one is needed | **none** |
| Wires crossing *with* an unintended junction | **none** |
| Component pins not touching anything | only U5.8 / U5.9, both correctly flagged no-connect |
| Power symbols attached to nothing | **none** |
| Duplicate / overlapping wire segments | none |

Every net resolves. That is a genuinely clean drawing job for 142 wires.

---

## 1. RETRACTED — the LM393 supply is correct

**The first issue of this document claimed U4 was powered backwards. That was wrong.
Sebastian caught it. There is no blocking error on this sheet.**

Correct netlist: **U4 pin 8 (V+) → `+5V`. U4 pin 4 (V−) → `GND`.**

### What I got wrong, and why it matters for the rest of this document

Everything here is reconstructed from raw geometry, which means it all rests on getting
KiCad's rotation matrices right. For a symbol placed at `(at x y 90)` the mapping from
library coordinates to sheet coordinates is one 2×2 matrix, and I solved for it
empirically by testing candidates against the file and keeping the one that made pins
land on wires.

I tested the wrong pair. The two candidates I compared were:

    (0, 1, 1, 0)    det = −1     ← legal
    (0, 1, −1, 0)   det = +1     ← NOT legal for an unmirrored symbol

and picked the second because it made U4's pins land on the +5 V wire and the GND symbol
while the first left them floating. That was real evidence and it pointed at a
physically impossible transform.

**The constraint I skipped:** every unmirrored symbol placement in KiCad is the default
transform `(1, 0, 0, −1)` — determinant −1, because library Y is up and sheet Y is down —
composed with a pure rotation, determinant +1. The product must have **determinant −1**.
A determinant +1 matrix is a *mirrored* placement, and the file says plainly that U4 has
no mirror. That one check eliminates my answer in a single line.

The two legal candidates for the 90° family are `(0, 1, 1, 0)` and `(0, −1, −1, 0)`. I
never tested the second, because I had it filed under 270°. It is the right one:

    90°  → (0, −1, −1, 0)        270° → (0, 1, 1, 0)

Under the correct matrix, U4 unit 3's pins land at y = 59.69 with **V+ at x = 128.27**
(the +5 V wire) and **V− at x = 143.51** (the GND symbol). Which is what the schematic
looks like on screen, which is what Sebastian said.

**The process failure, stated plainly:** I treated "which hypothesis makes more pins land
on wires" as decisive without first checking whether the hypothesis was admissible.
Landing on wires is *evidence*. The determinant is a *constraint*. Constraints get
applied first — they are free, and they delete whole branches before you start weighing
evidence.

And note the shape of the failure, because `08_honest_assessment.md` already named it:
*a design that is internally consistent and externally wrong passes every check you can
run on it.* This time it was the analysis, not the design. My reconstruction was fully
self-consistent under a transform that cannot physically exist, and it stayed
self-consistent right up until someone looked at the actual screen.

### What this retraction does and does not touch

Re-running the extraction with the corrected matrices changes the netlist in exactly one
substantive place — U4's two supply pins. Every other difference is a pin-number swap on
a symmetric two-terminal part (resistors, non-polarised capacitors), where net
*membership* is identical and only the 1/2 labelling flips. Verified by diff.

**The only polarised parts at 90° or 270° are U4 unit 3 and D2.** D2 re-checks correct:
cathode on `+60V`, anode on `GND`. But given the above, please confirm it with your eyes
rather than my arithmetic — **the cathode bar (the flat line with the little Z-ticks
on the ends) should be at the top, against the +60 V rail, with the triangle pointing up
into it.** If it looks the other way round, tell me.

Everything in §2 onward is independent of the rotation question and stands unchanged.

---

## 2. The protection chain is correct

I traced it pin by pin and it does what it is supposed to do.

**LM393 supply** — U4 pin 8 (V+) → +5V, pin 4 (V−) → GND, decoupled by C21 100 nF across
the same two rails. **Correct.**

**Threshold divider** — R14 10k (+3.3V→VTH_HI), R15 24k (VTH_HI→VTH_LO), R16 10k
(VTH_LO→GND).

    VTH_HI = 3.3 × 34/44 = 2.550 V
    VTH_LO = 3.3 × 10/44 = 0.750 V
    trip    = (2.55 − 1.65) / (20 × 1 mΩ) = ±45 A      ✓ matches §4.5

Both thresholds and the INA240's 1.65 V mid-scale derive from the *same* 3.3 V rail, so
the trip point is ratiometric — rail error cancels instead of shifting the trip. That is
a real property of the way you drew it and worth saying out loud in the writeup.

**Comparator polarity** — U4A: `+` = VTH_HI, `−` = ISNS → output pulls low when ISNS
climbs above 2.55 V. U4B: `+` = ISNS, `−` = VTH_LO → output pulls low when ISNS falls
below 0.75 V. Both open-drain outputs (pins 1, 7) tie to `FAULT_N` with R17 10k to +5 V.
Crossed inputs give you OR, not AND. **Correct.**

**Latch** — U5A: pin 4 (S̄/PRE) ← FAULT_N, pin 1 (R̄/CLR) ← RESET node, pins 2 & 3
(D, CLK) → GND, pin 5 (Q) → FAULT, **pin 6 (Q̄) → SD**. Power-on: C22 holds R̄ low,
Q = 0, Q̄ = 1, SD high, drivers enabled. Fault: S̄ low → Q = 1 (FAULT out), Q̄ = 0 →
SD low → shutdown. Set-dominant, powers up in the no-fault state. **Correct.**

**U5B tied off** — pins 10 (S̄) and 13 (R̄) to +5V, pins 11 (C) and 12 (D) to GND,
pins 8 and 9 no-connect. **Correct** — unused outputs left open, unused inputs tied,
which is the right way round.

**R19** 10k from SD to GND: if the latch loses power, SD is pulled low and the bridge
shuts down. Fail-safe in the correct direction. **Correct.**

**INA240** — IN− (1) ← R13 ← COIL_A, IN+ (8) ← R12 ← SW_A, OUT (5) → ISNS, VS (6) →
+3.3V with C20 100 nF, GND (2) → GND, REF1 (7) → GND, REF2 (3) → +3.3V. Verified against
TI SBOS662: pin 4 is "Reserved. Connect to ground or leave floating" — you tied it to
GND, which the datasheet explicitly permits. (My earlier sketch said "leave open"; both
are legal, no change needed.)

Current sign: sourcing current leaves SW_A, crosses the shunt, enters COIL_A, so
V(SW_A) > V(COIL_A) → IN+ > IN− → ISNS rises above 1.65 V. Positive coil current reads
high, which is what the +45 A threshold assumes. **Correct.**

**Bus TVS D2** — cathode on +60V, anode on GND. **Correct.** (I re-derived the 270°
rotation from scratch to check this one; it comes out right.)

**Electrolytics C9/C10** — pin 1 (+) on +60V. **Correct.**

**Bootstraps** — U1: +12V → R5 (1Ω) → D1 (ES1D, anode from R5, cathode to VB) → VB(8),
C4 1 µF across VB–SW_A. U2: identical with R8/D3/C16. Diode orientation correct in both.

**Gate loop** — R1/R2/R9/R10 10 Ω 1206 in series with each gate; R3/R4/R6/R7 10k
pulldowns, each returned to *its own* source (SW_A / GND / SW_B / GND), not to a common
node. **Correct** — this is the detail most people get wrong.

**Bridge** — Q1/Q3 drains on +60V, Q2/Q4 sources on GND, SW_A = Q1.S/Q2.D, SW_B =
Q3.S/Q4.D. Shunt R11 in series between SW_A and COIL_A; COIL_B taken directly off SW_B.
The shunt therefore carries true coil current. **Correct.**

---

## 3. Design-level findings — these are about the design, not the drawing

### 3.1 The bulk capacitors cannot carry the ripple current — quantified

This has been on the open-risk list unquantified. Here is the number.

At the 30 A design point with D ≈ 0.5:

    I_rms(bus) = I_load × √(D(1−D)) = 30 × 0.5 = 15 A RMS per channel

How that 15 A splits between the ceramics and the electrolytics, at 32 kHz:

    8 × 1 µF ceramic:        Z ≈ 1/(2π·32k·8µ)   ≈ 620 mΩ
    2 × 470 µF electrolytic: Z ≈ ESR ≈ 25 mΩ  (two 50 mΩ parts in parallel)

The electrolytics are ~25× lower impedance, so **they take essentially all of it —
roughly 14 A RMS into a pair of parts rated about 2 A RMS each.** They will run hot,
dry out, and fail. The ceramics do not rescue this: to move the split you would need
the ceramic bank below 25 mΩ at 32 kHz, which is ~190 µF of 100 V ceramic before DC-bias
derating. Not buildable.

**Options, cheapest first:**

1. **More electrolytics** — 6× 470 µF/100 V standard radial gets you to ~16 A. Six 18 mm
   cans is a lot of board area.
2. **Polymer or hybrid aluminium** — 3–4× 470 µF/100 V polymer at 3–4 A RMS each. Fewer
   parts, much lower ESR, more expensive. This is what I would do.
3. **Lower the design current** — if the real continuous number turns out well below
   30 A (still an open question with the lev team), the problem shrinks as I².

**What does *not* fix it:** interleaving the two channels 180° out of phase cancels
ripple on the *shared* bus/battery side, but each channel's local commutation loop still
circulates its own ripple through its own nearest caps. Interleaving is worth doing —
it's free in firmware — but do not size the caps on the assumption it will hold.

The schematic topology does not change either way. Add two more C_Polarized symbols now
if you want the footprints, and settle the part at procurement.

### 3.2 The over-current path does the one thing §3.2 of the design sheet forbids

`09_design_sheet_rev0.md` §3.2 is explicit: on a fault, turn **both low-side FETs on**
rather than tri-stating, so the coil dumps into its own resistance and the bus never sees
the energy.

The OCP you have drawn pulls `SD` low, which tri-states both half-bridges. That is a hard
turn-off. The coil current then freewheels through the FET body diodes into the +60 V bus:

    E = ½ · L_yoke · I²  = ½ × 9.25 mH × 45²  = 9.4 J
    into 940 µF from 60 V:  V = √(60² + 2E/C) = 153 V   against 100 V parts

**When this matters:** only if the bus is isolated at the moment of the trip — battery
disconnected, fuse open, contactor open. With the battery present it absorbs the energy
and the bus barely moves, which is the normal case.

**Why I am flagging it anyway:** an over-current is a plausible *cause* of a blown fuse.
The two conditions are correlated, not independent, so "compound failure, ignore it" is
not quite right.

**Two ways forward, pick one and log it:**

- **(a) Accept for rev0.** Log it as a known limitation: OCP hard-off is safe only with
  the bus connected. Zero cost, zero schedule impact. Defensible for a first article.
- **(b) Gate the PWM inputs instead of SD.** Route `PWM_A` / `PWM_B` through a 2-input
  AND (one 74HC08, or two 74HC1G08) with the latch's Q̄. On fault, PWM goes low → the
  IR2184 turns its **low side on** → the coil circulates through Q2 and Q4 → slow decay,
  exactly §3.2, with `SD` left high. Cost: one logic part per board and the 12 V hold-up
  cap you already specified in §4.6. This also makes the OCP path and the bus-fault path
  behave identically, which is worth something on its own.

I would take (b) if you have an hour, (a) if you do not. Either is defensible; silently
having (a) while the design sheet claims (b) is not.

### 3.3 The turn-off diode from §4.3 is missing

Design sheet §4.3 specifies **R_gate on 10 Ω, R_gate off 4.7 Ω + parallel diode**. The
schematic has a single 10 Ω resistor per gate and no turn-off path.

In an H-bridge, when one FET turns on the opposite switch node slews fast and Miller
current through C_gd of the *off* FET tries to pull its gate up. A slow, symmetric
turn-off makes that worse. The asymmetric network is cheap insurance: one small-signal
diode (BAV21 / 1N4148W) and one 4.7 Ω resistor across each 10 Ω.

Four gates × 2 parts = 8 extra parts. Either add them or delete the line from §4.3 —
right now the design sheet and the schematic disagree, and that is exactly the kind of
drift that makes a design document worthless later.

### 3.4 The shunt is the 2512 thick film the design sheet told you not to use

`R11` footprint is `R_2512_6332Metric`. §4.5 says "1 mΩ, 4-terminal, ≥2 W. Use a
metal-element 4-terminal part, **not a 2512 thick film**."

At 45 A the shunt dissipates 2.0 W. A standard 2512 is 1 W. And a thick-film 1 mΩ has a
TCR in the hundreds of ppm/°C, so the trip point walks with temperature.

This was logged as a deliberate compromise, so it is not new — but the footprint is now
committed in the file, and swapping to a 4-terminal part later is a layout change, not a
BOM change. Metal-element parts that fit a 2512-class outline exist (Vishay WSLP2512,
Bourns CSS2H-2512 — 2 W and 3 W versions, ~50 ppm/°C). If you keep 2 terminals, at least
move to a metal-element part now so only the Kelvin question stays open.

### 3.5 The INA240 input filter is not filtering anything

R12 = R13 = 10 Ω, C19 = 1 nF differential.

    f_c = 1/(2π · (R12+R13) · C19) = 1/(2π · 20 · 1n) = 7.96 MHz

That is three decades above anything on this board. It is not wrong — TI's own guidance
(SBOA174) is that the INA240 is *designed* to reject the common-mode step and that heavy
input filtering degrades the CMRR balance it depends on — but you should know that this
network is doing essentially nothing, and say so, rather than have someone assume it is
a 20 kHz filter.

If you want real filtering, put it **after** the INA240 on ISNS, where a resistor costs
you nothing in gain error.

### 3.6 No bus bleed resistor

940 µF at 60 V is **1.7 J** with no discharge path. On a hand-assembled board that people
will probe, that is a shock and short hazard that persists after power-down.

Add one resistor from +60V to GND: 22 kΩ, 0.16 W steady (use a 0.5 W or two 11 k in
series for voltage rating), discharges to under 10 V in about a minute. Cheap, and it is
the kind of thing a reviewer notices immediately.

### 3.7 Single GND

§3.1 of the design sheet lists `AGND` and `DGND` separately at the connector. The
schematic has one `GND`. For rev0 this is defensible — one net, one star point, handled
in layout — but it is a decision, so log it. The INA240 output and the comparator
thresholds both reference this ground while it carries 30–60 A of switched current.

---

## 4. Fix before you run ERC

| # | Item | Action |
|---|---|---|
| 1 | ~~U4 power reversed~~ | **Retracted — see §1. Nothing to fix.** |
| 2 | Missing footprints | `U5` (74HC74), `C19`, `C20`, `R12`, `R13` have no footprint assigned |
| 3 | Hierarchical label shapes | All 7 are `input`. `COIL_A`, `COIL_B` should be `passive` (or `bidirectional`), `ISNS` and `FAULT` should be `output`. As drawn, the parent sheet will throw "input pin not driven" on nets that are actually outputs |
| 4 | Value string consistency | `100 nF` (C2, C17) vs `100nF` (C3, C11, C21, C22, C23) — splits your BOM into two lines. Pick one |
| 5 | `R11` value `1mR` | Ambiguous in a BOM. Use `0R001` or `1m` |
| 6 | Bootstrap cap mismatch | C4 is 1210, C16 is 0805 — same function, same part. Make both 0805 |
| 7 | No voltage rating anywhere | **The most dangerous BOM omission on a 60 V board.** Add a `Voltage` field to every capacitor. C3/C11 (100 nF, 0805) on the bus need ≥100 V. C9/C10 need ≥100 V |
| 8 | Tolerance field | R14/R15/R16 set the trip point — add `Tolerance = 1%` so procurement cannot substitute 5% |
| 9 | Title block | Empty. Fill in title, rev, date, your name |
| 10 | MPN coverage | 9 of 54 parts have an MPN field |

Items 2–10 stand. Note that with the U4 finding retracted, the "power input pin not
driven" errors ERC will raise on `+5V`, `+3.3V`, `+12V`, `+60V` and `GND` are now
*purely* the expected missing-PWR_FLAG messages, with nothing hiding inside them.

**ERC messages you should expect and should NOT "fix" on this sheet:**

- *Power input pin not driven* on `+60V`, `+12V`, `+5V`, `+3.3V`, `GND` — correct. Those
  rails are generated on `AUX_RAILS`, which does not exist yet. The PWR_FLAGs belong
  there, not here. Do not sprinkle PWR_FLAGs on this sheet to silence them.
- Possible *"net has more than one name"* on the SW_B / COIL_B node. That node genuinely
  is both — half-bridge B's switch node *is* the coil B terminal, because the shunt is
  only in the A leg. Intentional.

---

## 5. Verify this one thing about the +60 V net

`#PWR01` is the `power:+12V` library symbol with its **Value** field edited to `+60V`.

In this file every power symbol's library pin is unnamed, which means KiCad takes the net
name from the Value field — so `+60V` should be a distinct net from `+12V`. The netlist I
extracted agrees: `+60V` contains only the bridge drains and the bus bank; `+12V` contains
only the two driver VCC pins.

But confirm it in KiCad rather than taking my word for it, because the failure mode is
catastrophic — if those two merged, 60 V lands on the IR2184 VCC pins. **Hover the +60 V
rail and the +12 V rail and read the net names off the status bar.** Ten seconds.

---

## 6. File hygiene — fix this before you do anything else

Your project is at `Desktop\final_lev\`. The root sheet's `Sheetfile` property reads:

    ..\..\Downloads\power_channel.kicad_sch

**Your live schematic is in your Downloads folder, outside the project.** And there are
two stale decoys sitting *inside* `final_lev\`:

| File | Symbols | Status |
|---|---|---|
| `Downloads\power_channel.kicad_sch` | 58 | **live — this is your work** |
| `final_lev\power_channel.kicad_sch` | 37 | stale (no INA240, no LM393, no 74HC74, no shunt) |
| `final_lev\copy_power_channel.kicad_sch` | 24 | older still (bridge + drivers only) |

Downloads is the folder people clean out. And the two decoys are one mis-click from being
loaded and quietly losing you a day.

**Procedure — do it in this order:**

1. Close KiCad completely (there is a `~final_lev.kicad_sch.lck` right now).
2. Move `final_lev\power_channel.kicad_sch` and `final_lev\copy_power_channel.kicad_sch`
   somewhere out of the project — an `_old\` subfolder is fine.
3. Copy `Downloads\power_channel.kicad_sch` into `final_lev\`.
4. Open `final_lev.kicad_sch`, right-click the sheet symbol → Properties → set the sheet
   file to `power_channel.kicad_sch` (no path).
5. Open the sheet and confirm you see the INA240, the LM393 and the 74HC74. If you see a
   bare H-bridge, you loaded a decoy — back out and try again.
6. Then put the whole `final_lev` folder under git, or at least next to `levpdu`.

I can run steps 2 and 3 for you once KiCad is closed — say the word.

---

## 7. Summary

**No blocking errors.** The originally-reported LM393 supply reversal was my mistake and
is retracted in §1, with the root cause written up there because the root cause is more
useful than the finding was.

What remains:

- One quantified component problem — bus electrolytic ripple current, ~7× over rating (§3.1)
- One architectural decision to make explicitly rather than by accident — OCP hard-off
  vs. slow decay (§3.2)
- Two design-sheet items that did not make it into the drawing — gate turn-off diode,
  shunt type (§3.3, §3.4)
- Four smaller design notes (§3.5–3.7)
- Nine housekeeping items before ERC (§4)

The drawing itself — 142 wires, 57 junctions, 54 parts, no dangling ends, no missing
junctions, no stray labels, no floating power symbols, every polarity correct — is clean.
The real work left on this sheet is component selection and two documented decisions, not
correction.

---

## 8. Revision history

| Rev | Date | Change |
|---|---|---|
| 0 | 2026-08-12 | First issue |
| 1 | 2026-08-13 | **§1 retracted.** LM393 supply is correct; the reported reversal was an error in my geometric reconstruction (wrong rotation matrix, determinant +1, physically inadmissible). Caught by Sebastian from the schematic on screen. Netlist re-extracted with corrected matrices; one substantive change (U4 pins 4/8), all other deltas are pin-number swaps on symmetric parts. D2 polarity re-verified. §§2–6 unaffected. |
