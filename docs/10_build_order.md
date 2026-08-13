# Build Order — What to Draw, In What Sequence

Levitation coil drive stage · Sebastian · 2026-08-11
Companion to `09_design_sheet_rev0.md`

---

## 0. Workflow flag — read this before you start drawing

You said schematic in LTspice, then PCB in KiCad. **That's double work, and you don't have
time for it tonight.**

LTspice has no refdes management, no footprint assignment, no ERC, and no netlist export
KiCad can consume. Drawing 100 components there and then redrawing them in KiCad is two
full passes.

**Suggested instead:**

- **KiCad is the schematic of record.** Draw the real, complete schematic there — it's what
  feeds the PCB and what anyone reviews.
- **LTspice is for proving the blocks you're unsure of.** Four small sims, not a board:
  bridge + load, bootstrap hold-up, fault decay, OCP trip.

That's one pass plus four focused simulations, rather than two full passes. If your class or
your lead specifically requires an LTspice schematic, ignore this — but if it was just your
plan, this saves you hours tonight.

---

## 1. Two corrections to the design sheet

### 1.1 Logic buffer changed: **74HCT2G17**, not 74LVC2G17

The IR2184 datasheet gives **V_IH = 2.7 V minimum**. A 3.3 V logic high leaves only 0.6 V of
margin on a switching board — not enough.

**74HCT** has TTL-level inputs (V_IH = 2.0 V) on a 5 V supply. So it accepts a 3.3 V *or* a
5 V MCU and outputs a clean 5 V into the IR2184. That is a solid 2.3 V of margin over
threshold, and it makes the logic-level question genuinely irrelevant rather than
approximately irrelevant.

**Part: 74HCT2G17 (dual Schmitt buffer), supplied from 5 V.** You'll need a 5 V rail —
add a small LDO off the 12 V.

### 1.2 ⚠️ Two things you must verify yourself before placing anything

I pulled these from the datasheet PDF and I am **not confident in either**, because both come
from graphics rather than text:

**(a) The SD pin polarity.** I got "active HIGH for shutdown," but the IR2183/IR2184 family
differs on exactly this point between variants, and I've seen the opposite claimed. Getting
it wrong means either a permanently dead board or permanently defeated protection.

→ **Read the truth table on page 2 of the datasheet yourself.**
→ **And design around it:** bring the latch output to SD through a **strap-selectable
inverter** — a 74HCT1G14 that you can bypass with a 0 Ω link. Costs one part and a jumper,
and makes the polarity a build-time decision instead of a re-spin.

**(b) The pin numbering.** My extraction gave: 1 IN, 2 SD, 3 COM, 4 LO, 5 VB, 6 HO, 7 VS,
8 VCC. That VB/VS ordering looks wrong to me versus the usual IR2184 arrangement.

→ **Check the package drawing in the datasheet directly.**

This is worth taking seriously: the previous design's own open-items list flagged
*"cross-check every part's footprint pin-out against its datasheet — the one error class the
audits don't catch."* That was correct then and it's correct now. **Every footprint gets
checked against the package drawing, by eye, before layout.** Not against my text, not
against a KiCad library symbol.

**Confirmed good from the datasheet** (these came from tables, and they validate the design
sheet): V_BS UVLO rising **8.0–9.8 V** — the bootstrap calc stands. Deadtime **280–520 ns** —
adequate against ~200 ns turn-off.

---

## 2. Build order

Build the **atom first**, prove it, then replicate. Do not draw all four FETs and two drivers
and then try to debug.

### Step 1 — Sheet setup (15 min)

Hierarchical sheets: `POWER_CHANNEL` (×2), `AUX_RAILS`, `IO_PROTECT`.
Draw the channel once as a hierarchical sheet and instantiate it twice. Do not copy-paste —
you'll fix a bug in one copy and not the other.

Paste the §2 assumption register from the design sheet into a text block on sheet 1.

### Step 2 — One half-bridge + its driver ← **the atom**

Q1 (high) + Q2 (low) + one IR2184.

    VCC(12V) ──┬── C 1µF + 100nF ── COM
               └── D_boot(ES1D) ── R_boot(1Ω) ──┬── VB
                                                └── C_boot(1µF/25V) ── VS
    HO ── R_on 10Ω ∥ (R_off 4.7Ω + diode) ── Q1 gate
    LO ── R_on 10Ω ∥ (R_off 4.7Ω + diode) ── Q2 gate
    VS ── switch node (Q1 source / Q2 drain)
    COM ── power ground
    IN ── from 74HCT2G17 buffer
    SD ── from latch, via the strap-selectable inverter (§1.2a)

Add 10 kΩ gate-to-source pulldowns on both FETs — holds them off before the 12 V rail comes
up.

**Prove this in LTspice before going further.** Drive IN with a 32 kHz pulse, watch V_B − V_S
across the full duty range, confirm it never approaches the 9.8 V UVLO. This is the single
most useful sim you will run.

### Step 3 — Mirror to a full H-bridge

Second half-bridge, second IR2184, both across the same bus. Coil connects between the two
switch nodes.

