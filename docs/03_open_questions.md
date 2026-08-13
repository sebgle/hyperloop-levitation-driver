# Levitation PDU — First-Pass Review & Open Questions

Author: Sebastian · Date: 2026-08-11
Sources reviewed: `Levitation_Power_System_Overview.pdf`, `more_constraints.txt`

**Ground rule for this project: nothing below is assumed. Every number that is not
measured or confirmed in writing is flagged as UNVERIFIED and blocks design.**

---

## Part 0 — What the two documents actually state (verbatim inputs)

| Parameter | Value | Source | Status |
|---|---|---|---|
| Pack voltage | 60 V | both | UNVERIFIED (max charged voltage never given) |
| Coil resistance | 4 Ω / coil | lev team, "as I recall" | UNVERIFIED — never measured |
| Coil inductance | 10 mH / coil | lev team, "as I recall" | UNVERIFIED — never measured |
| Coils per yoke | 2, in parallel → 2 Ω / 5 mH | overview doc | UNVERIFIED — "r we still doing parallel?" was never answered |
| PWM frequency | 16 kHz now, 32 kHz ceiling | lev team | Stated, but see Q9 |
| Baseline current | < 5 A, ideal < 1 A | lev team | Stated |
| Peak current | **60 A total (lev team minimum)** vs **120 A total (overview doc)** | conflict | **CONFLICT — blocks everything** |
| Over-current trip | 45 A / channel | overview doc | Derived from the 120 A figure |
| Topology | Full H-bridge, sign-magnitude PWM | overview doc | UNVERIFIED — bidirectional need never confirmed by lev team |
| Yoke grounding | floating; only common at motor-controller negatives | lev team | Stated |
| Current sensing | not used today, "add it anyway" | lev team | Stated |

---

## Part 1 — Findings from the first-pass math

Working numbers used: per yoke, 2 coils in parallel → **R = 2 Ω, L = 5 mH, τ = L/R = 2.5 ms**.

### F1. The 30 A/yoke figure is exactly 100 % duty cycle. This is a hard ceiling, not a peak.

    I_max = V / R = 60 V / 2 Ω = 30.0 A

There is no transient headroom above this. τ = 2.5 ms is ~40 PWM periods at 16 kHz,
so the coil current is fully resistance-limited in steady state — the inductance only
smooths ripple, it never lets you exceed V/R. Consequences:

- **The 45 A over-current trip can never fire in normal operation** at 60 V into 2 Ω.
  It only fires on a genuine fault (shorted coil, shoot-through, layout short). That is
  still worth having, but it must not be mistaken for thermal protection of the coils.
- **Peak = 100 % duty is incompatible with a bootstrap high-side supply.** The IR2184
  bootstrap capacitor can only recharge while the low side is on. At 100 % duty it
  never recharges, the high-side rail collapses through UVLO, and the FET turns off.
  Practical duty ceiling with a bootstrap is roughly 95–98 %, i.e. **~28.5–29.4 A**,
  and that assumes the refresh window is long enough at 16 kHz. This must be either
  designed around (duty clamp in firmware + hardware) or eliminated (isolated
  high-side supply / charge pump).

### F2. The current target is a 2× conflict and it changes the entire design.

- Lev team: *"minimum is like 60 A total across 4 yokes"* → **15 A / yoke**
- Overview doc: *"30 A / yoke (120 A total)"*

At 15 A/yoke: duty = 50 %, bus draw 60 A, everything gets dramatically easier.
At 30 A/yoke: duty = 100 %, bus draw 120 A, and several things below break.

| | 15 A / yoke | 30 A / yoke |
|---|---|---|
| Duty at peak | 50 % | 100 % (bootstrap fails) |
| Coil dissipation, per yoke | 450 W | 1800 W |
| Coil dissipation, all 4 | **1.8 kW** | **7.2 kW** |
| Bus current | 60 A | 120 A |
| FET conduction (hot, 6.7 mΩ) | 1.5 W/FET, 3.0 W/ch | 6.1 W/FET, 12.1 W/ch |
| Coil stored energy | 0.56 J | 2.25 J |

**The coil dissipation numbers are the biggest unanswered question in this project.**
1800 W into one yoke — or 7.2 kW into the pod — is not a "brief peak during
disturbances", it is a heater. Nothing in either document says how long the coils can
survive this, and nothing in the design limits the duration. See Q3.

### F3. Coil energy dump can exceed the 100 V rating of the FETs and bus caps.

At 30 A a yoke stores 2.25 J. If that energy has to go into the 470 µF bus cap alone
(battery disconnected, contactor open, fuse blown, connector bounce):

    V_peak = sqrt( (½·L·I² + ½·C·V²) · 2 / C ) = **115 V**

