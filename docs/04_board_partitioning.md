# Board Partitioning — One Board or Two, and Is a PDU Needed?

Levitation coil drive stage · Sebastian · 2026-08-11 · Rev 0

---

## 0. What a PDU is

"PDU" = **Power Distribution Unit**. In the prior design it is a separate small PCB that
sits between the battery and the drive boards and does four jobs:

1. **Fusing** — one main fuse for the whole pack, so a fault anywhere opens one device
2. **Transient clamping** — a TVS across the bus
3. **Precharge** — a resistor that charges the boards' bulk capacitors *before* the main
   contactor closes, so closing the contactor doesn't weld it shut with an inrush spike
4. **Splitting** — one battery input fans out to two board outputs

It contains no switching and no control. It is a fuse, a diode, a resistor and some
copper. **It exists only because the prior design used two drive boards** — something has
to split the pack between them.

**Consequence: the PDU question and the board-count question are the same question.**

- One 4-channel drive board → protection lives on that board → **no PDU**
- Two 2-channel drive boards → something must split the pack → **PDU needed**

---

## 1. Reframe: the overview document is not a requirements document

You've confirmed the "permanent-magnet biased suspension" claim was likely AI-generated
rather than told to you by the lev team. That has consequences beyond that one sentence.

**The overview PDF is a design *output* with rationale back-filled onto it.** Its
"requirements" sections read like requirements but were partly reconstructed to justify
decisions already made. So from here:

- **`more_constraints.txt` is authoritative.** It is a transcript of humans stating
  requirements.
- **The overview PDF is a hypothesis.** Every claim in it needs a source before it is
  designed against.

Specific claims in the overview PDF now carrying an UNVERIFIED flag, in addition to the
PM-bias claim:

| Claim | Why it's suspect |
|---|---|
| "Magnets carry the pod's static weight at essentially zero current" | Confirmed likely AI-generated. This was the *entire* justification for the H-bridge. |
| "Brief peaks up to 30 A during disturbances" | The lev team never said 30 A or "brief". They said 60 A total minimum. |
| "A lost diagonal keeps remaining support roughly balanced" | Plausible-sounding, unsourced. This is the entire justification for two boards. See §3.5. |
| "Over-current trip 45 A" | Derived from the unverified 30 A figure, and unreachable at 60 V into 2 Ω anyway. |
| "2 Ω / 5 mH per yoke" | Derived from an unresolved series-vs-parallel question. |

This is not a reason to distrust everything — the ripple maths, the freewheel choice and
the INA240 selection all held up under independent check. It is a reason to **source each
claim before designing against it**, which is what the open-questions document does.

---

## 2. What actually sets the board count

Three things, in order of weight. Two of them are still unanswered.

### 2.1 Bus current — depends on Q1, and it is close to decisive

Board input current is set by yoke current and channel count. It does **not** depend on
the topology choice (T2 vs T3), because that changes the switch count, not the current.

| | 4 channels on one board | 2 channels per board |
|---|---|---|
| @ 15 A/yoke | 60 A board input | 30 A board input |
| @ 30 A/yoke | **120 A board input** | 60 A board input |

From the first-pass copper analysis: 60 A on a PCB is comfortable. **120 A is a genuinely
hard PCB problem** — roughly 48–73 mm of uninterrupted 2 oz copper, on a board where the
fuse, TVS and connectors all interrupt it.

> **If Q1 comes back at 30 A/yoke → two boards.**
> **If Q1 comes back at 15 A/yoke → one board is viable, and simpler.**

### 2.2 Physical layout of the pod — UNANSWERED, needs asking

If the four yokes sit at four corners of the pod, a single central board means four long
high-current runs. Long runs at 15–30 A with 16 kHz switching mean voltage drop, loop
inductance and radiated EMI. Two boards placed near yoke pairs halve the run length.

If the pod is small enough that the runs are short either way, this factor drops out.

**I don't know the pod's dimensions or where the yokes sit. This needs asking.**

### 2.3 Measurement reference integrity — favours one board

Four current measurements feed one controller. On a single board there is one analog
ground and the four readings are directly comparable.

Across two boards, each INA240's *output* is referenced to its own board's ground — and
those grounds carry 30–60 A of switching current. Offsets between them appear directly as
current-measurement error. With a 1 mΩ shunt, 1 A of coil current is 1 mV at the shunt;
tens of millivolts of ground offset is not a rounding error.

This is **solvable** — the INA240 has REF1/REF2 pins precisely for referencing the output
to a remote ground, and differential ADC inputs also work. But it is extra design work
that the single-board option simply doesn't have.

---

## 3. The practical factors

### 3.1 Assembly effort

| | T2 (asym. half-bridge) | T3 (full H-bridge) |
|---|---|---|
| FETs on a 4-channel board | 8 | **16** |
| FETs on a 2-channel board | 4 | 8 |

Sixteen TO-220s hand-soldered onto one board, all needing to bolt flat to a common
heatsink with correct insulation and torque, is a meaningful assembly risk. Eight is not.

### 3.2 Blast radius of a mistake — the factor that probably matters most here

You are restarting this design because you didn't trust the last one. That implies you
expect to find errors, and the right question is what an error costs.

