# `power_channel` — title block + on-sheet annotations

Copy-paste source. Everything below is meant to go **on the schematic**, not in a document.

Numbers in these blocks are all traceable: datasheet values verified this session
(IRF100B201 C_rss, V_GS(th); INA240 pinout; 5.0SMDJ package) or carried from
`09_design_sheet_rev0.md`.

---

## 1. Title block

File → Page Settings.

| Field | Value |
|---|---|
| **Title** | `Levitation Coil Drive — Power Channel` |
| **Company** | `Guadaloop — Levitation Subsystem` |
| **Date** | `2026-08-13` |
| **Rev** | `0` |
| **Comment 1** | `Full H-bridge, bidirectional coil drive. 60 V bus · 30 A design · ±45 A trip.` |
| **Comment 2** | `Instantiated twice. Rails on AUX_RAILS, connectors + buffers on IO_PROTECT, bulk caps on BUS.` |
| **Comment 3** | `PROVISIONAL — coil L, k and R are unmeasured. See assumption register on this sheet.` |
| **Comment 4** | `Design record: levpdu/09_design_sheet_rev0.md · review: levpdu/13_schematic_review_power_channel.md rev 1` |

**Change `Company` if that's not your team's name** — I took "Guadaloop" from a folder on
your Desktop, which is a guess, not something you told me.

Comment 3 is the one that matters. A sheet that says out loud which of its inputs are
still unmeasured reads as engineering judgement. A sheet that doesn't reads as a claim
you can't support — and it's the first thing a sharp reviewer will probe.

---

## 2. Section annotations

Place with the **T** (text) tool. Suggested sizes: **2.0 mm bold** for the heading line,
**1.27 mm** for the body. Put each block above or left of the circuitry it describes,
not inside it.

### BUS DECOUPLING + CLAMP

```
BUS DECOUPLING + CLAMP
8 × 1 µF 1210 + 2 × 100 nF, all ≥100 V X7R, inside the commutation loop.
Bulk electrolytics are on the BUS sheet, shared between both channels —
interleaving the two bridges 90° cancels almost all of the bus ripple,
which only helps if the bulk is shared. 90 deg, NOT 180: under unipolar
PWM the bus draws current twice per carrier period, so a 180 deg shift
cancels nothing. See A14.
D2 is a residual clamp (113 V at 44 A), not an energy path. Coil energy is
handled by slow decay — see FAULT LATCH.
```

### POWER STAGE

```
POWER STAGE — FULL H-BRIDGE
IRF100B201, 100 V, 4.2 mΩ. 30 A/yoke design current, D ≈ 0.5 at 60 V into ≈1 Ω.
Bidirectional by requirement, not convenience: HEMS force goes as (B_pm ± B_coil)²,
so the SIGN of coil current changes the force, not just its magnitude.
Q1/Q3 tabs sit at +60 V, Q2/Q4 tabs at the switch nodes — four different
potentials, so every device needs an insulating pad to the heatsink.
```

### GATE DRIVE

```
GATE DRIVE — IR2184 × 2, one per half-bridge
One logic input per half-bridge. The IR2184 generates the complement and enforces
its own dead time, so sign-magnitude, locked-antiphase and mixed decay are all
firmware choices with zero hardware change. Cost: one extra signal per channel.
Bootstrap: +12 V → 1 Ω → ES1D → 1 µF across VB–VS.
0.41 V droop at 405 nC against a 1.5 V budget → D_max ≈ 94 %.
SD is ACTIVE LOW (S̄D̄ per datasheet Lead Definitions).
```

### GATE NETWORK

```
GATE NETWORK — asymmetric on purpose
10 Ω turning on; 4.7 Ω ∥ 10 Ω ≈ 3.2 Ω turning off. The diode conducts only for
current leaving the gate, so turn-on speed is untouched.
Why: IRF100B201 has C_rss = 310 pF and V_GS(th) = 2.0 V MIN. At 0.54 V/ns the
off device sees C_rss · dV/dt · R_g = 2.2 V on its own gate through 10 Ω —
above threshold. Cutting the off-path to ≈3 Ω gives 1.3 V.
Turn-on is deliberately left slow: speeding it up would raise dV/dt and make
the problem worse.
10 k pulldowns return to each FET's OWN source, so gates stay defined before
the drivers have power.
```

