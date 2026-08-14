# Levitation Coil Drive Stage — Engineering Design Log

**Engineer:** Sebastian
**Project:** Hyperloop pod levitation power/drive electronics
**Started:** 2026-08-11
**Approach:** Manual design. Schematic drawn in LTspice, PCB in KiCad. Every parameter
sourced or measured; nothing assumed.

---

## Why this log exists

A prior revision of this board was produced with AI-assisted placement and auto-routing.
It passed ERC, DRC and a net-by-net audit. It was still rejected — not because a check
failed, but because passing checks is not the same as understanding a design, and a board
you cannot defend is a board you cannot bring up on the bench.

This rebuild is deliberately slower. This log records what was decided, what was rejected,
and why — including the things that turned out to be wrong.

---

## Index of documents

| # | Document | Status |
|---|---|---|
| 00 | Design log (this file) | living |
| — | Open questions & first-pass review | **issued 2026-08-11, awaiting answers** |
| 01 | Reference library — verified datasheets, app notes, reference designs | rev 0 |
| 02 | Drive topology derivation | rev 0 — conditional on Q4 |
| 04 | Board partitioning — one board or two, and is a PDU needed | rev 0 — conditional on Q1, Q17 |
| 06 | HEMS slide + LEV EDD findings — **includes retractions of three Day-1 findings** | rev 1 |

---

## 2026-08-11 · Day 1

### Inputs received
- `Levitation_Power_System_Overview.pdf` — prior design overview, 2 control boards + PDU
- `more_constraints.txt` — transcript of the requirements conversation with the lev team
- Verbal constraint from lead: Molex 0389220002 barrier strips for external connections

### What I did
Read both documents, extracted every stated parameter into a table with a provenance
column, and ran a first-pass operating-point calculation before accepting any of the
prior design's conclusions.

### Findings — the design is structurally sound but rests on unverified numbers

**Confirmed correct in the prior design.** Not everything needed changing:
- INA240 for current sense — its enhanced PWM common-mode rejection is exactly the right
  tool for in-line shunt measurement on a switching bridge leg, and its offset is low
  enough that 1 mΩ still resolves the sub-1 A baseline.
- Ripple analysis — 188 mA pk-pk at 16 kHz / D = 0.5, i.e. 0.6 % of 30 A. The prior
  document's 0.6 % figure checks out independently.
- Diagonal yoke pairing (FL+RR / FR+RL) — the failure-mode reasoning is sound.
- Freewheel rather than active reversal for current decay — correct, and it is what keeps
  the bus overvoltage problem (below) from being worse than it is.
- Centralising pack protection in a separate PDU — right call.

**Structural finding: 30 A/yoke is exactly 100 % duty cycle, not a peak.**
`I_max = V/R = 60 V / 2 Ω = 30.0 A`. τ = L/R = 2.5 ms is ~40 PWM periods, so the load is
resistance-dominated and the inductance never lets current exceed V/R. There is no
transient headroom above 30 A. Two consequences the prior design did not account for:
- The specified 45 A over-current trip **can never fire in normal operation**. It is a
  fault detector only, and must not be mistaken for coil thermal protection.
- 100 % duty is **incompatible with a bootstrap high-side gate supply**. The bootstrap
  capacitor only recharges while the low side conducts. Practical ceiling is ~95–98 %
  duty, i.e. ~28.5–29.4 A. Quantified in Infineon AN-1123 §2.2.

**Blocking conflict: the peak current target differs by 2× between the two source documents.**
Lev team said "minimum is like 60 A total across 4 yokes" (15 A/yoke). The overview
document specifies 30 A/yoke, 120 A total. This one number sets the connector, the wire
gauge, the PDU copper, the heatsink, the FET count and whether the gate drive works at
all. Design cannot proceed past block diagram until it is fixed.

**Largest unanswered risk: coil thermal survival.**
At 30 A/yoke the coil dissipates `I²R = 1800 W` per yoke — 7.2 kW across the pod. At
15 A/yoke it is 450 W / 1.8 kW. The overview document calls this a "brief peak during
disturbances" but nothing in the hardware bounds the duration. Nobody has stated how long
a coil survives at peak. Issued to the lev team as Q3.

**Coil energy dump can exceed the 100 V device ratings.**
At 30 A a yoke stores `½LI² = 2.25 J`. Dumped into the 470 µF bus cap alone (battery
disconnected, fuse open, connector bounce) the bus reaches 115 V — above both the
IRF100B201 and the bus caps. At 15 A it reaches 77 V, which is fine. So at the higher
current target the design's survival depends on the battery being connected, which makes
the battery connection safety-critical rather than merely functional. Needs an explicit
clamp/bleeder answer.

**The lead's connector is rated 20 A.**
Molex 0389220002 verified from the manufacturer: 20.0 A max per contact, 300 V, AWG 12–26.
Marginal at 15 A/yoke (75 % of rating), fails at 30 A/yoke, and nowhere near the 60–120 A
battery path. AWG 12 is also the largest wire it accepts. Raised with the lead as Q10 with
four resolution options rather than a flat objection.

**PDU copper needs computing, not assuming.** IPC-2221 first pass for 2 oz external:
60 A needs 18–28 mm width; **120 A needs 48–73 mm**. The PDU board is 120 × 80 mm, so at
120 A essentially the entire board must be uninterrupted bus copper — while the fuse
holder, TVS and connectors all interrupt it. Marginal at best.
*Later correction: this used IPC-2221, which is now known to model a conductor in free
air. To be re-derived against IPC-2152 data.*

**Also flagged:** XT60 at 60 A/board has zero margin (rated 60 A); a 125 A ANL fuse does
not open until ~200 A+ and so does not protect a 120 A load; and standard ANL/MIDI fuses
are commonly rated 32 V DC, which is invalid on a 60 V pack.

