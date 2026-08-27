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
