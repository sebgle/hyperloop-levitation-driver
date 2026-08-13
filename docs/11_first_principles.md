# The Whole Thing, From First Principles

Levitation coil drive stage · written for Sebastian · 2026-08-11

This assumes nothing. It builds from "what is the pod trying to do" to "why is there a 1 µF
capacitor next to pin 5." Read it in order — each part depends on the one before.

---

# PART 1 — The physical problem

## 1.1 What the pod is actually doing

There's a steel rail above the pod. The pod hangs below it, not touching, held up by magnetic
attraction. Pull up hard enough and the pod rises; pull too hard and it slams into the rail;
pull too little and it drops.

The numbers from your EDD:

- Pod mass **316 kg** → weight **3100 N** (316 × 9.81)
- Four yokes share it → **775 N per yoke**
- Nominal gap: **8 mm**

A "yoke" is a U-shaped steel core with a coil wound on each leg, and a permanent magnet
embedded in each leg. It's an electromagnet that can be adjusted.

## 1.2 Why this is hard: the system is unstable

This is the single most important fact in the project, and everything else exists to deal
with it.

Magnetic attraction gets **stronger as the gap closes**. So:

```
gap gets slightly smaller → force gets stronger → pod pulled up harder
    → gap gets smaller still → force stronger still → ... → SLAM
```

And in the other direction:

```
gap gets slightly larger → force gets weaker → pod falls
    → gap larger still → force weaker → ... → DROP
```

There's no equilibrium the system settles into on its own. It's a pencil balanced on its tip.
Nudge it either way and it accelerates away from where it was.

**This is called an open-loop unstable plant**, and it means the pod *only* stays up because
something is actively measuring and correcting, thousands of times per second, forever.

How fast? From your force-vs-gap curve, the runaway has a time constant of about **32 ms**.
That's how long the pod takes to meaningfully depart. Everything in the control chain — the
sensor, the maths, and *your board* — has to be comfortably faster than that.

## 1.3 Why permanent magnets: the "zero-power" trick

You *could* levitate with coils alone. But holding 3100 N with coils means running current
continuously, forever, and current in a resistance means heat. Park the pod for ten minutes
and you're heating the coils the whole time for nothing.

So HEMS — **Hybrid Electromagnetic Suspension**:

- **Permanent magnets** provide a constant pull, sized so that at the 8 mm nominal gap they
  hold up the pod *by themselves*, at **zero current**.
- **Coils** only push the total force slightly up or slightly down to correct disturbances.

That's why your team's spec says baseline current **under 5 A, ideally under 1 A**, but peak
**30 A**. Normally the coils are doing almost nothing. They only work hard during a
disturbance — a bump in the track, a load shift, lift-off.

## 1.4 The consequence that decided your entire circuit

Magnetic force goes as the **square of the field**:

    F ∝ B²

For a plain electromagnet, B comes only from the coil, and B ∝ current. So F ∝ I². **Squaring
kills the sign.** +10 A and −10 A produce *exactly the same force*. Current direction is
meaningless. You'd only ever need current one way.

But with a permanent magnet in the circuit, the fields **add**:

    B_total = B_pm ± B_coil        so        F ∝ (B_pm ± B_coil)²

Now the sign matters enormously:

- Current one way → coil field **adds** to the magnet → **more** force → pod rises
- Current the other way → coil field **opposes** the magnet → **less** force → pod falls

Without the ability to reverse, you could only ever pull *harder* than the magnet already
pulls. You could never reduce the force below the bias. You'd have a system that can catch
the pod when it drops but can do nothing when it rises.

> **This is why your board needs to push current through the coil in both directions, and
> that requirement is what forces the H-bridge in Part 4.**

Your EDD confirms it: Figure 3 plots force against gap for currents from **−16 A to +12 A**.
Negative current is a design case, not an accident.

## 1.5 The control loop

```
gap sensor ──> microcontroller ──> YOUR BOARD ──> coil ──> force ──> gap
     ^              (PID)          (power stage)                       |
     |                                                                 |
     └─────────────────────────────────────────────────────────────────┘
```

The sensor measures the gap. The microcontroller compares it to the target and computes "I
need this much current, in this direction." **Your board turns that request into real current
from the battery.**

You are not designing the controller. You are designing the muscle that executes what the
controller decides. But the muscle has to be fast and honest, or the controller's maths is
worthless.