### Decision: re-derive the topology rather than inherit it
The prior design specifies a full H-bridge per yoke. Rather than validate it on its own
terms, derive the topology from the load and control requirements. If the H-bridge is
right it will fall out of the derivation and be defensible; if it is not, better to know
before layout. → document 02.

### Result of the derivation — a requirement nobody had written down

Force on an attractive electromagnet goes as B², so **current direction does not affect
force** for a pure electromagnet. Bidirectional current is only meaningful if the
suspension is permanent-magnet biased. The overview document asserts PM bias; the lev
team never confirmed it. Issued as Q4.

But the more interesting finding is that **negative voltage and negative current are
separate requirements**, and the prior design conflated them. Slow-decay di/dt is `−I·R/L`,
which goes to zero as current goes to zero — so a freewheel-only drive is *least* able to
reduce current exactly where this system normally operates:

| Operating point | Rise rate | Slow-decay rate | Asymmetry |
|---|---|---|---|
| 1 A (the ideal baseline) | +11.6 A/ms | −0.4 A/ms | **29 : 1** |
| 5 A (the stated baseline) | +10.0 A/ms | −2.0 A/ms | 5 : 1 |
| 15 A | +6.0 A/ms | −6.0 A/ms | 1 : 1 |

A PID loop driving a plant that responds 29× faster in one direction than the other will
either be detuned to the slow direction or will overshoot persistently. **So the drive
needs a −V capability regardless of whether the current ever reverses sign.**

That produces a clean decision rule instead of an assumption:

- **PM-biased (current must reverse)** → full H-bridge, 4 switches — as originally specified
- **Not PM-biased (current unidirectional, but still needs fast decay)** → **asymmetric
  half-bridge**, 2 switches + 2 diodes, giving the full +V / 0 / −V control set with half
  the switches and half the gate drivers

The original H-bridge is not *wrong* — it is a superset that works either way. But if the
suspension is not PM-biased it carries twice the switches, twice the drivers, twice the
conduction loss and twice the failure modes for a capability that is never used.

### Secondary finding: the natural current bandwidth may be too low
`f_c = 1/(2πτ) = 63.7 Hz`. For a levitation loop — open-loop unstable, and wanting a
current loop several times faster than the position loop — 64 Hz is not obviously enough.
This is the strongest argument for the current sensing the lev team was ambivalent about:
an inner current loop with voltage overdrive can push effective bandwidth well above the
natural 64 Hz, but only if the current is measured. Issued as Q3/Q9.

### Also raised with the controls team
Arduino PWM at 16 kHz on a 16 MHz AVR gives ~8–10 bit resolution. At 8 bit, one LSB =
60 V/256 → **117 mA of coil current**, leaving roughly 8 usable steps to hold a sub-1 A
baseline. This may be a control-resolution problem before it is a hardware problem.

### Reference library assembled
Verified first-party documents for every design block — gate drive, MOSFET loss and
thermal, current sensing, decay modes, bus protection, PCB copper. Aggregator sites
rejected. Four requested items could not be verified on a manufacturer domain and are
recorded as *not found* rather than substituted. Two published TI reference designs
(TIDA-00365 for voltage class, TIDA-00620 for current density) match closely enough to be
worth reading in full. → document 01.

### Open at end of Day 1
- **Blocking:** peak current target (Q1), measured L and R (Q2), coil thermal limit (Q3),
  bidirectional requirement (Q4), series-vs-parallel coils (Q5), max charged pack voltage (Q6)
- **Blocking:** connector resolution with lead (Q10)
- **Next once unblocked:** shunt placement decision from SBOA174; bootstrap sizing from
  AN-1123; FET loss and heatsink budget from AND9083 + AND8220; re-derive PDU copper
  against IPC-2152

---

## 2026-08-11 · Day 1, later — the overview document is downgraded from requirements to hypothesis

Confirmed with Sebastian that the "permanent-magnet biased suspension" claim in the
overview PDF was **likely AI-generated**, not stated by the lev team.

This is the most consequential finding so far, and not only for that one sentence. It
means the overview PDF is a **design output with rationale back-filled onto it** — its
"requirements" sections read like requirements but were partly reconstructed to justify
decisions already taken. The claim in question was the *entire* stated justification for
choosing a full H-bridge.

**Working rule from here:**
- `more_constraints.txt` is authoritative — it is a transcript of humans stating requirements.
- The overview PDF is a hypothesis. Every claim needs a source before it is designed against.

Claims now carrying UNVERIFIED flags: PM bias; "brief peaks up to 30 A"; "a lost diagonal
keeps remaining support roughly balanced"; the 45 A trip; 2 Ω / 5 mH per yoke.

Worth recording that this is *not* a reason to distrust the prior work wholesale — the
ripple analysis, the freewheel decay choice and the INA240 selection all held up under
independent check. It is a reason to source each claim before building on it.

### Board partitioning analysed → document 04

Established that **the board-count question and the PDU question are the same question**:
a PDU exists only to split the pack between multiple drive boards. One 4-channel board
needs no PDU.

Decisive factor is bus current, which is set by yoke current and channel count and is
independent of the topology choice: 4 channels at 15 A/yoke is 60 A (comfortable on a
PCB); 4 channels at 30 A/yoke is 120 A (a hard PCB problem). So board count is downstream
of Q1, plus pod geometry (new Q17).

Provisional recommendation: **two identical 2-channel boards** — but justified on bus
current, assembly risk and re-spin blast radius, **not** on the fault-tolerance argument
the overview PDF gave. That argument rests on the unverified premise that a pod is
controllable on two yokes at all; if it isn't, "which two yokes you lose" is irrelevant.
Issued as Q16 rather than inherited.

Noted a factor the prior design did not: four current measurements feeding one controller
share one clean analog ground on a single board, whereas across two boards the INA240
outputs are referenced to grounds carrying 30–60 A of switching current. At 1 mΩ, 1 A of
coil current is 1 mV — tens of millivolts of inter-board ground offset is not negligible.
Solvable via the INA240's REF pins, but it is design work the one-board option avoids.

