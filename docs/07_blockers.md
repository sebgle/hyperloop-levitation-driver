# What Actually Blocks Starting the Design

Levitation coil drive stage · Sebastian · 2026-08-11

There are ~24 open questions across the documents. Most of them are not blockers. This
separates the four that are.

---

## The test applied

For each open question: *if I never get an answer, what specifically can I not draw?*

- Changes the **schematic topology** → blocks starting
- Changes only a **component value** → design with a documented assumption, revisit later
- Changes the **PCB layout** → blocks layout, not schematic
- Changes **firmware or another team's work** → not a blocker for this board at all

---

## BLOCKER 1 — The control interface spec

**Blocks: schematic topology. Nothing meaningful can be drawn without it.**

This is the one I dropped when I shortened the message to the lev team, and it is the most
blocking item on the list. My mistake — it was Q8 in the original long version and it got
cut in compression.

What's needed:

- **How many signals per yoke, and what are they?** PWM + DIR? Two independent PWMs? A
  single antiphase PWM? Each needs *different gate-drive logic* — this is not a component
  choice, it is the structure of the schematic.
- **Logic level** — 3.3 V or 5 V. Sets the level-shift and input protection.
- **What does the board send back?** Analog current out, fault flag, temperature, nothing?
  Determines whether there's a fault latch, how many connector pins, and whether the
  current-sense output needs buffering and scaling to an ADC range.
- **Is there an enable / shutdown line**, and should the OCP fault latch until reset or
  auto-retry?

### A specific ambiguity worth resolving first

The EDD says *"Control is managed via PWM with a 50 % duty cycle limit."* In a
**bidirectional** system that sentence has two incompatible readings:

| Reading | What 50 % means | Gate logic |
|---|---|---|
| **Sign-magnitude PWM** | Duty runs 0–100 % with a separate direction bit; the 50 % cap limits current to 30 A | One leg switches, the other holds static; DIR selects which |
| **Locked-antiphase PWM** | 50 % duty **is zero current**; 0 % is full negative, 100 % is full positive | Both legs switch complementarily, always |

The EDD's own arithmetic (50 % × 60 V = 30 V → 30 A into 1 Ω) points to **sign-magnitude**.
But locked-antiphase is common enough on brushed-DC motor drivers — which is what they're
using today — that this must be confirmed rather than inferred. The two produce opposite
gate-drive designs, and locked-antiphase also has much higher ripple current and continuous
switching loss even at zero output.

---

## BLOCKER 2 — Coil inductance L, and the coupling k

**Blocks: every component value, and all simulation.**

Not stated anywhere — not in the EDD, not in the slide, not in the chat. The chat's
"10 mH" was a recollection from someone who also said they didn't remember.

What it blocks:

- **Bus capacitance and TVS sizing.** At 30 A the stored energy is 2.1 J, 4.2 J or 5.4 J
  depending on L — a 2.6× spread. The resulting bus peak with the battery absent is 112 V,
  146 V or 163 V against 100 V parts. You cannot pick a capacitor or a TVS from that range.
- **Current-loop design and the current-sense filter bandwidth.**
- **Any LTspice simulation at all.** You are drawing in LTspice specifically so you can
  validate before laying out. Without L you have nothing to validate against.

The measurement, precisely:

1. LCR at 1 kHz on one coil, **other coil open** → gives L
2. LCR at 1 kHz on one coil, **other coil shorted** → gives L(1−k²), so the pair gives k
3. Four-wire DC resistance on one coil → confirms 2 Ω vs 4 Ω
4. Same three readings on the **full yoke as actually wired**

Ten minutes with an LCR meter. Nothing else in the project has this ratio of effort to
unblocking.

---

## BLOCKER 3 — The connector

**Blocks: PCB layout, and it has procurement lead time.**

The EDD specifies **10 AWG** to the yokes. The Molex 0389220002 accepts **AWG 12–26** and is
rated **20 A** against 30 A required. The wire does not physically fit.

You cannot place a footprint until this resolves, and if the answer is "use a different
part" you need to select and source one — which is why this should go to your lead **today**
rather than after the lev team replies. It is on a different person and a different clock.

---

## BLOCKER 4 — One board or two

**Blocks: PCB layout only. Does not block the schematic.**

The two boards are identical, so a 2-channel schematic is a subset of a 4-channel one — you
can draw the channel first and decide the count later.

Needs: can the pod fly on two yokes (is modular fault tolerance real?), and where the yokes
physically sit relative to the electronics. Both are lev-team questions.

---

## Not blockers — design against an assumption and move

| Question | Why it doesn't block | What to assume meanwhile |
|---|---|---|
| Q3 — how long at peak current | Affects firmware foldback, not the board | Design the hardware to survive continuous peak |
| Q22 — is 30 A real or inherited from the old drivers? | 30 A is a safe upper bound either way | Design to 30 A/yoke |
| Q20 — control-loop bandwidth needed | Affects the sense filter corner only | Set the filter well above the plant, revisit |
| Q21 — gap sensor spec | Not on this board | — |
| Q7/Q8 — pod geometry | Folded into Blocker 4 | — |
| Q24 — is the EDD current? | Worth asking, but it's the best source available | Treat as current |
| Coil R (2 Ω vs 4 Ω) | Independent calculation strongly favours 2 Ω | Use 1 Ω/yoke, confirm in Blocker 2's measurement |

---

## What can start immediately, with zero further answers

Roughly 60 % of the schematic does not depend on any of the four blockers, because bus
voltage (60 V), peak current (30 A/yoke), and switching frequency (16–32 kHz) are all known:

1. **MOSFET selection and the full loss budget** — conduction, switching, gate charge.
   Independent of everything blocked. onsemi AND9083 Eq. 7 for the inductive-load switching
   term.
2. **Heatsink and thermal budget** — follows directly from (1). onsemi AND8220.
3. **Gate driver selection and bootstrap sizing** — Qg comes from (1), duty range is known
   to be ≤50 %, frequency is known. Infineon AN-1123 §2.2.
4. **Shunt selection and INA240 configuration** — 30 A full scale is known; gain option,
   Kelvin layout and the reference scheme all follow.
5. **Shunt placement decision** — in-line vs low-side vs high-side. TI SBOA174 Table 2.
   This is a real decision with consequences and it should be made deliberately, not
   inherited.
6. **OCP threshold and latch design** — 30 A legitimate, 60 A ceiling, so ~45 A is
   defensible. The LM393 in the old BOM has no latch; that needs designing.

**Recommended order:** 1 → 2 → 3 in one pass (they chain), then 5 → 4 → 6.

That is a full day of real work that nothing is waiting on, and it produces the numbers
you'll need to sanity-check whatever the lev team sends back.