---

# PART 2 — From "I want current" to "I have current"

## 2.1 What the coil looks like electrically

Two things:

- **Resistance** — the copper wire's own resistance. Turns current into heat. About **2 Ω**
  per coil, and since your two coils are wired in parallel, **1 Ω per yoke**.
- **Inductance** — a coil of wire stores energy in its magnetic field. About **10 mH** per
  coil (unmeasured — this is our weakest number).

Resistance sets how much current you get for a given voltage: `I = V/R`.
Inductance sets **how fast** current can change.

## 2.2 The inductor is the key mental model

If you remember one thing, remember this:

> **An inductor resists changes in current. Current through an inductor behaves like a heavy
> flywheel — it has momentum. You can speed it up or slow it down, but you cannot stop it
> instantly, and if you try, something breaks.**

The governing equation:

    V = L · (di/dt)        rearranged:        di/dt = V / L

**To change current, you apply voltage.** More voltage = faster change. And critically:

> **If you try to force current to change instantly (di/dt → ∞), the voltage goes to
> infinity.** That's what an arc is when you yank a plug out of an inductive load.

For your yoke: L ≈ 9.25 mH, so 60 V gives

    di/dt = 60 / 0.00925 ≈ 6500 A/s ≈ 6.5 A per millisecond

To swing from 0 to 30 A takes about 4.6 ms. **That's slow compared to your 31 µs PWM
period, and it's the same order as the 32 ms instability you're fighting.** This is why the
current-loop speed question keeps coming up.

## 2.3 The time constant

Left alone with a fixed voltage, the current rises exponentially toward `V/R` with time
constant

    τ = L / R = 0.00925 / 1 ≈ 9.25 ms

After 1τ you're at 63% of final, after 5τ essentially there. **This one number governs how
quickly your board can obey the controller.**

---

# PART 3 — Why PWM

## 3.1 The obvious approach, and why it fails

You want 15 A in a 1 Ω coil, so you want 15 V across it. You have 60 V. Drop the other 45 V
across something.

A transistor operated in its linear region can do exactly that. It would also dissipate:

    P = 45 V × 15 A = **675 watts**

In one transistor. That's a space heater with a silicon die inside it. Across your four
yokes you'd be throwing away kilowatts as heat, out of a battery you're carrying.

**Linear regulation is unusable at this power level.**

## 3.2 Switching: the trick

A switch has two states, and **both of them dissipate almost nothing**:

- **ON** — big current flows, but voltage across the switch ≈ 0 → `P = 0 × I ≈ 0`
- **OFF** — full voltage across it, but no current → `P = V × 0 ≈ 0`

Power is only lost during the *transition* between states, which lasts tens of nanoseconds.

So instead of holding a steady 15 V, you slam the full 60 V on and off very fast:

```
60V ┐   ┌───┐   ┌───┐   ┌───┐
    │   │   │   │   │   │   │        25% of the time ON
  0 ┴───┘   └───┘   └───┘   └───     average = 15 V
```

The fraction of time spent ON is the **duty cycle**. Average voltage = duty × 60 V.

## 3.3 Why this works — the coil does the averaging for you

Here's the elegant part. The coil's time constant is **9.25 ms**. Your PWM period at 32 kHz
is **31 µs**. That's a ratio of about **300 to 1**.

The current physically cannot follow the individual pulses. It only responds to the *average*.
The coil is a low-pass filter, and it filters the PWM into smooth DC on its own — no
additional filtering needed.

What's left is a small ripple. For your design, at 50% duty and 16 kHz, the ripple is about
**188 mA** on top of 30 A — **0.6%**. Negligible.

> **PWM gives you the efficiency of a switch with the controllability of a variable voltage.
> This is the foundational idea behind essentially all modern power electronics.**

## 3.4 What the microcontroller actually sends

Not a voltage or a current — a **duty cycle**. "Be on 25% of the time." Your board converts
that to real power. The controller is thinking in percentages; your board is the thing that
makes those percentages mean 30 amps.

---

# PART 4 — The H-bridge

## 4.1 One switch is not enough

Simplest possible arrangement:

```
   +60V ──────┬──────
              │
            [COIL]
              │
              ├── SWITCH
              │
   GND ───────┴──────
```

Close the switch, current flows down through the coil. Open it, current stops.

**Two problems.**

