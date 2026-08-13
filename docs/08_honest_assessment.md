# How Much Can Actually Be Designed Right Now — An Honest Assessment

Levitation coil drive stage · Sebastian · 2026-08-11

---

## The short version

About **two-thirds of the schematic can be drawn and defended today**. About **a sixth can
be drawn conservatively** and may be oversized. About **a quarter cannot be drawn at all**.

But the percentage is not the interesting part. The interesting part is that proceeding has
a specific failure mode that this project is *specifically* trying to escape, and it is worth
being explicit about it before deciding.

---

## The trap

You are rebuilding this board because the last one **passed every check and you still didn't
trust it**. ERC clean, DRC clean, 45/45 wiring audit, LTspice results all correct.

The reason those checks didn't earn trust is that they verified the design against **its own
assumptions**. A design that is internally consistent and externally wrong passes every check
you can run on it.

If I design a power stage against an assumed 10 mH, and then you simulate it in LTspice
against that same assumed 10 mH, the simulation will pass. It will pass beautifully. And it
will tell you nothing about whether the board works, because the simulation and the design
share the same unverified input.

**That is exactly the failure mode of the previous revision, reproduced in a new file.**

This does not mean don't proceed. It means the difference between good and bad progress here
is entirely about whether assumptions are *labelled*. Work built on a flagged assumption you
can revisit is real progress. Work built on an assumption you've forgotten you made is the
last design again.

---

## What can be finalised now — genuinely settled inputs

These follow from numbers the EDD states directly: 60 V max bus, 30 A/yoke peak,
16–32 kHz PWM, bidirectional current.

| Block | Confidence | Note |
|---|---|---|
| **MOSFET selection** | High | 60 V bus and 30 A are firm. The IRF100B201 has enough margin that the part choice survives any plausible answer. |
| **Conduction loss budget** | High | I²R with a temperature-corrected R_DS(on). No dependency on anything blocked. |
| **Shunt selection + INA240 config** | High | 30 A full scale is firm. Gain option, Kelvin layout, reference scheme all follow. |
| **Shunt placement decision** | High | Bidirectional current is confirmed, which mostly settles this toward in-line. TI SBOA174 Table 2. |
| **OCP threshold + latch** | High | 30 A legitimate, 60 A ceiling → ~45 A is defensible. The latch is missing from the old BOM and its design is independent. |
| **Fuse and TVS voltage class** | High | 60 V bus is firm, and the 32 V DC rating problem is already identified. |

That is real, permanent work. None of it gets thrown away.

---

## What can be drawn conservatively — and what that costs

| Block | Depends on | Conservative approach | Cost of being wrong |
|---|---|---|---|
| **Switching loss + heatsink** | Blocker 1 (Q1) | Size for locked-antiphase, where all four FETs switch continuously instead of two | A larger heatsink than needed. Cheap insurance. |
| **Bus capacitance + TVS energy** | Blocker 2 (L) | Size for the high end, L ≈ 13 mH → 5.4 J | Possibly 3–4× the capacitance needed. On a 316 kg pod this is grams. Acceptable. |
| **Gate resistor** | EMI/switching trade | Pick a range, tune on the bench | Normal practice anyway. |

**These are legitimately fine to design conservatively.** Over-sizing a heatsink and a
capacitor bank on a prototype is a good trade against waiting. Just record *why* the value
is what it is, so it can be reduced later rather than becoming folklore.

---

## What genuinely cannot be drawn

| Block | Why |
|---|---|
| **Control input stage** | PWM+DIR, two PWMs, and antiphase need three *different* logic structures feeding the gate drivers. Not a component choice — the shape of the circuit. |
| **Connector footprints** | 10 AWG will not fit a 12 AWG-max part. Dimensional, not a derating judgement. |
| **Board partitioning and layout** | Needs the two-yoke-flight answer and the physical yoke locations. |
| **Aux rail design** | Nobody has said whether the pod supplies 12 V and 3.3 V or whether this board generates them. Small, but it's an unknown nobody has stated. |

---

## The one thing that would change this materially

**Blocker 2 does not have to wait on the lev team.**

The measurement is three LCR readings and a four-wire resistance. If you have access to a
yoke and a meter — or can borrow one — **you can unblock it yourself this afternoon**, and it
is by a wide margin the highest-leverage hour available:

1. LCR at 1 kHz, one coil, other coil **open** → L
2. LCR at 1 kHz, one coil, other coil **shorted** → L(1−k²), so together these give k
3. Four-wire DC resistance, one coil → settles 2 Ω vs 4 Ω
4. Repeat on the full yoke as wired

That single measurement converts the bus capacitance, the TVS, the current-loop analysis and
**every LTspice simulation you plan to run** from assumption to fact.

**Do you have access to a yoke and an LCR meter?** If yes, that is the next thing to do,
ahead of any schematic work.

---

## Recommendation

**Proceed, but only on the work that is insensitive to the blockers**, and label every
assumption in the schematic itself rather than in your head:

1. MOSFET selection and the full loss budget *(assume antiphase for switching loss)*
2. Heatsink and thermal budget — follows from 1
3. Gate driver selection and bootstrap sizing
4. Shunt placement decision, then shunt + INA240 configuration
5. OCP threshold and latch

Steps 1–3 chain together; 4–5 are independent. That is one to two days of work that survives
any answer that comes back.

**Do not** start the control input stage, the connectors, or any layout. Those aren't
"probably fine" — they're genuinely undetermined, and starting them is how you end up
defending a decision you made because you were tired of waiting.

**And do not run a validation simulation against assumed L and call it verified.** Simulate
to *explore* — sweep L across 5–13 mH and see what actually changes, which is useful and
honest. Simulating to *confirm* against a number nobody measured is the previous design's
mistake wearing a different hat.
