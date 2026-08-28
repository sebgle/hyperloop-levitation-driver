# 21 — Stackup: copper weight, layer count, and why

**Decision date:** 2026-08-24
**Status:** decided and recorded. **Board Setup not yet reconfigured** — see §21.6.

---

## 21.1 A stackup bug found first

The board file carried **0.007 mm** copper on F.Cu and B.Cu. `14_power_channel_closeout.md`
records the intent as "copper 0.035 → 0.07 mm (2 oz)", so this was a dropped digit, not a
decision — 0.007 mm is not a copper weight that exists. Board total read 1.474 mm; with 0.07 it
comes to exactly 1.600 mm, which is what the design was aiming at.

It affects nothing already done — KiCad does not compute ampacity, so no DRC or clearance
result depended on it — but it propagates into fab outputs, and a fabricator reading the
stackup literally could have quoted 0.2 oz. At 0.007 mm the coil pours would have dissipated
**ten times** the intended power.

**Fixed** 2026-08-24 by direct file patch (KiCad closed): F.Cu and B.Cu → 0.07 mm, board total
1.474 → 1.600 mm. Core left at 1.44 mm.

> A first attempt at this patch also changed the core to 1.46 mm, which would have made the
> total 1.62 mm. Caught in the script's own printed output and reverted in the same session.
> The lesson is the cheap one: have the script print the number it computed, not just the
> number it wrote.

### What the copper is worth

```
sheet resistance (mohm/square)        20 C     70 C     85 C
  0.007 mm  (as the file had it)     2.463    2.947    3.092
  1 oz   (0.035 mm)                  0.493    0.589    0.618
  2 oz   (0.070 mm)                  0.246    0.295    0.309
  3 oz   (0.105 mm)                  0.164    0.196    0.206
```

---

## 21.2 The copper-loss picture

Coil-path loss at 30 A, on the 10.7 mm pours already placed, 2 oz, at 85 °C:

```
CH1 shunt -> J203    91.7 mm   8.57 sq   2.65 mohm   2.38 W
CH1 SW_B  -> J203    92.0 mm   8.60 sq   2.66 mohm   2.39 W
CH2 shunt -> J204    78.0 mm   7.29 sq   2.25 mohm   2.03 W
CH2 SW_B  -> J204    95.9 mm   8.96 sq   2.77 mohm   2.49 W
                                              TOTAL   9.30 W
```

With a via-stitched second copper layer in parallel:

```
+1 oz inner  (typical 4-layer)   6.20 W    saves 3.10 W   (33%)
+2 oz inner  (heavy 4-layer)     4.65 W    saves 4.65 W   (50%)
```

### The pour width is already correct

IPC-2221 external-layer sizing for 30 A at 2 oz:

```
dT = 10 C  ->  16.4 mm
dT = 20 C  ->  10.7 mm     <-- the width actually placed
dT = 30 C  ->   8.4 mm
dT = 45 C  ->   6.6 mm
```

The placed pours are exactly the ΔT = 20 °C width. Whoever sized them did it properly, and
**the copper-loss argument therefore does not justify four layers** — 3.1 W saved on a ~54 W
board, against pours that are already right.

---

## 21.3 The argument that actually decided it

**Four layers, 1 oz inner.** Four reasons, in order of weight.

**1. Choosing four now is free; choosing two and being wrong is not.** The placement is
identical either way — nothing already done is wasted. But if a 2-layer route ends with the
bottom pour shredded under the FET row, the remedy is not a tweak, it is a reroute. That
asymmetry settles the question on its own.

**2. The stackup geometry is doing work.** A standard 1.6 mm 4-layer puts thin prepreg
(~0.2 mm) between L1 and L2, with the thick core between L2 and L3. That places the ground
plane **0.2 mm** below the FET row instead of 1.44 mm away on the far side of a 2-layer board.
Loop inductance scales with that separation. This is the largest single benefit and it arrives
as a side effect of the stackup the fab builds by default.