**Problem 1 — current can only go one way.** Section 1.4 established you need both.

**Problem 2 — and this one destroys the circuit.** When you open the switch, the coil's
current has nowhere to go. But the current has momentum (§2.2) and *insists* on continuing.
`V = L·di/dt` with di/dt enormous means the voltage across the switch spikes to hundreds or
thousands of volts until something arcs or breaks down.

**Any inductive load needs a path for its current at all times.** This is non-negotiable.

## 4.2 The freewheel path

Add a diode:

```
   +60V ──┬─────────────
          │
        [COIL]      ╱│
          │   ◄────╱ │ diode
          ├─────────╲│
          │
          ├── SWITCH
   GND ───┴─────────────
```

Switch open → current continues around the loop through the diode, decaying gradually as it
dumps energy into the coil's resistance. No spike. This is called **freewheeling**, and it's
the reason your original design document mentioned letting the coil "coast down."

Still only one direction, though.

## 4.3 Building the H-bridge

Four switches, coil in the middle. It looks like the letter H:

```
        +60V
    ┌────┴────┐
   [Q1]      [Q3]        ← high side
    │         │
    ├──[COIL]─┤          ← the coil bridges the two switch nodes
    │    A  B │
   [Q2]      [Q4]        ← low side
    └────┬────┘
        GND
```

Now:

| Switches on | Coil sees | Current |
|---|---|---|
| **Q1 + Q4** | A at +60 V, B at 0 V | flows **A → B** |
| **Q3 + Q2** | A at 0 V, B at +60 V | flows **B → A** |
| **Q2 + Q4** (both low) | both ends at 0 V | freewheels, decays slowly |
| **Q1 + Q3** (both high) | both ends at +60 V | freewheels, decays slowly |
| all off | — | **forbidden** — see §4.5 |

**Both directions. Plus a freewheel path. This is why your design uses an H-bridge**, and now
you can derive it rather than accept it.

> ⚠️ **Q1 and Q2 must never be on together.** That would be a direct short from +60 V to
> ground through two transistors, limited only by their resistance — hundreds of amps in
> microseconds. This is called **shoot-through** and it destroys the FETs. Same for Q3/Q4.

## 4.4 Decay modes — the thing everyone gets wrong

You have two ways to reduce current, and they behave *completely* differently.

**Slow decay ("coast")** — turn on both low-side switches. The coil sees 0 V across it and its
current dies away through its own resistance:

    di/dt = −I·R / L

**Notice that this depends on I.** As current gets small, the decay gets slow. At 1 A in your
coil: **0.4 A/ms**. Painfully slow.

**Fast decay ("brake")** — turn on the *opposite* diagonal, applying −60 V across the coil to
actively push the current down:

    di/dt = −(V + I·R) / L

At 1 A: **12.4 A/ms**. Thirty times faster.

### Why this matters to you specifically

Your system normally sits **under 1 A** (§1.3, the PM carries the load). Compare at that
operating point:

| At 1 A | Raise current | Lower current |
|---|---|---|
| Slow decay only | +11.6 A/ms | **−0.4 A/ms** |
| Fast decay available | +11.6 A/ms | −12.4 A/ms |

**A 29:1 asymmetry.** A controller driving a plant that responds 29× faster in one direction
than the other either gets detuned down to the slow direction — throwing away most of its
bandwidth — or overshoots constantly.

> **So you need the ability to apply negative voltage across the coil, separately from the
> question of whether current ever reverses.** These are two different requirements, and
> conflating them is the most common mistake in inductive-load drive design.

The H-bridge gives you both.

## 4.5 Deadtime

Switching from "Q1+Q4 on" to "Q2+Q4 on" means turning Q1 off and Q2 on. Real transistors take
time — roughly 100–200 ns for yours. If Q2 starts turning on before Q1 has finished turning
off, both are partly on: **shoot-through**.

The fix is **deadtime** — a deliberate gap where *neither* is on. During that gap the coil
current flows through the body diode of the FET that's about to turn on, so the current still
has its path.

Your IR2184 enforces this in hardware: **280–520 ns** of deadtime, and an interlock that
physically cannot turn both outputs on at once. That's a large part of why it's a good choice
— it makes the most dangerous failure mode impossible by construction rather than by
firmware discipline.

---

# PART 5 — Driving the switches

## 5.1 MOSFETs

