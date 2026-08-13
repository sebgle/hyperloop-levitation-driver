# Drive Topology — Derivation From Requirements

Levitation coil drive stage · Sebastian · 2026-08-11 · Rev 0

> **Purpose.** The existing design specifies a full H-bridge per yoke. This document
> does not assume that. It derives the drive topology from the load and control
> requirements, so that the H-bridge is either *justified* or *replaced* — and so that
> the reasoning is on record either way.
>
> **Status of inputs.** R and L are UNVERIFIED (quoted from memory by the lev team, never
> measured). The bidirectional requirement is UNVERIFIED. Every conclusion below is
> conditional on those, and is written so that the answer falls out once they arrive.

---

## 1. The load

Working numbers, per yoke, two coils in parallel:

| Quantity | Value | Status |
|---|---|---|
| Coil resistance R | 2 Ω | UNVERIFIED |
| Coil inductance L | 5 mH | UNVERIFIED |
| Electrical time constant τ = L/R | **2.50 ms** | derived |
| Bus voltage V | 60 V | UNVERIFIED (nominal vs. top-of-charge unknown) |
| PWM frequency | 16 kHz (32 kHz ceiling) | stated |

Two consequences follow immediately, and they drive everything else.

**(a) The load is resistance-dominated, not inductance-dominated.**
The PWM period at 16 kHz is 62.5 µs, which is τ/40. The inductance therefore does not
store and release meaningful energy cycle-to-cycle — it only smooths ripple. Steady-state
current is set purely by Ohm's law:

    I = V · D / R          (D = duty cycle)

So `I_max = 60 V / 2 Ω = 30 A` at D = 1.0, and there is **no transient headroom above
30 A**. Any "peak current" spec above 30 A is unachievable at this bus voltage and this
coil resistance. This is the single most important structural fact about the design.

**(b) The open-loop current bandwidth is 64 Hz.**

    f_c = 1 / (2πτ) = 1 / (2π · 2.5 ms) = 63.7 Hz

For a magnetic levitation loop — which is open-loop unstable and typically wants a
current loop several times faster than the position loop — 64 Hz is not obviously
enough. This number needs to go to the controls team (see the open-questions doc, Q3
and Q9). It is also the strongest technical argument for adding the current sensing the
lev team was ambivalent about: an inner current loop with voltage overdrive can push the
effective current bandwidth well above the natural 64 Hz, but only if you can measure
the current.

---

## 2. Does the current need to reverse sign?

This is the question that decides the topology, and it is a *physics* question about the
yoke, not an electronics preference.

### Case A — pure electromagnet, no permanent magnet

An electromagnet attracting a ferromagnetic rail produces force proportional to **B²**:

    F ∝ B² ∝ I²

Force is therefore **independent of current direction**. Reversing the current flips the
field polarity and produces exactly the same attractive force. Bidirectional current buys
nothing. → **Unidirectional current.**

### Case B — permanent-magnet-biased suspension

The permanent magnet establishes a fixed bias flux B_pm that carries the static weight.
The coil adds or subtracts:

    B_total = B_pm ± B_coil        F ∝ (B_pm ± B_coil)²

Now current direction *does* matter: positive current increases the force, negative
current decreases it below the bias point. Without the ability to reverse, the system can
only ever pull harder than the magnet already pulls — it can never reduce the force below
the static bias, so it can only correct disturbances in one direction.
→ **Bidirectional current required.**

### Where this stands