### Recommendation: buy the PDU rather than build it

The PDU contains no switching and no control — it is a fuse, a TVS, a precharge resistor
and copper. Carrying 60–120 A on a PCB is among the harder problems in this project and a
solved commercial problem in 48 V marine/solar power distribution.

Verified that the **Victron MEGA-fuse is available in an 80 V DC variant covering
40–500 A**, which spans both candidate current targets with real headroom over a 60 V
pack. This also resolves the separate problem flagged earlier that standard ANL and MIDI
bolt-down fuses are commonly rated 32 V DC and are invalid on a 60 V bus.

Caveat carried forward: most commercial automotive/marine distribution blocks are rated
≤ 48 V DC. The voltage rating of every candidate part must be checked, and DC interrupting
capacity does not extrapolate upward from a lower-voltage variant — there is no zero
crossing to help extinguish a DC arc.

### New open questions
- **Q16** (lev/controls) — is the pod controllable on two yokes at all?
- **Q17** (lev/mech) — pod dimensions and physical yoke locations relative to the electronics
- **Q18** (Sebastian/lead) — is buying a commercial distribution block instead of
  fabricating a PDU acceptable? Right engineering call, but it removes a board from a
  project that may be assessed on what was built.

---

## 2026-08-11 · Day 1, evening — two real source documents surface, and I retract three findings

Sebastian produced a team slide ("Main Objective & Principle") and **LEV EDD 2026 1.pdf**.
These are proper team engineering documents and they supersede both the overview PDF and
much of the chat transcript. Full analysis in document 06.

### Q4 answered — and the "AI-generated" claim turns out to be correct

The system is **HEMS: Hybrid Electromagnetic Suspension** — permanent magnets providing
constant attractive force, coils actively regulating. The EDD's Fig. 3 plots force vs. gap
for **I = −16 A to +12 A**, which settles it: **current is bidirectional, the full H-bridge
is the right topology.** Document 02's decision rule resolves to the H-bridge branch.

Worth recording honestly: the PM-bias claim in the overview PDF — the one flagged this
morning as possibly AI-generated — is **correct**. It was unsourced, not wrong. That
distinction is exactly why the process was to verify rather than discard. The other flagged
claims remain unverified.

### The Q1 "conflict" was never a conflict

"60 A total" (chat) and "120 A total" (overview PDF) are both straight from the EDD table:
60 A is *Max Continuous Current*, 120 A is *Peak Current Capability*. Nobody was wrong and I
had spent the morning treating it as a blocking contradiction.

### The coil resistance conflict — settled by independent calculation

EDD says **2 Ω/coil**; the chat said 4 Ω. Rather than pick one, checked it against the
physical coil spec (250 turns of 18 AWG, yoke 228.6 × 76.2 × 127 mm). 18 AWG is 20.95 mΩ/m,
so 250 turns at a 300–400 mm mean turn gives **1.6–2.1 Ω cold**. The EDD is geometrically
consistent; 4 Ω would need a ~750 mm mean turn the envelope doesn't allow.

**Working value 2 Ω/coil → 1 Ω/yoke, still to be confirmed by measurement.**

### RETRACTIONS

Three of this morning's findings were built on the chat's 4 Ω figure and do not survive:

- ❌ **"30 A/yoke is exactly 100 % duty with no headroom."** With R_yoke = 1 Ω the ceiling is
  **60 A/yoke**; 30 A needs only 30 V, i.e. **50 % duty** — matching the EDD's stated 50 %
  limit. There is **30 V of headroom** at the peak operating point.
- ❌ **"100 % duty breaks the bootstrap high-side supply."** At 50 % duty the bootstrap
  recharges every cycle. Routine sizing, not a structural flaw.
- ❌ **"The 45 A over-current trip can never fire."** With a 60 A ceiling it is reachable and
  is real protection.

The design's operating point is materially better than the one I analysed this morning.
Recording this in full rather than quietly correcting it — the reason the chat numbers were
wrong is that they came from someone who prefaced them "I highkey don't remember," and the
lesson is that a remembered number and a documented number are not the same input.

### What survived

The connector conflict (worse — see below), the 120 A of PDU copper, the fast-decay
requirement, the fuse voltage-rating problem, and large coil dissipation (now 900 W/yoke,
3.6 kW total — half my earlier figure, still substantial).

### New: the 18 AWG thermal claim checks out

EDD §2.3 claims 18 AWG (rated 7 A continuous) safely absorbs 15 A peaks. 15 A in 0.823 mm²
is **18.2 A/mm²**, which looked optimistic, so I checked the transient rather than the
steady state. Copper mass ≈ 0.55–0.74 kg/coil → thermal mass 213–284 J/K; at 450 W/coil that
is **1.6–2.1 K/s, i.e. 47–63 s to +100 K**. **The claim holds if "brief" means seconds.**
Good reasoning on their part. Q3 narrows from an open unknown to "where between 1 s and 60 s."

### New: an error in EDD §2.2

The EDD justifies parallel coils by saying series would require **120 V**. That assumes 30 A
through the series pair, but force depends on MMF = N·I *per coil*, so series needs the same
15 A per coil — **60 V, not 120 V**. The conclusion (parallel) is still right, but for a
different reason: series at 60 V sits at 100 % duty with zero headroom, parallel at 30 V sits
at 50 % with 30 V spare. Worth correcting because the stated reasoning would mislead if the
bus voltage ever changed.

### New: mutual inductance, and a result that simplifies one decision

Both coils sit on the same magnetic circuit, so M = k·L is significant. Derived that
**τ = L(1+k)/R is identical for series and parallel** — series/parallel changes current
capability, not speed. That removes one variable from that trade-off.

Consequence for Q2: measuring one coil in isolation is insufficient. Need one coil with the
other **open** (gives L) and with the other **shorted** (gives L(1−k²)) — two readings give k.

### REVISED AND WORSE: the coil energy dump