Your switches are **MOSFETs** — voltage-controlled. Put voltage on the **gate** relative to
the **source** and current flows from **drain** to source.

Your part, **IRF100B201**:

- **100 V** rating — must exceed your 60 V bus, with margin
- **4.2 mΩ** on-resistance — at 30 A that's `30² × 0.0042 = 3.8 W` of heat
- Needs about **10–12 V** gate-to-source to turn fully on

⚠️ **On-resistance rises with temperature.** At 125 °C it's roughly **6.7 mΩ**, not 4.2. So
real dissipation is `30² × 0.0067 = 6.0 W`. **Always compute losses hot.** A design that only
works at 25 °C doesn't work.

## 5.2 Why a microcontroller pin cannot drive a MOSFET

The gate looks like a **capacitor** — about 9500 pF on yours. To switch, you have to charge
and discharge it. The datasheet expresses this as **gate charge, Q_g = 170–255 nC**.

To switch in 100 ns you need:

    I = Q / t = 255 nC / 100 ns = **2.5 amps**

A microcontroller pin sources maybe 20 mA. It would take **12 microseconds** — during which
the FET is half-on, in its linear region, dissipating enormous power. It would die.

So you need a **gate driver**: a chip that takes a logic signal and delivers amps of gate
current. Your IR2184 sources 1.4 A and sinks 1.8 A.

## 5.3 The high-side problem — the genuinely subtle part

The low-side FET (Q2) is easy. Its source is at ground. Put 12 V on the gate, done.

The high-side FET (Q1) is a different animal. Its **source is the switch node** — the point
that connects to the coil. When Q1 turns on, that node rises to 60 V.

To keep Q1 on, you need gate 10 V *above its source*. Source is at 60 V. So you need:

    V_gate = 60 + 10 = **70 volts**

**You don't have 70 volts. Your supply is 60.**

This is a real, fundamental problem with N-channel high-side switches, and everyone hits it.

## 5.4 The bootstrap — the trick that solves it

```
      +12V
        │
        ▼ D_boot
        │
        ├──────────────┐  ← VB (high-side supply, floating)
        │              │
     C_boot         [driver]
        │              │
        └──────────────┴──── VS ── switch node
```

A capacitor (`C_boot`) sits between the driver's floating supply pin (VB) and the switch node
(VS). Here's the sequence:

**Step 1 — low-side on.** Q2 is on, so the switch node is at **0 V**. Current flows from the
12 V rail through `D_boot` into `C_boot`, charging it to ~11.3 V. The capacitor now holds
11.3 V between its two plates.

**Step 2 — high-side turns on.** The switch node rises to **60 V**. The capacitor's bottom
plate is tied to that node, so it rides up with it. But a capacitor holds its *voltage
difference* — so its top plate is now at **60 + 11.3 = 71.3 V**.

**You just made 71 volts out of a 12 V supply.** The driver uses that floating 11.3 V to hold
Q1's gate above its own source. The diode blocks the 71 V from feeding back into the 12 V
rail.

This is genuinely clever, and it's why almost every half-bridge driver works this way.

## 5.5 The catch — and why "50% duty" mattered so much

Look again at Step 1. **The bootstrap capacitor only recharges while the low side is on.**

If you ran 100% duty — high side permanently on — the switch node never returns to ground,
`C_boot` never recharges, and it slowly drains through the driver's own quiescent current.
Eventually it drops below the driver's **undervoltage lockout** (8.0–9.8 V on yours) and the
driver **shuts the high side off**. Your bridge dies mid-operation.

> **This is why I spent a whole morning worried about whether you were running at 100% duty.**
> When I thought the coil was 2 Ω/yoke, 30 A needed the full 60 V — 100% duty — and the
> bootstrap would have failed. When the EDD showed 1 Ω/yoke, 30 A needs only 30 V — **50%
> duty** — and the capacitor recharges every single cycle with enormous margin.

Sizing it is a balance:

