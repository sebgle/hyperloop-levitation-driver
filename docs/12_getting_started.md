# Getting Started — Open KiCad and Draw This

Levitation coil drive stage · Sebastian · 2026-08-11

You're right that the topology is standard and you can copy the shape. Values can come later.
But **four decisions change the shape**, not the values — get those right now.

---

## 1. The four structural decisions (get these right, redraw otherwise)

### 1.1 Two PWM inputs — one per LEG. Neither of them is a direction signal.

**This is not "duty cycle + direction."** Both wires are PWM. There is no direction wire.

Your H-bridge has two legs. Each leg is a half-bridge (one top FET, one bottom FET) with its
own IR2184. **The IR2184 needs exactly one input** — it drives its top and bottom FETs
opposite to each other automatically, with deadtime. So:

> **2 legs → 2 drivers → 2 input signals. That's the whole reason there are two.**

Each signal controls what voltage *its own leg's output* sits at:

    V_coil = V_A − V_B = 60 V × (D_A − D_B)

| D_A | D_B | Coil sees | Current |
|---:|---:|---:|---|
| 100 % | 0 % | +60 V | max, forward |
| 75 % | 25 % | +30 V | half, forward |
| 50 % | 50 % | 0 V | zero |
| 25 % | 75 % | −30 V | half, **reverse** |
| 0 % | 100 % | −60 V | max, **reverse** |

**Direction is the *sign of the difference* between the two duty cycles.** It doesn't need
its own wire — it falls out of the arithmetic.

And this is why it makes the modulation question disappear. Both schemes run on identical
hardware:

- **Sign-magnitude:** hold `D_B` at 0 %, sweep `D_A` 0→100 % for forward. Swap the roles for
  reverse.
- **Locked antiphase:** set `D_B = 1 − D_A`. Now 50 % means zero current, 100 % means full
  forward, 0 % means full reverse.

**What NOT to do:** bring in one PWM + one DIR line and build logic gates that route the PWM
to the correct leg. That works, but it welds sign-magnitude into copper. If the answer comes
back "antiphase," you redraw and re-spin.

Two wires, no gates, no commitment. It costs one extra signal line.

### 1.2 Shunt goes IN-LINE with the coil, not in the ground leg

Ground-leg (low-side) sensing is easier to draw and easier to route, and it's what most
hobby designs do. It also cannot see bidirectional current, which you need.

**The shunt sits between one switch node and one coil terminal:**

```
SWA ──[SHUNT]── COIL_A ──[COIL]── COIL_B ── SWB
        │  │
      INA240 inputs (Kelvin)
```

This puts the sense amplifier's inputs on a node that swings 0↔60 V at 32 kHz — which is
exactly what the INA240 is built for, and why that part is in the design.

### 1.3 The bus-fault block turns FETs ON, not off

Two *separate* protection paths, and they do opposite things:

| Path | Trigger | Action |
|---|---|---|
| **Over-current** | ±45 A on the shunt | Latch → shut the whole bridge **off** |
| **Bus fault** | Bus under/over-voltage | Force **both low-side FETs ON** (slow decay) |

Draw them as two separate blocks. If you merge them into one "fault → shutdown" signal you
lose the energy-dump protection and you will not notice until something is 146 V.

### 1.4 Put a bypassable inverter between the latch and the `SD` pins

I could not confidently determine whether the IR2184's `SD` is active high or active low —
the family differs on this. Rather than guess:

```
LATCH_OUT ──┬──[74HCT1G14 inverter]──┬── SD (both drivers)
            └────────[0Ω link]───────┘
```

Populate one or the other once you've read the truth table. One part, and the polarity stops
being a re-spin risk.

**Everything else is a value you can change later without redrawing.**

---

## 1.5 The protection, in plain language

Four things can go wrong. Each gets its own answer.

### ① Both FETs in one leg turn on at once → dead short across the battery

Called **shoot-through**. Hundreds of amps in microseconds, FETs destroyed.

**Handled for you.** The IR2184 physically cannot turn both its outputs on simultaneously,
and it inserts 280–520 ns of dead time between them. **You draw nothing.** This is a big part
of why that chip was chosen.

### ② Too much current — a shorted coil, a pinched wire, a bad command

**Detect it:** the shunt measures current, the INA240 amplifies it, a comparator watches for
±45 A.

**Act on it:** shut the whole bridge off.