That is above the 100 V IRF100B201 and above the 100 V bus caps. At 15 A it is 77 V,
which is fine. So at the higher current target, **the design's survival depends on the
battery being connected** — which makes the battery connection safety-critical rather
than merely functional. This needs an explicit answer (clamp / bleeder / larger bus
cap / TVS energy rating), not a hope.

### F4. The lead's connector is rated 20 A. It cannot carry the specified current.

**Molex 0389220002** — barrier strip, 2 circuit, 8.26 mm (0.325") pitch:

- **Current: 20.0 A max per contact**
- Voltage: 300 V
- Wire: AWG 12–26
- Plating: nickel (mating) / tin (termination), brass + steel base

| Connection | Current | 20 A part? |
|---|---|---|
| Yoke output @ 15 A/yoke | 15 A | Marginal (75 % of rating) |
| Yoke output @ 30 A/yoke | 30 A | **Fails — 150 % of rating** |
| Board battery input | 30 A or 60 A | **Fails** |
| PDU battery input | 60 A or 120 A | **Fails badly** |
| MCU / logic / PWM signals | < 1 A | Fine |

Also: AWG 12 is the largest wire it accepts. AWG 12 is itself only good for ~20–30 A
in chassis wiring. So the wire is a constraint too, not just the connector.

This is a direct conflict between a requirement from your lead and a requirement from
the lev team, and only they can resolve it. See Q1.

### F5. PDU copper: 120 A through 2 oz pours needs to be computed, not assumed.

IPC-2221 external-layer trace width for 2 oz copper:

| Bus current | ΔT = 20 °C | ΔT = 40 °C |
|---|---|---|
| 60 A | 28 mm | 18 mm |
| 120 A | **73 mm** | **48 mm** |

The PDU board is 120 × 80 mm. A 73 mm-wide uninterrupted pour on an 80 mm-tall board
means essentially the entire board is bus copper — and the fuse holder, the TVS, and
the connectors all interrupt it. This is *possibly* achievable at 120 A but only with
deliberate, verified copper geometry (or heavier copper, or a bolted bus bar). At 60 A
it is comfortable. Another reason F2 has to be settled first.

### F6. XT60 at 60 A/board has zero margin.

XT60 is rated 60 A continuous. At 30 A/yoke each board draws 60 A — exactly the
rating. XT90 (90 A) or a bolted lug would be the honest choice. At 15 A/yoke (30 A per
board) XT60 is fine.

### F7. The 125 A ANL fuse does not protect a 120 A load.

A 125 A ANL fuse carries 120 A indefinitely and does not open until roughly 200 A+, and
even then slowly. It is a catastrophic-short fuse, not an overload protection device.
That may be the intent — but it should be a stated intent, not an accident.

### F8. Things in the design that are actually well-chosen

Not everything needs changing. These hold up:

- **INA240** for the current sense. Its enhanced PWM common-mode rejection is
  specifically designed for in-line shunt measurement on a switching H-bridge leg, and
  its offset is low enough that 1 mΩ still resolves the < 1 A baseline
  (1 A → 1 mV → 20 mV out on the A1 gain option).
- **1 mΩ / 3 W shunt.** 0.9 W at 30 A — inside rating.
- **Current ripple.** 188 mA pk-pk at 16 kHz / D = 0.5 (0.6 % of 30 A). The overview
  doc's 0.6 % figure checks out. Ripple is a non-issue at either current target.
- **Diagonal yoke pairing (FL+RR / FR+RL).** The failure-mode reasoning is sound.
- **Separate PDU.** Centralising pack protection is the right call.
- **Freewheel instead of active reversal** for current decay — correct, and it is what
  keeps F3 from being worse than it is.

---

## Part 2 — Questions

### For the lev team (Aditya et al.) — these block the design

**Q1. What is the actual peak current per yoke: 15 A or 30 A?**
"60 A total" and "120 A total" appear in the same conversation. This single number sets
the connector, the wire gauge, the PDU copper, the heatsink, the FET count, and whether
the bootstrap gate drive works at all. I cannot start until it is fixed.

**Q2. Someone has to measure L and R on an actual yoke.**
"As I recall, 4 Ω and 10 mH" is not a design input. An LCR meter at 1 kHz plus a
4-wire DC resistance reading on one coil, and again on a full yoke as wired, takes ten
minutes. Everything in Part 1 moves if these are off by even 30 %.
Also: is the coil DC resistance quoted at room temperature? Copper rises ~0.39 %/°C —
a coil at 120 °C has ~1.4× the resistance it had cold, which cuts peak current
by ~30 % just as you need it most.

**Q3. How long can a yoke sustain peak current before something melts?**
At 30 A/yoke that is 1800 W per yoke / 7.2 kW across the pod. At 15 A it is 450 W /
1.8 kW. I need: (a) a maximum sustained duration at peak, (b) a thermal class /
insulation rating for the coil, (c) a duty-cycle envelope. Without this the board has
no basis for a time-limited current fold-back, which it almost certainly needs.

**Q4. Is bidirectional current actually required?**
The overview doc asserts permanent-magnet-biased suspension where the coil trims the
field both ways. The lev team never confirmed this — they only said "all that matters
is current through the coils." If current is only ever needed in one direction, a full
H-bridge (4 FETs, 2 drivers, in-line sense) collapses to a half-bridge or a simple
low-side switch + freewheel diode, and the part count roughly halves.
If it *is* bidirectional: does the current have to cross zero smoothly, or is a
dead-band at zero acceptable?

**Q5. Coils in series or parallel per yoke — final answer?**
The conversation raises it ("r we still doing parallel?") and never resolves it.
Parallel → 2 Ω, 30 A max, 5 mH. Series → 8 Ω, 7.5 A max, 20 mH. Completely different
board.

**Q6. What is the maximum charged pack voltage, not the nominal?**
"60 V" is a nominal. A 60 V nominal Li-ion pack (~16S) is ~67 V full. If it is 60 V
*nominal* and the FETs are 100 V, the derating margin shrinks. I need the top-of-charge
voltage and the pack's internal resistance / max continuous discharge rating.

**Q7. Are the yokes electrically isolated from the pod chassis?**
An H-bridge drives both terminals, so neither can be grounded. The lev team said the
yokes are floating, which is compatible — but I need confirmation there is no
incidental chassis path, and what the coil-to-core insulation rating is (the switch
node swings 0–60 V at 16 kHz against the core).

**Q8. What exactly is the interface from the controller?**
"The levitation controller outputs low-power PWM signals" is not a specification. I need:
- One PWM + one DIR line per yoke, or two complementary PWMs, or something else?
- Logic level: 3.3 V or 5 V?
- Is the Arduino the source, or is a motor controller still in the path?
- Is there an enable / fault-return line, and does the controller want the OCP fault
  reported back?
- Does it want the current-sense output as analog, or does the board digitise it?

**Q9. Arduino PWM resolution at 16 kHz is a control problem, not just a hardware one.**
On a 16 MHz AVR, 16 kHz PWM gives ~10-bit resolution at best and commonly 8-bit. At
8-bit, one LSB = 60 V/256 → **117 mA of coil current**. To hold a < 1 A baseline you
would have about 8 usable steps. Does the control team know this? It may drive a
decision to put the PWM generation on a better timer or add a hardware current loop.

### For your lead — connector decision

**Q10. The Molex 0389220002 is a 20 A part. Which connections is it mandatory for?**
It is fine for logic and PWM. It is marginal at 15 A/yoke and fails at 30 A/yoke, and
it is nowhere near the 60–120 A battery path. Options to put to them:
- Barrier strip for signals only, lugs / XT90 / Anderson for power
- Move to a higher-rated barrier strip in the same style (needs a part search)
- Multiple contacts paralleled per connection (works, but is a compromise and needs an
  explicit derating)
- Reduce the current target so the 20 A part is legitimate

Also worth asking *why* — is this a standardisation, tooling, or serviceability
requirement? That determines which of the above is acceptable.

### For you, Sebastian — scope of what I do next

**Q11.** Do you want the full H-bridge treated as fixed, or should we re-derive the
topology from the requirements once Q4 is answered?

**Q12.** Are you rebuilding both the control board *and* the PDU, or just one?

**Q13.** How much of this is graded / reviewed by someone, and is there a deadline that
constrains how much re-derivation is worth doing?

**Q14.** What is your LTspice comfort level with switching converters specifically —
should I give you models and let you build the testbench, or walk through the first
simulation step by step?

**Q15.** Is there a house KiCad library, a preferred manufacturer (JLCPCB / PCBWay /
other), and layer-count or copper-weight limits I should design inside?

---

## Part 3 — What I'll produce once these are answered

1. A corrected requirements table with every number sourced and dated.
2. A worked-through topology justification (or a change recommendation).
3. Datasheets + linked reference designs and app notes for each block: gate drive,
   current sense, OCP, bus protection, thermal.
4. A hand-buildable LTspice testbench you assemble yourself, with the models supplied.
5. Calculation sheets you can check: FET losses, heatsink sizing, bootstrap cap,
   gate resistor, shunt and OCP thresholds, copper widths, bus capacitance.