- **Big enough** that it doesn't droop much during the on-time. Yours: `405 nC / 1 µF =
  0.41 V` of droop, against a 1.5 V budget. Comfortable.
- **Small enough** that it fully recharges during the off-time. With `R_boot = 1 Ω` and 1 µF,
  recharge takes ~4 µs, so you'd be fine up to **94% duty**.

You're operating at 50%. Enormous margin either way.

## 5.5b What an IR2184 actually is

It's a **half-bridge gate driver**. One chip drives **one leg** — one top FET and one bottom
FET. Your H-bridge has two legs, so it needs **two IR2184s per channel**, four per board.

("IR" = International Rectifier, the company that invented this class of part. Infineon
bought them. The IR2181/2183/2184 are the same family with different shutdown and deadtime
options.)

### The one-sentence version

**It takes one logic-level wire from your microcontroller and turns it into two properly
driven MOSFET gates — including the impossible-looking floating one — and it makes the
dangerous state physically unreachable.**

### Six jobs, all in one 8-pin chip

1. **Amplifies.** Logic in (a few mA), 1.4 A / 1.8 A of gate current out. §5.2.
2. **Solves the high-side problem.** Provides the floating VB/VS supply the bootstrap
   capacitor charges. §5.3–5.4.
3. **Makes two signals from one.** Input high → top FET on. Input low → bottom FET on.
4. **Inserts deadtime.** 280–520 ns where neither is on, so they never overlap. §4.5.
5. **Interlocks.** Physically cannot turn both outputs on at once, whatever the input does.
6. **Undervoltage lockout.** If its supply sags below ~9 V it shuts off rather than
   half-driving the FETs into their linear region and cooking them.

### The pins, and the two "worlds" inside the chip

```
   ┌──────────────────┐
   │      IR2184      │
   │                  │        ── ground-referenced world ──
   │  VCC ────────────┼───  +12 V supply
   │  COM ────────────┼───  ground (its 0 V reference)
   │  IN  ────────────┼───  your PWM signal
   │  SD  ────────────┼───  shutdown
   │  LO  ────────────┼───  bottom FET's gate
   │                  │
   │                  │        ── floating world ──
   │  VB  ────────────┼───  floating supply +   (bootstrap cap top)
   │  VS  ────────────┼───  floating supply 0 V (the SWITCH NODE)
   │  HO  ────────────┼───  top FET's gate
   └──────────────────┘