The overview document asserts Case B ("the yokes use magnets that carry the pod's static
weight at essentially zero current"). **The lev team never confirmed this.** Their only
statement on the subject was *"all that matters is current through the coils"*, which is
compatible with either case.

This is open question **Q4** and it must be answered before a schematic is drawn. It is
worth noting that the fact they run the coils from motor controllers today is weak
evidence for Case B — but a motor controller is also just what you reach for when you
need a PWM current source, so it proves nothing.

---

## 3. The requirement everyone misses: negative *voltage* is not the same as negative *current*

Even if the current is strictly unidirectional (Case A), the drive may still need to be
able to apply **negative voltage** across the coil, in order to pull the current *down*
quickly. These are separate capabilities and conflating them is the most common error in
inductive-load drive design.

At any operating current I, the achievable current slew rates are:

| Applied coil voltage | di/dt |
|---|---|
| +V (drive)     | (V − I·R) / L |
| 0 (freewheel, "slow decay") | −I·R / L |
| −V (reverse, "fast decay")  | −(V + I·R) / L |

Evaluated for this load:

| I (A) | Duty | Rise at +V | Decay at 0 V | Decay at −V |
|---:|---:|---:|---:|---:|
| 0  | 0 %   | +12.0 A/ms | 0 A/ms      | −12.0 A/ms |
| 1  | 3.3 % | +11.6 A/ms | **−0.4 A/ms** | −12.4 A/ms |
| 5  | 16.7 %| +10.0 A/ms | **−2.0 A/ms** | −14.0 A/ms |
| 15 | 50 %  | +6.0 A/ms  | −6.0 A/ms   | −18.0 A/ms |
| 30 | 100 % | **0 A/ms** | −12.0 A/ms  | −24.0 A/ms |

### The finding

**At the normal operating point the freewheel path is catastrophically asymmetric.**

The lev team specified baseline current **< 5 A, ideally < 1 A**. That is where this
system lives almost all of the time. At 1 A:

- current can be *raised* at 11.6 A/ms
- current can only be *lowered* at 0.4 A/ms

That is a **29 : 1 asymmetry**. At 5 A it is still 5 : 1.

The reason is structural: slow-decay di/dt is `−I·R/L`, which goes to zero as the current
goes to zero. A freewheel-only drive is *least* able to reduce current exactly where the
system normally operates. A PID loop asked to control a plant whose response is 29× faster
in one direction than the other will either be detuned to the slow direction (losing most
of its bandwidth) or will overshoot persistently in the fast direction.

Time to bring current fully to zero:

| I (A) | Slow decay (5τ) | Fast decay | Speed-up |
|---:|---:|---:|---:|
| 1  | 12.5 ms | 0.08 ms | 152× |
| 5  | 12.5 ms | 0.39 ms | 32× |
| 15 | 12.5 ms | 1.01 ms | 12× |
| 30 | 12.5 ms | 1.73 ms | 7× |

**Conclusion: this drive needs a −V capability regardless of whether the current ever
reverses sign.** That eliminates the simplest topology from contention on control grounds,
before cost or part count is even considered.

Reference for the terminology and the circuit forms: TI **SLVA321A**, *Current
Recirculation and Decay Modes* (fast / slow / mixed decay, Figures 2-1 through 2-5).

---

## 4. The three candidate topologies

| | Switches | Diodes | Coil voltage states | Current direction | Quadrants |
|---|---:|---:|---|---|---|
| **T1** Low-side switch + freewheel diode | 1 | 1 | +V, 0 | unidirectional | 1 |
| **T2** Asymmetric half-bridge | 2 | 2 | +V, 0, **−V** | unidirectional | 2 |
| **T3** Full H-bridge | 4 | (body) | +V, 0, −V | **bidirectional** | 4 |

### T1 — single low-side switch + freewheel diode
One N-channel FET in the coil return, one diode across the coil. Cheapest possible: no
high-side drive, no bootstrap, no level shifting.
**Rejected on the Section 3 finding.** It has no −V state, so it inherits the 29 : 1
slew asymmetry at the operating point. It is the right answer for a solenoid you only need
to turn on and off, and the wrong answer for a coil inside a stability loop.

### T2 — asymmetric half-bridge
One high-side switch above the coil, one low-side switch below it, and two diodes
returning to the opposite rails. This is the standard topology for switched-reluctance
drives and proportional solenoids.

- Both switches on → **+V** across coil
- One switch on → **0 V** (freewheel through one switch + one diode)
- Both switches off → **−V** (current flows through both diodes back into the bus)

Gets the full +V / 0 / −V control set with **half the switches and half the gate drivers
of an H-bridge**. Current is unidirectional. The −V state regenerates into the battery,
which a battery absorbs happily.

**This is the correct answer if — and only if — the lev team confirms Case A.**

### T3 — full H-bridge
Four switches, two half-bridge drivers. Adds true current reversal on top of everything
T2 offers.

**This is the correct answer if the lev team confirms Case B (PM-biased).**

### Decision rule

```
Is the suspension permanent-magnet biased (Q4)?
├── YES → current must reverse         → T3, full H-bridge      (as originally specified)
└── NO  → current is unidirectional
         └── Does it need fast decay? (Section 3 says YES)
                                        → T2, asymmetric half-bridge
                                          → ~50% fewer switches and drivers
```

The original design's H-bridge is **not wrong** — it is a superset of T2 and it will work
either way. But if Case A is true, it is carrying twice the switches, twice the gate
drivers, twice the conduction loss and twice the failure modes for a capability that is
never used. That is worth ten minutes of asking before it is worth ten hours of laying out.

---

## 5. What does *not* change between T2 and T3

Worth noting, because it means work can start now on the parts that are settled:

- The current-sense architecture (shunt placement, INA240, filtering)
- The over-current comparator and its latch
- Bus capacitance and the coil-energy-dump analysis
- Bus protection: fuse, TVS, precharge, reverse polarity
- The gate-drive bootstrap problem and the max-duty-cycle limit — **both T2 and T3 have a
  high-side switch**, so this is unavoidable in either case
- Thermal design and heatsinking of the high-side/low-side pair
- Connector and copper sizing (once the current target is settled)

The topology question changes the *count* of switches, not the *design* of any one of them.

---

## 6. Consequences to carry forward

1. **30 A/yoke is 100 % duty.** A bootstrap high-side supply cannot sustain 100 % duty —
   the bootstrap capacitor never recharges and the driver trips its V_BS undervoltage
   lockout. Either the peak current target drops below ~29 A, or the high-side supply
   becomes a charge pump or isolated rail. Quantified in Infineon **AN-1123** §2.2; the
   charge-pump remedy is TI **SLVA444** §3.
2. **The natural current bandwidth is 64 Hz.** The controls team needs to confirm this is
   compatible with the levitation loop. If it is not, an inner current loop is mandatory,
   which makes the current sensing mandatory rather than optional.
3. **Fast decay is a requirement, not a feature.** Whichever topology is chosen must be
   able to apply −V across the coil.
4. **Nothing can be finalised until Q1 (15 A or 30 A?), Q2 (measured L and R) and
   Q4 (bidirectional?) are answered.**

---

## Sources

- TI **SLVA321A**, *Current Recirculation and Decay Modes* — https://www.ti.com/lit/pdf/slva321
- TI **SLVAE59A**, *Using Motor Drivers to Drive Solenoids* — https://www.ti.com/lit/pdf/slvae59
- Infineon **AN-1123**, *Bootstrap Network Analysis* — https://www.infineon.com/assets/row/public/documents/24/42/infineon-bootstrap-network-analysis-applicationnotes-en.pdf
- TI **SLVA444**, *Providing Continuous Gate Drive Using a Charge Pump* — https://www.ti.com/lit/an/slva444/slva444.pdf