**Both PWM inputs go to the connector independently** (design sheet §3.1). Resist the urge to
generate the second one on-board from the first — that's what locks you into a modulation
scheme.

### Step 4 — Bus network

2× 470 µF 100 V + 4× 1 µF 100 V 1210 + 4× 100 nF 0805, plus the 5.0SMDJ70A TVS.

**Layout note for later:** the ceramics go physically closest to the FET drains. The
commutation loop — bus cap → Q1 → Q2 → back to cap — is the highest-di/dt loop on the board
and it must be as small as possible. This matters more than almost anything else in the
layout.

### Step 5 — Current sense

1 mΩ 4-terminal shunt **in-line with the coil**, INA240A1 across it, REF pin at 1.65 V from
the 3.3 V rail via a divider + buffer (or a reference IC — a resistor divider alone will
drift).

Kelvin connections from the shunt sense terminals to the INA240 inputs, routed as a tight
differential pair. Small RC filter at the inputs.

### Step 6 — OCP + latch

LM393 as a window comparator: INA240 output vs. **2.55 V** and vs. **0.75 V**.
Open-collector outputs wire-OR with a common pull-up.

Into a **74HC74** as a set-dominant latch → strap-selectable inverter → both IR2184 SD pins.
Bring the latch output to the connector as `/FAULT`, and bring a reset line in.

**Do not skip the latch.** The old BOM had a bare LM393, which means the fault self-clears
the instant current drops and the bridge chatters into the fault repeatedly.

### Step 7 — Bus-fault detector → slow decay

This is design sheet §3.2 and it's the piece that makes the energy dump a non-problem.

Comparator on the bus voltage. On undervoltage or overvoltage: **drive both low-side FETs on**
rather than shutting everything off. Note this is *different* from the OCP path — OCP shuts
the bridge down, bus-fault commands slow decay.

**220 µF hold-up on the 12 V rail** so the FETs stay driven for the ~60 ms the current takes
to decay.

### Step 8 — Aux rails

LM5164 60 V → 12 V. Then 12 V → 5 V (buffers) and 12 V → 3.3 V (INA240, reference).
Mark the LM5164 DNF-able in case the pod supplies 12 V.

### Step 9 — Connectors

- Power (battery in, 2× yoke out): **Molex 38969-0002**, 50 A, 8–20 AWG
- Signals: the lead's Molex 0389220002, 20 A — fine here

Per channel: `PWM_A`, `PWM_B`, `/SD`, `ISENSE`, `/FAULT`, `RESET`, `AGND`, `DGND`.

---

## 3. The four simulations worth running

| # | Sim | Proves | Pass criterion |
|---|---|---|---|
| 1 | Bootstrap hold-up, duty 5–95 % | §4.3 sizing | V_B − V_S never below 10 V |
| 2 | Bus open at 30 A, both low FETs on | §3.2 | Bus stays under 100 V; current decays in <100 ms |
| 3 | Ripple, sign-magnitude vs. antiphase | Modulation sensitivity | Shows which scheme costs you |
| 4 | Shorted coil → OCP | Trip timing | Latch fires, bridge off, current bounded |

Sweep, don't confirm:

```
.param Rcoil=2  Lcoil=10m  kcpl=0.85  Vbus=60  Fpwm=32k
.step param Lcoil list 5m 10m 13m
```

If a result barely moves across that sweep, the design is insensitive to the thing you don't
know — which is the actual thing worth demonstrating tomorrow.

---

## 4. Suggested time budget

| | |
|---|---|
| Sheet setup + assumption block | 15 min |
| Half-bridge atom + sim 1 | 1 h |
| Mirror to H-bridge | 20 min |
| Bus network | 20 min |
| Current sense | 45 min |
| OCP + latch | 45 min |
| Bus-fault → slow decay | 30 min |
| Aux rails | 30 min |
| Connectors + IO | 30 min |
| Second channel (instantiate) | 10 min |
| Sims 2–4 | 1 h |
| **Total** | **~6 h** |

Doable. **If you run short, drop sims 3 and 4 and the bus-fault detector** — the fault
detector is a genuine improvement but it's the piece you can add in rev 1 without disturbing
anything else.

---

## 5. What to tell your lead tomorrow

Lead with what makes this defensible rather than with what's unresolved:

1. **Topology derived, not inherited** — H-bridge justified from the confirmed PM-biased
   HEMS architecture, with the simpler alternative documented and ruled out on evidence.
2. **Three unknowns designed around rather than guessed** — independent PWM inputs make the
   modulation scheme irrelevant, HCT buffers make the logic level irrelevant, and
   slow-decay-on-fault makes the inductance irrelevant to protection.
3. **A real defect found and fixed** — the previous BOM's over-current comparator had no
   latch and would chatter into a fault.
4. **A connector conflict caught before layout** — the EDD specifies 10 AWG, the specified
   part accepts 12 AWG max at 20 A. Resolved with Molex 38969-0002 at 50 A, same family.
5. **One open risk, stated plainly** — if the coil is 4 Ω rather than 2 Ω the gate drive
   needs rework. Independent calculation from the coil geometry says 2 Ω. One measurement
   closes it.