```

**This is the important idea.** The chip has two halves that live at different voltages:

- **The bottom half** is referenced to ground. Ordinary.
- **The top half floats.** `VS` connects to the switch node, so the whole high-side section
  rides up and down between 0 V and 60 V, 32,000 times a second, dragged along by its own
  output. `HO` is measured *relative to VS*, so it's always the right ~11 V above the top
  FET's source — no matter where that source happens to be at that instant.

That floating section is the entire reason this chip exists. The bootstrap capacitor is its
battery, and the diode is what stops the 71 V from leaking back into your 12 V rail.

### What one input does

| `IN` | Top FET | Bottom FET | Leg output sits at |
|---|---|---|---|
| high | **ON** | off | **+60 V** |
| low | off | **ON** | **0 V** |
| *(transition)* | off | off | deadtime, ~400 ns |

So one wire decides **which rail this leg's output is connected to.** PWM that wire and the
output becomes a square wave between 0 V and 60 V, whose *average* is `duty × 60 V`.

> **That's why 2 legs = 2 wires.** Each wire sets one end of the coil. The coil sees the
> difference. Direction comes free.

## 5.6 Gate resistors

Between driver and gate you put a resistor — typically 10 Ω. Why deliberately slow it down?

**Fast switching** = less switching loss, but violent `dv/dt` and `di/dt`, which rings against
parasitic inductance and radiates EMI. It can also couple through a FET's own capacitance and
falsely turn on the opposite FET.

**Slow switching** = quieter, but more energy burned per transition.

10 Ω gives ~64 ns transitions — a reasonable middle. Often you use a *lower* resistance for
turn-off than turn-on (yours: 10 Ω on, 4.7 Ω off, with a diode to bypass): turning off fast is
safer, because a FET that's off can't shoot through.

---

# PART 6 — Measuring the current

## 6.1 Why bother

Two reasons.

**Protection.** If something shorts, you need to know within microseconds.

**Control.** Right now the controller sends a duty cycle and *hopes* the current is right. But
current depends on coil resistance, which changes with temperature — a hot coil has ~31% more
resistance, so the same duty gives ~24% less current. Without measurement the controller is
working with a plant that quietly changes underneath it.

With current feedback you can close an **inner loop** — "I asked for 15 A, I measure 12 A,
push harder" — which makes the current track the request regardless of temperature, *and* lets
you use the voltage headroom to force current to change faster than the natural L/R time
constant would allow. Given that §1.2's instability is only about 3× slower than your current
loop, that speed-up may be necessary rather than nice.

## 6.2 How

A **shunt** — a very small, very precise resistor in the current path. **1 mΩ** in your case.
Ohm's law does the rest: 30 A → 30 mV.

Small on purpose: at 30 A it only wastes `30² × 0.001 = 0.9 W`. But 30 mV is a *tiny* signal
to extract from a board slamming 60 V around at 32 kHz, which is where the difficulty lives.

## 6.3 Where to put it — three options

**Low-side** (between bridge and ground): easy, ground-referenced, cheap. But it can't see
current during every part of the switching cycle, and it **can't detect a shorted load**.

**High-side** (between battery and bridge): sees total current, catches shorts. But the
amplifier inputs sit at 60 V.

**In-line** (in series with the coil itself): sees the **true coil current, in both
directions, at all times**. This is what you want — you need bidirectional measurement, and
this is the only placement that gives it honestly.

The cost: the shunt is attached to the switch node, so **both amplifier inputs swing from 0 V
to 60 V and back, 32,000 times a second**, while you try to read 30 mV across them.

## 6.4 Why the INA240 specifically

Ordinary difference amplifiers fail badly here. When both inputs jump 60 V simultaneously
(**common-mode**), imperfect internal matching turns some of that jump into apparent signal —
producing huge spikes on the output at every switching edge. Against a 30 mV signal, that's
fatal, and it causes false overcurrent trips.

The **INA240** is built specifically for this. Its enhanced PWM rejection gives **132 dB** of
common-mode rejection at DC and still **93 dB at 50 kHz**. That is the entire reason the part
exists, and it's the correct choice for in-line sensing on a switching bridge.

Configuration: gain 20, so 30 A → 600 mV. Because current is bidirectional you offset the
output to mid-rail (**1.65 V**), so positive current reads above 1.65 V and negative below.
Full scale ±82 A — plenty of headroom for fault detection.

**Kelvin connection**: take the measurement from separate sense terminals right at the shunt
element, not from the fat current-carrying copper. Otherwise you measure the resistance of
your own PCB trace along with the shunt.

---

# PART 7 — Protection

## 7.1 Shoot-through
Handled in hardware by the IR2184's interlock and deadtime (§4.5). Nothing further to do.

## 7.2 Over-current

Something shorts, or the controller commands nonsense. Detect and shut down **without waiting
for software**.

A **comparator** watches the INA240 output. Above ~45 A (either direction — so two
comparators, forming a window), shut the bridge off.

**Two subtleties:**

**It must latch.** Turn the bridge off and the current falls, so the fault clears, so it turns
back on, so the fault returns — chattering into a short thousands of times a second until
something burns. A **latch** holds the fault until deliberately reset. *The previous design's
BOM had a bare comparator and no latch. That's a real defect and we're fixing it.*

**The comparator can be slow, and that's fine here.** An LM393 takes ~1.3 µs to respond, which
sounds dangerous. But your load is 9.25 mH, so the fastest possible di/dt is 9730 A/s — in
1.3 µs the current rises **12.6 mA**. The inductance protects you. The genuinely fast fault is
shoot-through, and §4.5 already handled that in hardware.

*Notice the shape of that argument: a spec that looks alarming in isolation is fine once you
check it against the actual physics. That's the difference between selecting parts and
designing.*

## 7.3 The energy problem — where does 4 joules go?

The coil stores energy in its magnetic field:

    E = ½ · L · I² = ½ × 0.00925 × 30² = **4.16 joules**

That energy is real and it must go *somewhere*. Normally, when you reduce current, it flows
back into the battery, which absorbs it happily.

**But what if the battery isn't there?** A fuse opens, a connector bounces, the contactor
trips — at 30 A, mid-flight.

Now 4.16 J has nowhere to go but the bus capacitors. Energy into a capacitor is `½CV²`, so:

    V = √(2E/C) = √(2 × 4.16 / 470 µF) ≈ **146 volts**

Against 100 V FETs and 100 V capacitors. Everything on the bus dies.

And you can't fix this with capacitance — even 1000 µF only gets you down to 109 V. You'd
need thousands of microfarads.

## 7.4 The fix — and this one's satisfying

Don't send the energy to the bus at all. **Turn both low-side FETs on.**

The current circulates in a closed loop — `coil → Q2 → Q4 → coil` — and dies in the coil's own
1 Ω of resistance:

    τ = L / (R + 2·R_ds) = 9.25 mH / 1.01 Ω ≈ 9.1 ms   →   fully decayed in ~46 ms

**All 4.16 J turns into a trivial amount of heat in the coil. The bus never sees it.**

Cost: a comparator watching the bus, and a 220 µF hold-up capacitor on the 12 V gate-drive
rail so the FETs can still be *driven* for those 46 ms after the bus is gone.

This is why the design has a bus-voltage detector whose action is "turn switches **on**"
rather than the intuitive "turn everything **off**." With inductive loads, turning everything
off is often the most dangerous thing you can do.

## 7.5 Fuse and TVS

**Fuse** — last-resort protection against a catastrophic short. Critically, it must be rated
for **60 V DC**. DC is much harder to interrupt than AC: AC crosses zero 120 times a second
and the arc self-extinguishes, while DC arcs just keep burning. *Most automotive fuses are
rated 32 V DC — using one here means it may not actually clear the fault. This is a real
problem in the original design.*

**TVS diode** — clamps transient spikes. Non-conducting below its threshold (~70 V), conducts
hard above it. Catches whatever §7.4 doesn't.

---

# PART 8 — How every design decision maps back

| Decision | Traces back to |
|---|---|
| **Full H-bridge** | §1.4 — PM bias means force depends on current *sign* |
| **Two independent PWM inputs** | §4.4 — lets firmware pick any decay strategy, so we don't need to know the modulation scheme in advance |
| **IRF100B201, 100 V** | §5.1 — 60 V bus needs headroom for switching overshoot |
| **Losses computed at 125 °C** | §5.1 — R_ds(on) rises ~60% hot |
| **IR2184 gate driver** | §5.2 amps of gate current; §4.5 hardware shoot-through interlock |
| **C_boot = 1 µF, R_boot = 1 Ω** | §5.4–5.5 — droop small enough, recharge fast enough |
| **50% duty is safe** | §5.5 — bootstrap recharges every cycle. This is why the coil resistance question mattered so much |
| **10 Ω / 4.7 Ω gate resistors** | §5.6 — EMI vs. switching loss, asymmetric because off-fast is safe |
| **1 mΩ shunt, in-line** | §6.3 — only placement that sees true bidirectional coil current |
| **INA240** | §6.4 — the only affordable way to read 30 mV riding on a 60 V square wave |
| **Latched OCP** | §7.2 — unlatched protection chatters into the fault |
| **LM393 is fast enough** | §7.2 — 9.25 mH limits di/dt to 12.6 mA in 1.3 µs |
| **Bus fault → both low FETs on** | §7.4 — keeps 4.16 J in the coil instead of on the bus |
| **220 µF on the 12 V rail** | §7.4 — FETs must stay driven for 46 ms after the bus dies |
| **60 V-rated fuse** | §7.5 — DC arcs don't self-extinguish |
| **Measure L and R** | §2.3 — τ sets everything, and §1.2 says everything must beat 32 ms |

---

# PART 9 — The one-paragraph version

The pod hangs from a steel rail by magnetic attraction, which is inherently unstable — closer
means stronger means closer still — so something must actively correct it faster than the
~32 ms runaway. Permanent magnets carry the static weight so the coils idle near zero current;
the coils only trim the field, and because they trim a *biased* field they must be able to
push current **both ways**. Regulating 30 A linearly would waste hundreds of watts, so you
switch instead, and the coil's own 9 ms time constant smooths 32 kHz pulses into clean DC. Four
transistors in an H-bridge give both directions plus the ability to actively force current
*down*, which matters because the passive decay path is 29× too slow at the sub-1 A currents
this system actually runs at. Driving the two high-side transistors needs a voltage above the
supply, which a bootstrap capacitor manufactures by riding up with the switch node — and which
is why running at 50% duty rather than 100% is structurally important. A 1 mΩ shunt and a
purpose-built amplifier read the current out of a 60 V square wave for protection and for an
inner control loop. And because the coil holds 4 joules that must go somewhere, a bus fault
commands the bridge to short the coil to itself rather than switch off, keeping that energy
where it can do no harm.