The higher parallel-yoke inductance makes this worse, not better. At 30 A with L_yoke ≈
9.25 mH the coil stores **4.16 J**; dumped into the 470 µF bus cap with the battery absent
the bus reaches **146 V** against 100 V parts (my morning figure was 115 V). Holding it below
85 V on capacitance alone would need ~2300 µF per yoke.

The battery normally absorbs this, so the real fix is a sized TVS plus adequate bulk plus
never opening the bus under load — but **the 470 µF in the BOM was clearly not chosen with
this calculation behind it**, and the triggering fault (fuse opens or connector bounces at
peak) is plausible on a pod.

### Connector conflict is now dimensional, not a judgement call

EDD §2.2 specifies **10 AWG** conductors to the yokes. The Molex 0389220002 accepts
**AWG 12–26** and is rated **20 A**. The wire will not physically fit, and the part is rated
at two-thirds of the required current. This must be resolved with the lead before any
footprint is placed.

### Plant dynamics, now from their numbers

316 kg pod, 8 mm nominal gap, ~3100 N (internally consistent: 316 × 9.81 = 3100).
Unstable pole from the Fig. 3 force–gap slope ≈ **30.8 rad/s (4.9 Hz), 32 ms to double** —
considerably more benign than the 1–2 mm gap I had assumed this morning. Current-loop
separation lands at **2.7–3.5×** at the likely inductance: tight against the 5–10× rule of
thumb but not disqualifying, especially with 30 V of headroom to overdrive with.

### New open questions
- **Q22** — is 30 A/yoke a physics requirement, or inherited from the 30 A motor drivers
  being replaced?
- **Q23** — where does the 50 % duty limit come from: thermal, control, or the existing driver?
- **Q24** — is the EDD current? Does it describe the yoke on the pod today?

---
*Log continues.*

---

## 2026-08-12 — `power_channel` schematic review (netlist-level, not visual)

Reviewed the completed `power_channel` sheet. Rather than inspect the drawing, I parsed
`power_channel.kicad_sch` directly and rebuilt the connection graph from raw geometry —
symbol origins, library pin offsets, KiCad's rotation and mirror transforms, wire
segments, junctions, labels and power symbols — and extracted the netlist independently
of KiCad. 54 components, 142 wires, 57 junctions, 36 labels.

Full findings in `13_schematic_review_power_channel.md`.

### The drawing is geometrically clean

No dangling wire ends, no labels attached to nothing, no wires crossing without a needed
junction and none crossing with an unwanted one, no floating pins except the two the
no-connect flags cover. For a hand-drawn 142-wire sheet that is a good result and worth
recording, because the errors that *were* found are design errors, not drafting errors.

### One blocking error: the LM393 supply is reversed

`U4` unit 3 is rotated 90°, and after the rotation pin 8 (V+) lands on the GND symbol
while pin 4 (V−) lands on the +5 V wire. The comparator is powered backwards: it does not
work, it conducts through its ESD structures, and the over-current protection is silently
dead — `FAULT_N` floats high, the latch never sets, the bridge keeps switching.

**ERC will not catch this.** It reports "power input not driven" on both rails (correct,
since the rails are generated on a sheet that does not exist yet), and the swap hides
inside a message that is expected and will be dismissed.

Method note, because it matters: this hinged entirely on KiCad's 90° transform, and both
candidate sign conventions place the pins on wires, so geometry alone is ambiguous for
any two-pin part. It was resolvable only because the LM393 power unit's two pins share a
library x-offset, which forces them to share a y after rotation — and only one convention
puts that y at 59.69, where the GND symbol and the +5 V wire end actually sit. Fetched
copies of the KiCad source disagreed with each other on this, so the file itself had to
settle it. Same class of ambiguity as the IR2184 pinout mistake; caught this time.

### Quantified: the bulk capacitors cannot carry the ripple

Previously logged as "electrolytic ripple-current ratings unverified". Now closed with a
number. At 30 A and D ≈ 0.5 the bus sees **15 A RMS per channel**. At 32 kHz the two
470 µF electrolytics present ~25 mΩ against the eight 1 µF ceramics' ~620 mΩ, so the
electrolytics take **~14 A of it into parts rated about 2 A each**.

Adding ceramic does not fix it — matching 25 mΩ at 32 kHz needs ~190 µF of 100 V ceramic
before DC-bias derating. The answers are more electrolytics (6×), polymer/hybrid parts
(3–4×), or a lower real design current. Interleaving the two channels cancels ripple on
the shared bus but not in each channel's local commutation loop, so it cannot be used to
size these parts.

### The OCP path contradicts §3.2 of the design sheet

§3.2 says: on a fault, turn both low-side FETs **on** so the coil dumps into its own
resistance. The drawn OCP pulls `SD` low, which tri-states both half-bridges — a hard
turn-off, the one action §3.2 exists to prevent. The coil then freewheels through the
body diodes into the bus: 9.4 J at the 45 A trip, reaching 153 V into 940 µF if the bus
happens to be isolated.

The battery normally absorbs it. But an over-current is a plausible *cause* of a blown
fuse, so the trip and the isolated-bus condition are correlated, not independent.

Two options recorded: accept for rev 0 and log the limitation, or gate the PWM inputs
with the latch's Q̄ through a 74HC08 — which turns a fault into slow decay directly,
leaves `SD` high, and makes the OCP path and the bus-fault path behave identically. One
part. **Decision still open.**

### Design sheet vs. schematic drift

Two §4 items did not make it into the drawing:

- **§4.3 gate turn-off network** (4.7 Ω + parallel diode) — absent; gates have a single
  symmetric 10 Ω. Matters in an H-bridge because of dv/dt-induced turn-on through C_gd.
- **§4.5 shunt** — §4.5 says explicitly "not a 2512 thick film"; `R11` is committed to
  `R_2512_6332Metric`. 2.0 W at the 45 A trip against a 1 W part, plus a thick-film TCR
  that walks the trip point.

Either build them or amend §4. A design document that quietly disagrees with the
schematic is worth less than no document.