### CURRENT SENSE

```
CURRENT SENSE — in-line with the coil
1 mΩ 4-terminal shunt between SW_A and COIL_A. Only this position sees true
bidirectional coil current; high-side or low-side sensing does not.
Common mode is the switch node — a 0–60 V square wave — which is exactly what
the INA240 exists for (CMRR 132 dB DC, 93 dB at 50 kHz).
Gain 20 · REF1→GND, REF2→+3V3 gives 1.65 V at zero current · 20 mV/A · ±82 A FS.
R12/R13 are capped at 10 Ω: anything larger causes gain error against the
amplifier's input impedance.
4-terminal is mandatory, not preferred — at 1 mΩ the solder joints and pad
copper are comparable to the element itself.
```

### OCP THRESHOLDS

```
OCP THRESHOLDS
2.55 V and 0.75 V → ±45 A (30 A legitimate, 60 A ceiling).
Both thresholds and the INA240's 1.65 V mid-scale come from the SAME 3V3 rail,
so the trip point is ratiometric — rail error cancels instead of moving the trip.
```

### WINDOW COMPARATOR

```
WINDOW COMPARATOR — LM393
Inputs are crossed deliberately: A trips on ISNS > 2.55 V, B trips on
ISNS < 0.75 V, and BOTH pull low. Open-drain outputs tied together give OR.
1.3 µs propagation delay is not a problem here: worst-case di/dt is 9730 A/s,
so the current rises 13 mA in that time. The load inductance does the work.
The fast fault is shoot-through, and the IR2184's interlock handles that.
```

### FAULT LATCH

```
FAULT LATCH — 74HC74, set-dominant
Without a latch an over-current self-clears the instant it trips, and the
bridge chatters at the trip point.
FAULT_N → S̄ sets it. Q drives FAULT out; Q̄ drives SD low to shut both
half-bridges down. R18/C22 hold C̄L̄R̄ low at power-up so the latch always comes
up in the no-fault state. R19 pulls SD low if the latch is unpowered —
fail-safe direction.
REV 0 LIMITATION: SD is a hard turn-off, not slow decay. The coil then
freewheels into the bus through the body diodes. Safe while the battery is
connected; not safe with the bus isolated. Accepted for rev 0 — see
levpdu/13_schematic_review_power_channel.md §3.2.
```

### SHEET I/O

```
SHEET I/O
PWM_A, PWM_B   in    one per half-bridge; Schmitt-buffered on IO_PROTECT
RESET          in    clears the fault latch
COIL_A, COIL_B pwr   to the yoke via the barrier strip
ISNS           out   1.65 V ± 20 mV/A
FAULT          out   HIGH = latched fault
```

### ASSUMPTION REGISTER

Put this one somewhere with space — bottom-left or bottom-right of the sheet.

```
ASSUMPTIONS — REV 0, PROVISIONAL
A1  Coil 2 Ω/coil, 1 Ω/yoke      EDD §2.2 + independent geometry check   UNMEASURED
A2  Coil 10 mH/coil, k = 0.85    estimate only                           UNMEASURED
A5  Peak current treated as continuous (deliberately conservative)
A6  Ambient 40 °C
A9  60 V is the MAXIMUM bus voltage, not nominal
A1 is the one that hurts: at 4 Ω the duty goes to 100 % and the bootstrap
needs rework. It is also the easiest thing to measure.
Full register with change costs: levpdu/09_design_sheet_rev0.md §2
```

---

## 3. Why bother

Three of these blocks say something a reader cannot get from the netlist:

- **GATE NETWORK** explains why eight parts exist that look redundant. Without it, the
  next person deletes them.
- **WINDOW COMPARATOR** pre-empts "isn't the LM393 too slow?" — which is the first
  thing anyone asks when they see it in a switching converter.
- **FAULT LATCH** admits a rev-0 limitation in the place where someone would otherwise
  discover it the hard way.

That's the difference between a schematic that has been drawn and one that has been
designed, and it's the part that reads well outside the team.