**3. The current sense.** The protection scheme rests on a 0.5 mΩ shunt at 25 mV/A, amplified
×50, compared against thresholds sitting 224 mV below the top of the INA240's output swing. That
measurement must stay clean while 30 A commutates at ~0.5 V/ns centimetres away, and the
±45 A trip is the only thing between a fault and four destroyed FETs. A continuous plane under
that differential pair is cheap insurance on the circuit whose failure costs the most.

**4. The board composition is an unusually good fit.** 158 SMD footprints and 424 SMD pads
against **26 through-hole parts totalling 72 holes**. An inner plane here is nearly solid — close
to the full theoretical benefit, rather than a plane perforated into uselessness.

### The case against, recorded honestly

Two layers might well work, and the same SMD density that makes the inner plane good also means
less routing is forced to the bottom layer. The loss argument is genuinely weak. On a
cost-driven production run at volume, the 2-layer attempt should be made before spending the
money.

It is not that. It is a prototype whose foundational input — the coil — is still unmeasured, on
a design where the numbers have already moved three times. Margin gets bought where it is cheap.

**Rejected: 4-layer with 2 oz inner.** Halves coil loss to 4.65 W, but 2 oz inner layers are a
specialty order with a real cost step, to buy 4.6 W on a 54 W board. Revisit only if the thermal
budget turns out tight after the coil is measured.

---

## 21.4 Layer roles

| Layer | Copper | Role |
|---|---|---|
| **F.Cu** | 2 oz | Components, high-current pours, gate-drive loops |
| **In1.Cu** | 1 oz | **Solid GND plane. No routing, ever.** Unbroken under the FET row and the sense pairs — this is the thing being bought |
| **In2.Cu** | 1 oz | Paralleled high-current copper stitched to F.Cu, plus +60 V distribution |
| **B.Cu** | 2 oz | **The four 30 A coil pours**, plus logic and signal routing and GND fill stitched to In1.Cu. Amended 2026-08-24: see the note below |

> **Amended 2026-08-24, and this is a real change.** The coil pours were assigned to F.Cu. They
> cannot go there. Mapping every clear vertical channel on F.Cu, courtyards only, gives 5.80 mm
> in the band below the bridge, 8.30 mm through the logic blocks, 2.43 mm below them, and **no
> continuous channel of any width** from the bridge to the coil connectors. A 10.7 mm pour has
> nowhere to run. Necking one to the widest available 5.1 mm puts a 68 °C rise at 30 A right
> next to the current-sense amplifier.
>
> B.Cu is obstructed only by through-hole pads, 72 of them, and offers the full 159 mm width in
> both bands above the bulk row. The coil pours belong there, dropping through vias just after
> each shunt and landing at the connector, paralleled onto F.Cu wherever a channel exists. At
> 15 A per layer a 5.1 mm F.Cu run is only a 14.1 °C rise.
>
> In1.Cu then sits between the B.Cu coil currents and the F.Cu circuitry, shielding the sense
> amplifiers and comparators from 30 A passing underneath. That is a benefit of four layers
> nobody had articulated.
>
> Consequence: B.Cu logic gets routed **around** the pours, not the other way round. Signal
> demand is 3,126 mm of connection length, 5.6 % of one layer, against roughly 19 % for the
> pours, so there is room. The ordering has to be respected.


Target stackup, 1.60 mm total:

```
F.Mask    0.01
F.Cu      0.07     2 oz
prepreg   0.2      <-- keeps the GND plane close under the FET row
In1.Cu    0.035    1 oz
core      0.97
In2.Cu    0.035    1 oz
prepreg   0.2
B.Cu      0.07     2 oz
B.Mask    0.01
          1.60
```

**Confirm with the fab that 2 oz outer with 1 oz inner is available on 4 layers.** It is a
common combination, but some low-cost processes offer only 1 oz outer on 4-layer stackups, and
1 oz outer would **double** the pour losses to ~18.6 W. That would change the decision, not just
the quote.