### Smaller findings

- INA240 input filter is 10 Ω + 1 nF → **7.96 MHz** corner. Effectively no filter. Not
  wrong (TI SBOA174 argues against heavy input filtering, which unbalances the CMRR the
  part depends on) but it should not be described as a filter.
- No bus bleed resistor. 940 µF at 60 V = **1.7 J** persisting after power-down on a
  board people will probe.
- Single `GND`; §3.1 lists AGND and DGND separately. Defensible for rev 0, but a decision.
- Missing footprints on U5, C19, C20, R12, R13. No voltage rating field on any capacitor —
  the most dangerous BOM omission on a 60 V board. No tolerance field on the three
  resistors that set the trip point.
- All seven hierarchical labels are typed `input`; COIL_A/COIL_B are passive and
  ISNS/FAULT are outputs.

### Confirmed correct against first-party datasheets

INA240 pin 4 verified against TI SBOS662: "Reserved. Connect to ground or leave floating"
— tying it to GND is permitted, and my earlier sketch saying "leave open" was equally
valid, not a correction. Threshold divider maths, comparator polarity (crossed inputs
giving OR through the wired-AND), latch set-dominance and power-on state, Q̄→SD, the SD
pulldown direction, both bootstrap diode orientations, the TVS cathode, the electrolytic
polarity, and gate pulldowns returned to their own sources — all verified correct from
the extracted netlist.

Worth noting one property of the design that emerged from the review rather than being
designed in: both trip thresholds and the INA240's 1.65 V mid-scale come from the same
3.3 V rail, so the trip current is ratiometric and rail error cancels instead of shifting
the trip point.

### Project file hygiene — a real risk, not housekeeping

The root sheet's `Sheetfile` property points at `..\..\Downloads\power_channel.kicad_sch`.
The live schematic lives in Downloads, outside the project folder, while two stale copies
(37 symbols and 24 symbols) sit inside `final_lev\` where they can be loaded by mistake.
Recovery procedure recorded in the review document.

---
*Log continues.*

---

## 2026-08-13 — RETRACTED: the LM393 supply reversal

**Yesterday's blocking finding was wrong. There is no error. U4 pin 8 (V+) is on `+5V`
and pin 4 (V−) is on `GND`, which is correct.** Sebastian caught it by looking at the
schematic; I had it from a reconstruction that was confidently, self-consistently wrong.

### Root cause

The whole netlist-extraction approach depends on getting KiCad's symbol rotation matrices
right. For `(at x y 90)` the library-to-sheet mapping is one 2×2 matrix. I solved for it
empirically — tried candidates, kept the one that made pins land on wires.

I compared the wrong pair:

    (0, 1, 1, 0)    det = −1     legal
    (0, 1, −1, 0)   det = +1     inadmissible

and chose the second, because under it U4's pins landed exactly on the +5 V wire end and
the GND symbol while under the first they floated. The evidence was real. The hypothesis
was impossible.

Every unmirrored placement in KiCad is the default transform `(1, 0, 0, −1)` — det −1,
because library Y is up and sheet Y is down — composed with a pure rotation, det +1. The
product must have **det −1**. Det +1 is a mirrored placement, and the file states U4 is
not mirrored. One line of arithmetic kills my answer.

The two legal 90°-family candidates are `(0, 1, 1, 0)` and `(0, −1, −1, 0)`. I never
tested the second because I had it filed under 270°. Correct mapping:

    0° → (1, 0, 0, −1)    90° → (0, −1, −1, 0)    180° → (−1, 0, 0, 1)    270° → (0, 1, 1, 0)

### The lesson, which is the part worth keeping

**Constraints before evidence.** I ranked hypotheses by how well they explained the data
without first checking whether they were physically admissible. The determinant test is
free and deletes an entire branch before any weighing starts. I did the expensive step
first and skipped the cheap one.

Two failure modes stacked on top of each other here:

1. I had already been burned on the IR2184 pinout by trusting a rendered datasheet page,
   so I over-corrected into "derive everything from raw geometry" — and then applied that
   method without its own sanity check.
2. Two independent web fetches of the KiCad source disagreed with each other on these
   matrices (one returned a 180° case that was not even a rotation). Having decided both
   were unreliable, I fell back on empiricism and treated the file as ground truth,
   forgetting that the file is only ground truth once the *reader* is correct.

`08_honest_assessment.md` says: *a design that is internally consistent and externally
wrong passes every check you can run on it.* That was written about the design. It
applies just as well to the analysis. My reconstruction was internally consistent under a
transform that cannot exist, and it stayed that way until a human looked at the screen.

### Scope of the retraction

Re-ran the extraction with corrected matrices and diffed against the previous run. **One
substantive change: U4 pins 4 and 8.** Every other delta is a pin-number swap on a
symmetric two-terminal part — resistors and non-polarised capacitors — where net
membership is identical and only the 1/2 labelling flips.

The only polarised parts at 90° or 270° are U4 unit 3 and D2. D2 re-checks correct
(cathode on `+60V`), but that now wants confirmation by eye rather than by my arithmetic.

Also cleared: with the corrected matrices, zero power symbols resolve as floating.

Unaffected, because none of it depends on rotation: the bus ripple-current calculation,
the OCP hard-off vs. slow-decay question, the missing gate turn-off network, the shunt
type, the INA240 input filter corner, the bleed resistor, the AGND/DGND decision, and all
of the housekeeping items. The schematic review is reissued as rev 1.

### Standing note

Second time Sebastian has overruled me on a KiCad connectivity claim and been right both
times. Recording that as a process fact, not a pleasantry: on anything that can be read
directly off the canvas, **his eyes are the instrument and my reconstruction is the
model.** When they disagree, the model is what gets re-derived first.

### File hygiene — resolved

`Desktop\final_lev\` is now self-contained. The live 58-symbol sheet is in the project
folder, the root sheet's `Sheetfile` property points at it locally instead of at
`..\..\Downloads\`, and the two stale copies are parked in `_old\` under names that make
them unmistakable. A pre-edit backup of the root sheet is in `_old\` as well.

---
*Log continues.*

---

## 2026-08-13 — `power_channel` closed out. ERC clean.

Sheet is finished: 62 components, 44 labels, all footprints assigned, title block and
nine on-sheet annotation blocks in place. ERC returns 12 errors and 6 warnings and
**every one of them is expected** — nothing on this sheet needs changing.

### ERC results, accounted for line by line

| Count | Message | Why it is expected |
|---|---|---|
| 7 err | `pin_not_connected` — all seven sheet pins on the root | The root sheet holds one sheet symbol and nothing else. Resolves when `IO_PROTECT` exists and the root gets wired |
| 5 err | `power_pin_not_driven` — +60V, +12V, +5V, +3V3, GND | PWR_FLAGs belong on `AUX_RAILS`, which does not exist yet. Deliberately not silenced here |
| 3 warn | `isolated_pin_label` — FAULT, PWM_A, PWM_B | Same root cause as the seven. These three hierarchical labels touch exactly one pin inside the sheet; the other four touch several |
| 2 warn | `pin_not_driven` — U1.1, U2.1 (IN) | The PWM inputs have no driver yet. Buffers are on `IO_PROTECT` |
| 1 warn | `multiple_net_names` — SW_B / COIL_B | Intentional. Half-bridge B's switch node *is* the coil B terminal, because the shunt is only in the A leg |

**ERC also settled an open question for free.** Five distinct `power_pin_not_driven`
violations means five distinct undriven power nets — which confirms `+60V` and `+12V`
are separate nets despite `#PWR01` being a `power:+12V` symbol with its Value edited.
Had they merged there would have been four. That closes the item without hovering
anything.