**The catch — it must latch.** If you just switch off, current falls, so the fault clears, so
it switches back on, so the fault returns — thousands of times a second, chattering into a
short until something burns. A **latch** (74HC74) holds the fault until you deliberately
reset it.

*The previous design had the comparator but no latch. That's a real defect.*

### ③ The battery disconnects while current is flowing ← the sneaky one

A fuse opens, a connector bounces, the contactor trips — at 30 A.

Your coil is storing **4.16 joules** in its magnetic field, and that energy has to go
somewhere. Normally it flows back into the battery. With the battery gone, it slams into the
bus capacitors instead:

    V = √(2E/C) = √(2 × 4.16 / 470 µF) ≈ 146 V

Your FETs and capacitors are rated 100 V. Everything on the bus dies. And **capacitance can't
save you** — even 1000 µF only gets you to 109 V.

**The fix costs nothing: turn both BOTTOM FETs on.**

The current then runs in a circle — `coil → Q2 → Q4 → coil` — and burns itself out in the
coil's own 1 Ω in about 46 ms. All 4.16 J stays in the coil as a trivial amount of heat. The
bus never sees it.

So: a comparator watches the bus voltage, and if it goes out of range it turns **switches
on**, not off. Plus a 220 µF capacitor on the 12 V rail so the FETs can still be *driven* for
those 46 ms after the bus is gone.

> **This is why ② and ③ must be separate circuits. They do opposite things.** Over-current
> shuts everything off. Bus fault turns switches on. Merge them and you lose ③ entirely.

### ④ Something catastrophic

A **fuse** (rated for 60 V *DC* — most automotive fuses are only rated 32 V and won't reliably
clear a DC arc) and a **TVS diode** across the bus to clamp whatever's left.

**Summary:**

| Problem | Answer | Do you draw it? |
|---|---|---|
| Shoot-through | IR2184 interlock + deadtime | No — built into the chip |
| Over-current | Shunt → INA240 → comparator → **latch** → all FETs off | Yes |
| Battery disconnect | Bus comparator → **both bottom FETs ON** | Yes |
| Catastrophic short | Fuse + TVS | Yes |

---

## 2. Have these open while you draw