---

## 21.5 Two constraints that fall out of the numbers

### The `HV_POWER` net class is a trap as configured

`HV_POWER` has a **3.0 mm track width** and its patterns cover `+60V`, `GND`, `*SW_*`,
`*COIL_*`, `*VB_*`, `*VBATT*`. A 3.0 mm track at 2 oz carrying 30 A gives, by IPC-2221, a
temperature rise of roughly **164 °C**. Three millimetres is 12 % of the required area.

**These nets must be routed as zones, never as tracks.** 10.7 mm of pour is the sized width.
The 3.0 mm class width is only safe for short stubs and for the genuinely low-current members
of the class — `*VB_*` is bootstrap, milliamps, and is in this class for its clearance, not its
width.

### Via stitching: the inner layer only helps if current can reach it

```
per-via current (25 um plating, IPC-2221 internal curve)
   0.3 mm drill    0.90 A @ dT=10 C     1.22 A @ dT=20 C
   0.4 mm drill    1.11 A @ dT=10 C     1.50 A @ dT=20 C
   0.6 mm drill    1.48 A @ dT=10 C     2.01 A @ dT=20 C

vias required to carry 30 A between layers
   0.3 mm drill    34 (dT=10)    25 (dT=20)
   0.4 mm drill    28 (dT=10)    21 (dT=20)
   0.6 mm drill    21 (dT=10)    15 (dT=20)
```

The `HV_POWER` via is already 1.2 mm / 0.6 mm drill, which is the right size.
**Budget 20 vias per 30 A layer transition** — dT = 10 °C with margin.

Sanity check: one 0.3 mm via, 1 mm long at 85 °C, is 0.919 mΩ; forty in parallel are 0.023 mΩ,
negligible against the 2.25–2.77 mΩ pours. Vias are a thermal limit here, not a resistive one.

---

## 21.6 Not yet done

Board Setup has **not** been reconfigured. Remaining:

1. Board Setup → Physical Stackup → **Copper Layers: 4**, then enter the §21.4 thicknesses.
   (F.Cu and B.Cu are already 0.07 from the §21.1 fix; the inner layers and dielectrics are new.)
2. Board Setup → Board Editor Layers → set **In1.Cu** and **In2.Cu** type to **power**.
3. Net classes: address the `HV_POWER` width trap per §21.5.
4. Confirm 2 oz outer / 1 oz inner with the fab.

---

## 21.7 Routing order

Deliberate: the loops that determine whether the board works get the copper first; the signals
that merely need to arrive get routed around them.

1. **Commutation loops** — bridge ceramics to FET drains and sources. Shortest, fattest, on
   F.Cu. Everything else routes around these.
2. **Gate loops** — gate and return as a tight pair per FET, over In1.Cu. These decide whether
   the FETs switch cleanly. The **low side** returns through the ground plane and closes its own
   loop. The **high side** returns through VS, a routed net on a node slewing at 0.5 V/ns, so HO
   and VS must be drawn as a deliberate pair or the loop area becomes whatever the router chose.
3. **Sense pairs** — Kelvin connections from the shunts to the INA240s, over unbroken plane,
   no crossings.
4. **High-current pours** — **coil pours on B.Cu**, paralleled onto F.Cu where a channel
   exists, 20 vias per transition. The +60 V bus zone on F.Cu paralleled onto In2.Cu.
   See the amendment in §21.4: F.Cu has no continuous channel wide enough for a coil pour.
5. **Bulk to bridge** — the ~81 mm feed.
6. **Logic and signals** on B.Cu, routed around the coil pours. `SD` is the fault shutdown
   line, sits at 767 Ω, and runs 45 mm past the bridge: keep it over the plane and away from any
   switching node.
7. **GND fill and stitching**, then DRC.

---

## 21.8 The coil pours as built

Drawn 2026-08-27. All four are on B.Cu, one polygon each, plus a small F.Cu landing zone
on each A leg. Measured with `tools/pour_check.py`, which rasterises the real outline at
0.05 mm rather than trusting its bounding box.