**On the `isolated_pin_label` warnings:** these are the exact warnings I misdiagnosed
earlier in this project, when I told Sebastian they were stray labels in the root sheet
and he deleted working ones on my advice. They are not stray. KiCad reports them at the
parent path because hierarchical connectivity resolves there, and they are benign until
the parent is wired. Nothing gets deleted.

**On SW_B / COIL_B:** KiCad will use `SW_B` in the netlist. Leave it. Deleting the local
`SW_B` label to force the other name would split the node — U2's VS pin and C16 sit in a
separate wire region joined only by that label, and they would be orphaned.

### Gate turn-off network — derivation now on record

The design sheet §4.3 called for 4.7 Ω + diode across each gate resistor without showing
the arithmetic, and I initially argued the case was weak based on a guessed C_rss of
~60 pF. Checked it against the datasheet instead: **IRF100B201 C_rss = 310 pF,
V_GS(th) = 2.0 V minimum, Q_gd = 45 nC.**

    t_miller = Q_gd / I_g   = 45 nC / 0.4 A        ≈ 112 ns
    dV/dt    = 60 V / 112 ns                       ≈ 0.54 V/ns
    i        = C_rss × dV/dt = 310 pF × 0.54e9     = 167 mA
    V_gs     = i × (R_gate + R_driver_sink)
             = 0.167 × (10 + ~3)  = 2.2 V     ← vs 2.0 V min threshold
             = 0.167 × (4.7 + ~3) = 1.3 V     ← with the network

A worst-case-threshold part starts conducting as originally drawn. §4.3 was right and my
scepticism was wrong; the difference was five times the reverse transfer capacitance.
The lever is the *victim's* gate impedance, not the aggressor's slew rate — turn-on stays
at 10 Ω deliberately, because speeding it up would raise dV/dt and make it worse.

### Two errors caught during the build, both mine

**Approving from a screenshot.** Sebastian showed me the first gate-turn-off branch and
I said it was correct — from the image, immediately after writing a document about why
images are not evidence. It was reversed. He then replicated it four times. As built it
would have been *worse than fitting nothing*: the diode bypassed the 10 Ω on turn-on,
raising dV/dt to 1.25 V/ns and the induced gate voltage to 5.0 V.

**Mirror is not rotation.** The first fix attempt mirrored the diodes instead of rotating
them, and nothing changed electrically. Worth recording why: a diode's two pins both lie
on the library x-axis, so at 90°/270° each pin's sheet-y depends only on its library-x.
Mirror-X negates library-y, which is zero for both pins — it repaints the body and moves
nothing. Only changing the angle to 270 swapped the ends. The picture changed and the
netlist did not, which is a compact illustration of why the file is the thing worth
checking.

### Remaining before layout

- Cosmetic: the BUS DECOUPLING annotation still overlaps wiring. Plot to PDF to confirm.
- Export the netlist to `levpdu/`.
- Netclasses (POWER / GATE / Default) before opening the PCB editor.
- Deferred by decision, not oversight: bulk electrolytics and the bus bleed resistor move
  to the shared BUS sheet; OCP hard-off accepted for rev 0.

---
*Log continues.*

---

## 2026-08-13 (later) — the shunt nearly took the board out, and F8 caught it

`power_channel` is closed. The last hour was spent on a fault that no ERC run would ever
have found, and it is the most instructive thing in this log.

### A 4-terminal footprint under a 2-pin symbol

After switching R11 to the Vishay WSK2512 land pattern, "Update PCB from Schematic"
returned:

    Warning: No net found for component R11 pad 4 (no pin 4 in symbol).
    Warning: No net found for component R11 pad 3 (no pin 3 in symbol).

Read casually that says "two unused pads". It did not. Pulling the pad geometry out of
KiCad's own `.kicad_mod` gave the real numbering:

| Pad | Role | Size | End |
|---|---|---|---|
| 1 | current | 3.3 × 2.03 mm | left |
| 2 | **sense** | 1.4 × 0.76 mm | left |
| 3 | **sense** | 1.4 × 0.76 mm | right |
| 4 | current | 3.3 × 2.03 mm | right |