| Document | Use it for |
|---|---|
| **IR2184 datasheet** — [PDF](https://www.infineon.com/assets/row/public/documents/24/49/infineon-ir21844s-datasheet-en.pdf) | The "Typical Connection" diagram is literally the half-bridge you're drawing. **Also read the truth table on p.2 for §1.4.** |
| **TIDA-00365 schematic** — [ti.com/tool/TIDA-00365](https://www.ti.com/tool/TIDA-00365) | A real, manufactured 75 V / 10 A discrete full bridge. Download schematic **TIDRN75**. Closest published thing to what you're building. |
| **Infineon AN-978** — [PDF](https://www.infineon.com/assets/row/public/documents/24/42/infineon-hv-floating-mos-gate-drivers-applicationnotes-en.pdf) | The canonical reference for bootstrap gate drive. Section on bootstrap component selection. |
| **Your `09_design_sheet_rev0.md`** | Values, when you get to them |

---

## 3. Set up the KiCad project first (15 minutes, saves hours)

**Hierarchical sheets.** Create these:

```
root.kicad_sch
├── POWER_CHANNEL.kicad_sch   ← instantiate TWICE
├── AUX_RAILS.kicad_sch
└── IO_PROTECT.kicad_sch
```

**Draw the channel ONCE and instantiate it twice.** Do not copy-paste a channel — you will
fix a bug in one copy and not the other, and that class of error survives every check you can
run.

**Net naming.** Decide now, stick to it. Hierarchical labels on the channel sheet:

| Net | What |
|---|---|
| `VBUS`, `PGND` | 60 V power in, power ground |
| `+12V`, `+5V`, `+3V3`, `AGND` | aux rails |
| `SW_A`, `SW_B` | the two switch nodes |
| `COIL_A`, `COIL_B` | coil terminals (after the shunt) |
| `VB_A`, `VS_A`, `VB_B`, `VS_B` | floating bootstrap supplies |
| `PWM_A`, `PWM_B`, `SD` | control in |
| `ISNS`, `FAULT`, `RESET` | status out |

Note `SW_A` and `COIL_A` are **different nets** — the shunt is between them. Easy to
accidentally merge.

**Symbols.** Don't burn time making perfect ones tonight:

- MOSFETs → `Device:Q_NMOS_GDS`, set the value to `IRF100B201`
- IR2184 → make a plain 8-pin rectangle. Verify pin numbers against the **package drawing**,
  not against my notes or a downloaded symbol.
- INA240, LM393, 74HC74 → standard 8/14-pin symbols exist in the stock libraries
- Footprints can wait — assign them after the schematic is complete

---

## 4. Draw the half-bridge atom first

**Do not draw four FETs and two drivers and then debug.** Draw ONE leg completely, check it,
then mirror it.

### The ~14 parts in one leg

```
                          VBUS
                            │
        +12V                │
          │                 │
        [R_boot 1Ω]         │
          │                 │
        [D_boot ES1D]       │
          │                 │
    ┌─────┴─────┐           │
    │  VB       │           │
    │        HO ├──[10Ω]────┤ gate
    │           │  ∥        │
    │           │ [4.7Ω+D]  ├─── Q1 (IRF100B201, high side)
    │  IR2184   │           │
    │        VS ├───────────┴──── SW_A  ←── switch node
    │           │                   │
    │  VCC ─────┼── +12V            │
    │  COM ─────┼── PGND            │
    │           │                   │
    │        LO ├──[10Ω]────┐       │
    │           │  ∥        ├─── Q2 (IRF100B201, low side)
    │  IN ──────┼─ PWM_A    │       │
    │  SD ──────┼─ SD       │       │
    └───────────┘           │      PGND
                            │
    C_boot 1µF: VB ── VS
    C_vcc: 1µF + 100nF from VCC to COM
    R_pd: 10k gate→source on BOTH Q1 and Q2
```

**Full part list for one leg:**

| Ref | Part | Connection |
|---|---|---|
| U | IR2184 | — |
| Q1, Q2 | IRF100B201 | high side, low side |
| C_boot | 1 µF 25 V | VB → VS |
| D_boot | ES1D (200 V ultrafast) | +12 V → VB, in series with R_boot |
| R_boot | 1 Ω | in series with D_boot |
| C_vcc1, C_vcc2 | 1 µF, 100 nF | VCC → COM, right at the chip |
| R_g1on, R_g2on | 10 Ω | HO → Q1 gate, LO → Q2 gate |
| R_g1off, R_g2off | 4.7 Ω | parallel with the above |
| D_g1, D_g2 | small signal diode | in series with each R_off, cathode to driver |
| R_pd1, R_pd2 | 10 kΩ | each gate → its own source |

**The two things people get wrong here:**

1. **`R_pd1` goes from Q1's gate to Q1's *source* (the switch node), NOT to ground.** The
   high-side FET's reference is the switch node. Same for `C_boot` — it goes VB to VS, not
   VB to ground. If you tie either to ground you've defeated the entire floating-supply idea
   from Part 5 of the first-principles doc.

2. **The turn-off diode points *toward the driver*.** Current takes the low-resistance path
   out of the gate on turn-off, and the high-resistance path in on turn-on.

### Then: mirror it

Copy the leg to make leg B. Second IR2184, `IN` → `PWM_B`, same `SD`. Both across the same
`VBUS`/`PGND`.

Coil path: `SW_A ──[SHUNT]── COIL_A ── (connector) ── COIL_B ── SW_B`

---

## 5. Order for the rest

Once the bridge is drawn, these are all independent — do them in whatever order you like:

| Block | Rough size |
|---|---|
| Bus network — 2× 470 µF, ceramics, TVS | 8 parts |
| Current sense — shunt, INA240, RC filter, 1.65 V ref | 10 parts |
| OCP — LM393 window comparator + 74HC74 latch + the §1.4 inverter | 12 parts |
| Bus-fault detector → both low FETs on | 6 parts |
| Aux rails — LM5164 60→12, LDOs to 5 V and 3.3 V | 15 parts |
| Connectors + input buffers (74HCT2G17) | 6 parts |

---

## 6. Start right now with this

1. **Create the KiCad project** and the four hierarchical sheets (§3)
2. **Open the IR2184 datasheet** to the Typical Connection diagram
3. **Draw the one half-bridge leg** from §4 — about 14 symbols
4. **Check three things** before going further:
   - `C_boot` goes VB → **VS**, not VB → ground
   - Q1's pulldown goes to the **switch node**, not ground
   - The IR2184 pin numbers match the **package drawing**
5. **Mirror it.** You now have a working H-bridge.

That's maybe 90 minutes and it's the hard part. Everything after it is bolt-on blocks you can
draw while tired.

**Message me when the leg is drawn** — I'll check it before you replicate the mistake twice.