A layout error on a **4-channel board** costs one full re-spin and takes the whole pod
down until it arrives. A layout error on a **2-channel board** costs a re-spin of a
smaller, cheaper board — and if you ordered five, you have spares to test the fix on while
the pod keeps a working pair.

At prototype quantities the economics favour this too: five copies of a small board is
typically no more expensive than five copies of a large one, and you lay out **one** design
either way because the two boards are identical.

### 3.3 Spares and interchangeability

Two identical boards means one spare covers either position. A single 4-channel board has
no spare unless you build a second complete one.

### 3.4 Harness complexity — favours one board

One board: one battery input, four yoke outputs, one control connector.
Two boards: two battery feeds (hence the PDU), four yoke outputs split across two
connectors, two control connectors. More connectors is more failure points — and given the
20 A connector constraint already in play, connector count is not a free variable.

### 3.5 Fault tolerance — do NOT inherit this argument

The overview PDF's headline reason for two boards is that a board failure costs two yokes
instead of four, and that a diagonal pair is more recoverable than an adjacent pair.

The *geometry* argument is sound in isolation: losing diagonally opposite corners keeps
the remaining support roughly balanced about the centre of mass, where losing two adjacent
corners produces a large pitch or roll moment.

**But the premise is unverified.** If losing any two of four yokes means the pod drops
regardless, then "which two" is irrelevant and this entire justification evaporates. I
could not find a general answer in the literature — it depends on their specific pod mass,
geometry, gap and remaining force margin.

**Ask the lev/controls team: is the pod controllable on two yokes at all?** If the answer
is no, two boards must be justified on §2.1, §3.1 and §3.2 alone — which, to be clear, is
still a sufficient case. It just isn't *this* case.

---

## 4. Recommendation

**Provisional: two identical 2-channel boards — but for §2.1, §3.1 and §3.2, not for the
fault-tolerance reason the overview document gave.**

This is provisional because it flips to a single 4-channel board if Q1 comes back at
15 A/yoke *and* the yokes are physically close together. Both answers are outstanding.

The decision resolves instantly once Q1 lands:

```
Q1: peak current per yoke?
├── 30 A → 120 A on one board is a hard PCB problem   → TWO BOARDS + PDU
└── 15 A → 60 A on one board is comfortable
          └── Are the yokes physically far apart?
              ├── YES → TWO BOARDS + PDU   (shorter high-current runs)
              └── NO  → ONE BOARD, no PDU  (simplest harness, one analog ground)
```

---

## 5. If two boards: buy the PDU, don't build it

**This is the strongest cost/schedule recommendation in this document.**

The PDU contains no switching and no control. It is a fuse, a TVS, a precharge resistor
and copper. Designing a PCB to carry 60–120 A is one of the harder problems in this
project — and it is a completely solved commercial problem in the marine and solar world,
where 48 V nominal battery systems are routine.

What you'd buy instead:

- **A bolt-down bus bar / distribution block.** Commercial units are widely available at
  150–500 A with M8/M10 studs. ⚠️ **Check the DC voltage rating.** Most automotive and
  marine distribution blocks are rated 48 V DC or below; your bus is 60 V. This is a real
  filter, not a formality.
- **A properly voltage-rated main fuse.** The **Victron MEGA-fuse** is available in an
  **80 V DC** variant covering 40 A through 500 A — which spans both candidate current
  targets with genuine voltage headroom over a 60 V pack. This also resolves the separate
  problem already flagged, that standard ANL and MIDI bolt-down fuses are commonly rated
  only 32 V DC and are **invalid on a 60 V bus**.
- **Precharge and contactor at the pack**, which is where the prior design already put
  them — correctly.

**What this buys you:** the highest-current, highest-consequence part of the system is
handled by parts with published ratings and real interrupting capacity, instead of by a
2 oz PCB pour you'd have to defend. It removes an entire board from your fabrication
schedule. And it removes the one part of the design where a copper-sizing mistake starts
a fire rather than just failing.

**What to verify before committing:** the DC voltage rating of every candidate part, and
the fuse's interrupting capacity at 60 V DC. DC interrupting is much harder than AC
because there is no zero crossing to help extinguish the arc, and ratings do **not**
extrapolate upward from a lower-voltage variant.

---

## 6. Questions this generates

**For the lev / controls team:**
- **Q16.** Is the pod controllable on two yokes? This decides whether modular fault
  tolerance is a real benefit or a retrofitted justification.
- **Q17.** What are the pod's dimensions and where do the four yokes physically sit
  relative to where the electronics would mount? This sets whether one central board means
  unacceptably long high-current runs.

**For you:**
- **Q18.** What is your budget, and is buying a commercial fused distribution block
  instead of fabricating a PDU acceptable to your lead? It is the right engineering call,
  but it removes a board from the project, which may matter if the project is being
  assessed on what you built.

---

## Sources

- Victron MEGA-fuse, 32 V / 58 V / **80 V DC** variants, 40–500 A — https://bluemarine.com/products/victron-mega-fuse-32v-48v-80v
- Littelfuse MIDI HP 70 V DC bolt-down fuse (PCB-mount alternative) — https://www.littelfuse.com/assetdocs/littelfuse-datasheet-4998-midihp70v?assetguid=b72fcd7a-c66d-4916-844c-ac55ebed196c