Current terminals are **1 and 4**; sense terminals are **2 and 3**. That is Vishay's
numbering, not the sequential order anyone would assume. R11 was still a `Device:R` with
pins 1 and 2, so KiCad mapped SW_A to pad 1 (correct, large) and **COIL_A to pad 2 — a
1.4 × 0.76 mm sense terminal.** The full 30 A coil current would have been routed into a
sense pad while the large current pad on the far side sat unconnected. First power-up
failure.

And the Kelvin taps went nowhere, so the board would also have had 2-terminal sensing —
the exact defect the 4-terminal part was bought to fix.

### Fix

`Device:R_Shunt` (4 pins: 1 and 4 current, 2 and 3 sense, each sense tap adjacent to its
own current terminal) matches the footprint numbering exactly. Swapped via Change Symbol
so reference, value and footprint survived, then rewired — and critically, R12 and R13
were moved off the current nodes, which is the step that is easy to skip and would have
silently preserved the original defect:

    SNS_P     R11.2 — R12.1              Kelvin tap, SW_A end   → route as a pair
    SNS_P_F   R12.2 — C19 — U3.8 (IN+)   filtered, at the chip
    SNS_N     R11.3 — R13.1              Kelvin tap, COIL_A end
    SNS_N_F   R13.2 — C19 — U3.1 (IN−)
    SW_A      R11.1 (current)   COIL_A   R11.4 (current)

Sign preserved: SNS_P is the SW_A-side tap feeding IN+, so positive coil current still
reads above 1.65 V and the ±45 A window is the right way round. Had the sense pair been
crossed, the over-current trips would have fired on the wrong polarity — a fault that
would only show up on a real coil.

`R_Shunt` is also 2.54 mm wider than `Device:R`, which left the old wires overshooting the
new pins by 1.27 mm each side. Fixed.

### The lesson

**A footprint's pad numbering is a datasheet fact, not a convention.** The failure lived
entirely in the symbol-to-footprint pin mapping — invisible in the schematic, invisible
to ERC, visible only at the moment the schematic met the board. Which is an argument for
running F8 early, before layout is a sunk cost, rather than treating it as the last step.

Also worth stating plainly: this was introduced by *my* recommendation to move to a
4-terminal shunt. The advice was right; I gave it without checking that the symbol could
carry four pins.

### One more retraction: my own tooling had a bug

The first netlist cross-check disagreed with KiCad on exactly one thing — which end of R8
was pin 1. Cause: my mirror handling applied the flip in library space rather than output
space, which swaps pin numbering on any symbol that is **both rotated and mirrored**. R8
(270°, mirror X) is the only such symbol on the sheet, so it was the single part capable
of exposing it. No electrical consequence — a resistor is symmetric and net membership was
identical — but every rotated-and-mirrored part reasoned about earlier in this project
carried a latent pin-swap risk. Fixed, re-run, exact match.

That is the argument for the cross-check. Two independent methods disagreeing by one pin
number is how you find out one of them is wrong.

### Final state of `power_channel`

- **ERC:** 12 errors, 7 warnings — all traced to `AUX_RAILS`/`IO_PROTECT` not existing yet,
  plus the intentional SW_B/COIL_B naming. The new `isolated_pin_label` on COIL_A is
  positive evidence the Kelvin rewire took: COIL_A now holds exactly one pin inside the
  sheet because R13 correctly left it.
- **Update PCB from Schematic: 0 errors, 0 warnings.** 60 footprints, 39 nets.
- **Netlist cross-check: exact match on all 39 nets, pin for pin**, between KiCad's
  netlister and an independent reconstruction from raw symbol geometry.
- **Netclasses:** 6 classes (Default, HV_POWER, SENSE, GATE, AUX, ANALOG), 15 patterns,
  every named net resolving to exactly one class. `SNS_P`/`SNS_N` are a differential pair
  in the SENSE class — KiCad's `_P`/`_N` convention means the DP router will handle them
  as a coupled pair, which is the layout half of what the INA240 needs to reject 60 V of
  common mode.

Remaining before layout: BOM export, `min_clearance` 0.0 → 0.2, annular ring 0.1 → 0.13,
and copper 0.035 → 0.07 mm (2 oz — the board is not buildable at 1 oz).

---
*Log continues.*

---

## 2026-08-14 — BUS, IO_PROTECT, root wiring. Schematic complete.

The remaining three sheets and the root are done. **84 nets, 156 components, ERC 0 errors
and 1 accepted warning, netlist verified against an independent reconstruction.**

### BUS — power entry

Battery in on J101 (Molex 38969-0002, now approved by the lead), six 470 µF bulk
electrolytics, 22 k bleed, PWR_FLAGs on +60V and GND.

Two things worth recording. The bulk bank is **sized by ripple-current rating, not
capacitance** — ~20 A RMS on the shared bus once the two channels interleave 180°, so the
part count follows whatever ripple rating the chosen capacitor has rather than a target
microfarad number. And the bleed resistor was re-derived after the bank grew: 22 k against
2820 µF is τ = 62 s, so 60 V → under 10 V in ~110 s, not the ~40 s implied when the bank
was two capacitors. 5.1 J stored.

### The fuse is now a harness item, not a board part

Originally drawn as F101 on this sheet. Reversed after pulling the actual mechanical data:
the MIDI HP is a **bolt-down chassis component** — roughly 48 × 36 × 16 mm on M6 studs —
designed to bolt to a bus bar, not to FR4.

On-board it would have cost ~50 × 40 mm plus socket access at the battery entry, put M6
clamp load onto a 1.6 mm board through thermal cycling, and carried 60 A across a bolted
joint instead of a soldered one. In the harness it costs nothing, is what the part is for,
and **also protects the battery cable** — which a board-mounted fuse never could. A chafe
upstream of J101 is invisible to an on-board fuse.