| Net | Narrowest cut in the conductor | dT at 30 A | Closest foreign copper |
|---|---|---|---|
| `/COIL_A1` | 11.00 mm | 19 C | 0.800 mm to H1 |
| `/COIL_A2` | 11.00 mm | 19 C | 0.800 mm to H2 |
| `/COIL_B1` | 10.70 mm | 20 C | 0.331 mm to Q4.3 [GND] |
| `/COIL_B2` | 10.70 mm | 20 C | 0.337 mm to Q203.2 [+60V] |

IPC-2221 external, 2 oz, `I = 0.048 * dT^0.44 * A^0.725`, A in mil^2. The 10.7 mm the
project sizes to is 20.3 C, not 20.0, which matters only because a checker comparing against
a computed 20 C flags the very width it is supposed to bless.

### The two legs are not built the same way, and the reason is the shunt

The A legs terminate on R11 and R219, which are surface mount. A pour on B.Cu cannot touch a
front pad, so each A leg needs a front landing zone off the shunt and a via field down to the
back: **15 vias at 2.0 A each on CH1, 19 at 1.58 A on CH2**, HV_POWER size, 1.2 mm pad on a
0.6 mm drill.

The B legs terminate on Q3/Q4 and Q203/Q204 and on the yoke connectors, all through-hole, so
the pour reaches every one of them down its own barrel. **No vias at all.**

That asymmetry is worth stating plainly because it looks like an inconsistency and is not: it
is the difference between a surface-mount current-sense resistor and a TO-220 lead.

### The fence at each TO-220 row

Pins sit on 2.54 mm pitch, and on both B legs each coil pin has a foreign neighbour 0.64 mm
away -- a gate on one side, a rail pin on the other. A single rectangle over the row would
enclose the gate pin and both rail pins, stranding each as a 0.3 mm island inside a node that
swings the full bus every cycle.

Both B pours instead stop below the row and send two narrow lobes up to the coil pins only.
No foreign pad ends up inside any coil pour on this board. The copper arriving at each pin is
then about 1.9 mm wide, which is the pad. **A TO-220 lead is the constriction and no pour
geometry can widen it** -- 4.7 to 5.0 mm total across both lobes, and `pour_check` now
recognises a cut that lands on the net's own pads and says so rather than calling it a neck.

### CH2's A leg is fenced too, and that one is a placement consequence

R11 sits at 180 degrees and R219 at 0, so the two shunts are 180-degree rotations of each
other rather than mirror images. Each block is internally consistent, tap and filter and
amplifier pin all on the same side, so nothing looks wrong until you try to take 30 A off the
pad:

```
R11.4  /COIL_A1  x[105.35,108.65] y[64.85,66.88]   open space directly above
R219.4 /COIL_A2  x[251.33,254.63] y[66.12,68.15]   SNS_N sits 0.51 mm above it
```

CH1's coil pad faces an empty band. CH2's is fenced by its own Kelvin tap, so its F.Cu zone
has to notch around SNS_N, and the current crosses that fence through two channels totalling
6.45 mm over a 1.36 mm length. Short constrictions between large copper areas are governed by
spreading rather than by the steady-state IPC curve, so the real rise is well under what
6.45 mm of continuous trace would give, but it is the one place where CH2 is worse than CH1.

The clean fix is rotating R219 to match R11, which drags R210, R211 and U203 with it to keep
the sense pair uncrossed. That is a block rework for a 1.4 mm constriction, so it is recorded
rather than done.

### What measurement caught that drawing did not

The pours were first built as overlapping rectangles, then redrawn by hand as single
polygons. The redraw was right everywhere that was hard -- both lobe pairs survived, no
foreign pad was enclosed, all 34 vias stayed inside their zones on both layers, and
`COIL_A1_F` came out better than the rectangle it replaced because its staircase swallows
R11 pad 4 whole instead of clipping its edge.