Requirement recorded on the sheet as a text block, because it now lives outside this
board's boundary: **70 A Littelfuse MIDI HP, 70 VDC, 2500 A interrupting, mounted at the
battery.** Most automotive fuses are 32 V and are not acceptable. The note also states
explicitly that nothing fuses J101 locally, so no one reading BUS in isolation can
conclude the board is unprotected.

### IO_PROTECT — board I/O

Four connectors (rails in, 12-way control, two yoke outputs), PWM input buffering, output
conditioning, rail entry protection.

**Buffer choice — 74LVC2G17 at 3.3 V, and the reason is not the obvious one.** The library
had no HCT part, and 74HC7014 at 5 V needs 0.7 × VCC = 3.5 V to register a high, which a
3.3 V MCU cannot produce — that would have silently reintroduced assumption A4. LVC's
inputs accept up to 5.5 V *regardless of VCC* (verified on the SN74LVC2G17 datasheet), so
powered from 3.3 V it takes a 3.3 V or a 5 V MCU with no assumption either way. Output
drives the IR2184's 2.7 V VIH with 0.6 V of margin; the datasheet lists 3.3 V drive as a
supported configuration.

**10 k pulldowns on the four buffer inputs are a safety item.** An unplugged harness leaves
an LVC input floating, which oscillates. Pulled low, both IR2184 inputs sit low, both low-
side FETs turn on, and each coil is shorted through Q2/Q4 — slow decay. The safe state is
the default state whenever nothing is connected.

**RESET is pull-low-only, and this is a firmware constraint invisible from the schematic.**
The 74HC74 runs from +5 V and needs 3.5 V to release CLR. A 3.3 V MCU driving RESET high
push-pull would sit at 3.3 V — ambiguous — and the latch could stay permanently cleared,
losing fault latching entirely. Drive low to clear, then release; the on-board pull-up
provides the high level. Written onto the sheet.

**ISNS output filtering.** 100 Ω + 100 nF, with the capacitor on the *connector* side of
the resistor. First drawn with the cap on the amplifier side, which was wrong twice over:
it hung 100 nF directly on the INA240 output with no isolation resistor (stability), and
it loaded the very node the window comparators watch. On the connector side the resistor
isolates the amplifier and the RC gives a 16 kHz filter on the outgoing copy — while the
comparators tap ISNS upstream on power_channel, so the over-current trip stays fast.

### Rail protection, and a gap it exposed

D201/D202 are series Schottkys on the incoming +12 V and +5 V. Each does two jobs: blocks
reverse polarity, and **isolates the hold-up capacitor** so it cannot back-feed into a
collapsing pod rail — which is the job C201 exists for in the first place.

+3.3 V deliberately gets none. A 0.35 V drop would cost ~10 % of the current-sense
full-scale range, and losing 3.3 V **fails safe**: the buffer outputs go low, the IR2184
inputs go low, the low-side FETs turn on, slow decay.

Working through that rail by rail exposed something. Slow-decay-on-fault needs two things
true at once:

    12 V alive     → drivers can hold the low-side FETs on     C201 covers this
    SD held HIGH   → drivers not shut down                     nothing covered this

SD is driven by U5 pin 6 — the 74HC74's Q̄ — **and that chip runs from +5 V**. If the 5 V
rail dies mid-fault, R19's pulldown drags SD low, the bridge tri-states, and the coil dumps
into the bus: exactly what §3.2 exists to prevent. The board was half-provisioned — 12 V
anticipating a feature the 5 V rail equally depends on. Fixed by giving +5 V the same
treatment: blocking diode plus 220 µF.

Neither is exercised yet — the bus-fault detector §3.2 describes still isn't designed, and
the OCP path remains hard-off by accepted rev-0 decision. But provisioning half of a
mechanism is worse than provisioning none, because it looks finished.

### Root — dual instantiation

CH1 and CH2 both point at power_channel.kicad_sch. Thirteen nets joining IO_PROTECT to the
two channels, drawn as short stubs with matching local labels rather than long wires.
RESET is the only one-to-many, shared by both channels.

### The #PWR duplicate episode

Annotating with "Keep existing" produced 32 "Duplicate items" errors and KiCad refused a
full ERC: *schematic is not fully annotated*. All 253 instance-references were assigned —
the problem was that every `#PWRxx` was identical across CH1 and CH2, because power symbol
references were already set and "keep existing" kept them. Real components renumbered
correctly into the gaps the 100/200 blocking had left (CH2 took C211–C231, R210–R232,
D203–D209, Q201–Q204, U203–U207 with zero collisions).

Fixed by rewriting **only CH2's path references** to #PWR0301–#PWR0332 directly in the
file, after diffing CH1's full 96-reference list before and after and asserting equality
before writing. The obvious alternative — KiCad's "Reset existing annotations" — would have
renumbered all 120-odd real components across the design to fix something cosmetic,
invalidating the review document, this log and the netlist snapshot.

Worth remembering as a hierarchical-design gotcha: **power symbol references are per
instance path, and "keep existing" will not make them unique for you.**

### Verification

- **ERC: 0 errors, 1 warning** — the SW_B/COIL_B naming, reported once because both
  channels share a sheet file.
- **Netlist cross-check: exact match on all 84 nets, pin for pin**, between KiCad's
  netlister and a reconstruction built from raw symbol geometry, rotation matrices and
  hierarchical label resolution across four sheets and two instances.
- That check found one more bug in my own tooling: PWR_FLAG lives in the `power:` library,
  so it was being treated as a net-naming symbol and keyed on its Value — welding +60V,
  +12V, +5V, +3.3V and GND into a single net. A flag is a marker, not a name. Second
  tooling bug the cross-check has caught, after the mirror-transform error on R8.
- **All 37 capacitors now carry a Voltage field.** The bus bank had been covered only by a
  text note, but the note lives on the drawing and the BOM is what people order from.

### Remaining before layout

One custom footprint (Molex 38969-0002, used by J101/J203/J204). J201 and J202 still need
real parts chosen — pick something KiCad already has footprints for and that count goes to
zero. Board Setup values and 2 oz copper are done.