What it got wrong was one horizontal edge on each B leg landing at y=134 instead of 138.2.
That made both bands **6.50 mm where they needed 10.7**, held for 33 mm on CH1 and 27 mm on
CH2, for a 46 C rise. Invisible on canvas. Obvious the moment something measured it.

`lay.py` could not have caught it: its zone check treats a zone as its bounding box, which is
exact only while zones are rectangles. `pour_check.py` exists because that assumption died
the moment the pours became polygons.

### Still open on these nets

`U2.6`, `C16.2`, `R6.1` and `U207.6`, `C226.2`, `R224.1` -- the high-side drivers' VS
references, their bootstrap capacitors and a gate resistor each. All surface mount, none
carrying coil current. They are a routing job, and DRC will keep listing the coil nets as
unconnected until it is done.

---

## 21.9 Planes are not traces, and A17 was computing the wrong one

A17 said the bulk-to-bridge feed needs 28.0 mm and concluded the 13 mm corridor could not carry
it. That number came from the IPC-2221 trace formula. The feed is not a trace.

Push the same formula onto In2.Cu at 1 oz and it asks for **146 mm** of width for 60 A at
dT = 20 C. The board is 160 mm wide. When a formula demands the entire board, the honest
reading is that it is being asked a question it was not calibrated for: it models a narrow
conductor losing heat to the laminate around it, and a plane is its own heat spreader.

### Count squares instead

```
1 oz copper   0.494 mOhm / square          2 oz copper   0.247 mOhm / square

cap row y=143 to bridge row y=62     81 mm long, about 150 mm wide
                                     0.54 squares  ->  0.267 mOhm
                                     16 mV and 0.96 W at 60 A

spreading at one bulk cap pad        a = 1.2 mm, b = 8.5 mm   0.154 mOhm
  six of them in parallel                                     0.026 mOhm
spreading at one FET drain pin       a = 0.98 mm, b = 8 mm    0.165 mOhm
                                     5 mV and 0.15 W at its own 30 A

end to end                           about 0.46 mOhm
                                     27 mV and 1.65 W at 60 A
                                     0.14 mW/mm2 over 150 x 80 mm
```

Two orders of magnitude below what a board dissipates comfortably. The corridor width was never
the constraint. What matters for a plane is that it stays a plane.

### Which is why In2.Cu still carries no signals

The original reason stands and is now the only reason: a route across In2.Cu cuts the plane, and
a cut plane forces the current around it. That is how a plane turns back into a trace, and the
trace numbers really are as bad as A17 first suggested.

### The power path needs no vias

Every +60 V pad that carries current is through-hole:

```
Q1.2  Q3.2  Q203.2  Q201.2       FET drains, y = 62
C101.1 ... C106.1                bulk caps,  y = 143
J101.1                           bus input,  (153.5, 182.5)
```

So an In2.Cu plane reaches all eleven down their own barrels. Vias are needed only to bring the
surface-mount bridge ceramics on F.Cu onto the plane, and those carry ripple, not bus current.

### The In2.Cu split, and why the bottom of the board is not +60 V

The stackup is F.Cu / In1 GND / In2 +60V / B.Cu, so B.Cu's nearest plane is In2. Over the power
section that is fine: the bus is an AC ground, bypassed by six bulk caps and by the interplane
capacitance of In1 against In2 (about 0.9 nF across the 0.97 mm core).

Under the IO connectors it is not fine. J202 carries the PWM inputs, the enable lines and the
two current-sense outputs off the board, and those are the signals whose reference quality
matters most. So In2 is split: **+60 V above y = 150 plus a finger down to J101, GND below it.**
The finger runs x 146 to 162, which clears J202's leftmost pin at x = 169 by 7 mm.

A split plane is a hazard wherever a signal crosses the split. Nothing crosses it yet. Anything
routed on B.Cu across y = 150 between x = 143 and x = 165 later will need a return path checked
by hand.

