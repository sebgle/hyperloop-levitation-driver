# 20 — PCB layout phase: placement, review, and the CH2 leg swap

**Status:** placement complete and verified. Routing not started.
**Board:** 160 × 140 mm, outline (100,50)–(260,190), 184 footprints.
**DRC:** clean except unconnected items (expected — nothing is routed).

---

## 20.1 Why the board grew from 160 × 100 to 160 × 140

The bulk capacitor bank did not fit.

C101–C106 are Rubycon ZLH 470 µF / 100 V in Ø16 × 31.5 mm cans
(`100ZLH470MEFC16X31.5`), six of them, and the plan was to sit them between the two coil
connectors. They did not fit, and I did not catch it because **I was checking pad extents
instead of courtyards.**

That is worth recording as a method error, not just an outcome. The Molex 38969-0002 coil
connector has a courtyard of 26.6 × 29.9 mm — far larger than the region its pads occupy. On
pad extents alone, J203 and J204 read as "clear" with room between them. On courtyards they
do not. I declared the placement feasible on the wrong measurement, and Sebastian caught it
from the canvas before I did.

The clearance checker was rewritten to read `F.CrtYd` geometry — `fp_line`, `fp_poly`,
`fp_rect` **and** `fp_circle` (centre + end → radius, which is how KiCad stores the courtyard
of a radial electrolytic). Every clearance number in this document comes from that path.

Board grew to 140 mm tall. The bulk row now sits below the connectors at y = 150 on roughly
17 mm pitch, x = 134…218.

---

## 20.2 Floorplan

```
y  50– 59   heatsink shadow (extrusion covers x 122..243, face at y ~= 58.6)
y  59– 71   FET row (y=62) + bridge ceramics (y=66) + 100nF (y=69.5)
y  71– 93   gate networks, drivers (y=77), bootstrap (y=88), sense clusters
y  96–135   CH1 logic (x 108–160), CH2 logic (x 173–225, = CH1 + 65)
y 141–158   bulk cap row, y=150, ~17 mm pitch, x 134..218
y 158–190   J101, J202, J201, IO passives
edges       J203 (107.5, 157.5 rot 90), J204 (252.775, 145.166 rot -90)
```

### The FET ordering is thermal, not electrical

Under unipolar 3-level PWM at the D = 0.75 design point, conduction splits 3:1. Q1 (leg A
high side) and Q4 (leg B low side) conduct 75 % of the period **and** take all of the hard
switching. Q2 and Q3 conduct 25 % and switch at zero volts.

So two devices per channel run hot and two run cool, and they are placed to alternate:

```
CH1   Q2 (cold)  Q1 (hot)  Q3 (cold)  Q4 (hot)      x = 125, 140, 155, 170
CH2   Q202(cold) Q201(hot) Q203(cold) Q204(hot)     x = 190, 205, 220, 235
```

C-H-C-H, so no two hot devices share a heatsink segment. This ordering is a constraint on any
future re-placement, not an accident of layout.

---

## 20.3 Verified placement metrics

All measured from `final_lev.kicad_pcb` geometry, not from screenshots.

| Metric | Value |
|---|---|
| Courtyard overlaps | **0** across all 184 footprints |
| Commutation loop, CH1 leg A | 17.7 / 17.8 mm (two nearest ceramics) |
| Commutation loop, CH1 leg B | 16.7 / 16.8 mm |
| Commutation loop, CH2 leg A | 17.7 / 17.8 mm |
| Commutation loop, CH2 leg B | 16.7 / 16.8 mm |
| Gate turn-off loop | 19.6 – 27.4 mm, identical on both channels |
| Bootstrap cap → VB/VS | 3.3 – 6.4 mm |
| Sense pair routing | no crossing; 2.5 mm P/N length mismatch |
| Closest HV ↔ LV approach | 2.88 mm |
| Heatsink shadow intrusions | none |
| Mounting hole keepouts | 12 – 28 mm |
| Closest footprint → outline | J204 at 0.175 mm |

**Loop metric, stated explicitly**, because figures under a different definition were quoted
earlier in this project and the two are not comparable: the number is a **two-segment path
length** — high-side drain pad to the ceramic's +60 V pad, plus the ceramic's GND pad to the
low-side source pad. It is not a closed-loop perimeter and it does not include the ceramic's
own internal path or via inductance. All four figures are produced by `tools/lay.py`.

### Known cost, accepted for now

Copper loss on the coil and bus runs at 30 A on a 10.7 mm pour:

```
CH1  shunt -> J203        91.7 mm    ~1.9 W
CH1  SW_B  -> J203        92.0 mm    ~1.9 W
CH2  shunt -> J204        78.0 mm    ~1.6 W
CH2  SW_B  -> J204        95.9 mm    ~2.0 W
     bulk cap -> bridge drain  ~81 mm
                          total     ~8.7 W
```

Reducing this means restructuring the floorplan — roughly 50 further part moves — and it
trades against the connector positions, which are set by the mechanical interface. Recorded
as a known cost rather than an oversight. Revisit if the thermal budget tightens after the
coil is measured.

---

## 20.4 The one structural defect found: CH2's SW_A run

CH2 was built as an exact +65 mm copy of CH1's FET row. That is the right instinct for two
identical channels and it is wrong here, because **the coil connectors are mirrored** — J203
sits to the *left* of CH1, J204 sits to the *right* of CH2.

Consequence: CH1's leg A is adjacent to its shunt (R11) and connector. CH2's leg A is as far
from J204 as the board allows. Its SW_A node — 0 to 60 V, slewing at roughly 0.5 V/ns — has
to cross leg B's high-current territory to reach the shunt at x ≈ 248.

**The fix is to swap leg A and leg B within CH2**, making CH2 a true mirror of CH1 rather than
a translation of it. Leg B moves −30 mm in X, leg A moves +30 mm in X. Y and rotation are
unchanged on every part, because each leg keeps its internal low/high ordering.

### Verified before recommending

| | before | after |
|---|---|---|
| CH2 SW_A net span | 55.6 mm | **25.8 mm** |
| CH2 Q201 pad 3 → R219 pad 1 | ~38 mm | **7.94 mm** |
| CH2 COIL_B2 net span | 97.0 mm | 105.8 mm |
| sum of the two | 152.6 mm | **131.6 mm** |
| courtyard overlaps | 0 | **0** |
| CH2 leg A commutation loop | 17.7 mm | **17.7 mm** |
| CH2 leg B commutation loop | 16.7 mm | **16.7 mm** |
| thermal order | C-H-C-H | **C-H-C-H** |
| heatsink shadow intrusions | none | none |
| closest moved part → M3 hole | — | 12.73 mm (Q201 → H2) |
| closest moved part → outline | — | 8.60 mm |

COIL_B2 gets 8.8 mm longer. That is the honest cost. It buys a 30 mm reduction on SW_A and,
more importantly, removes the crossing: after the swap COIL_B2 runs down open board to the
connector, which is structurally identical to what CH1 already does (COIL_B1 spans 97.8 mm).
The commutation loops do not change at all.

**Correction.** When this was first reported in chat I said the two legs "trade" loop values,
17.7 ↔ 16.7. That was a misreading of my own output. The loops are **unchanged**, and they
have to be: the ceramics move with their blocks and land on each other's coordinates, so each
leg finds a ceramic at exactly the same distance as before. Same reason the board comes out
identical whether the ceramics are included in the selection or not. The corrected figures are
in the table above and are reproducible with `tools/lay.py`.

### Two findings that made the edit safe

**1. Every leg-local net is fully contained in its block.** Audited from the netlist:

```
/CH2/G_Q1  G_Q2  HO_A  LO_A  VB_A   -> 100% inside leg A
/CH2/G_Q3  G_Q4  HO_B  LO_B  VB_B   -> 100% inside leg B
/CH2/SD                             -> spans both (logic net, both drivers)
/CH2/SW_A                           -> touches R219, the shunt, which does not move
```

So the gate loops and bootstrap loops translate rigidly and do not change at all. If any
gate resistor or bootstrap part had been left outside its block, the move would have silently
stretched a gate loop.

**2. The bridge ceramics inside each block are spaced exactly 30 mm apart.**

```
C212 192.5   C214 198.5   C215 204.5   C216 210.5   C217 201.5
C219 222.5   C220 228.5   C221 234.5   C222 240.5   C223 231.5
```

Every pair differs by exactly +30.0 mm. They are +60 V → GND bus decouplers, common to both
legs, so they are not associated with a leg electrically — and because they are spaced at the
shift distance, moving them with their block lands them precisely on each other's old
coordinates. The resulting board is identical either way, which means they can be included in
a blind window-select instead of being carefully excluded. That turns a 32-part hand-pick into
two rubber-band drags.

---

## 20.5 J203 outline violation — resolved

J203's courtyard left edge sat at x = 99.950 against a board edge of x = 100.000: 0.050 mm
**outside** the outline. Resolved by moving J203 from x = 107.0 to x = 107.5 (y snapped to
157.5, rotation 90 unchanged). Left margin is now 0.450 mm. J204's right margin is 0.175 mm.
Both inside, zero courtyard overlaps board-wide.

---

## 20.6 Process notes carried forward

- **No file surgery while KiCad is open.** A reference designator was renamed externally
  while the editor held the file; the next save from KiCad overwrote it. All external patching
  is now batched to periods when the editor is closed.
- **Check courtyards, never pad extents.** See 20.1.
- **KiCad multi-instance hierarchy**: per-instance reference designators live in
  `(instances (project ... (path "<uuid>" (reference "X") (unit N))))`. Both the reference
  *and* the unit field must be patched, and a uniqueness check must key on `(ref, unit)` —
  multi-unit parts legitimately repeat their reference across units.
- **KiCad transform**: `a = radians(-ang); out = (x + lx·cos a − ly·sin a, y + lx·sin a + ly·cos a)`.
- **Pad net syntax in this file** is `(net "NAME")` with no net number.

---

## 20.8 Leg-A bridge ceramic orientation

Found 2026-08-24 while laying out the CH1 leg A commutation loop, before any copper was
placed.

The C-H-C-H thermal ordering in §20.2 forces the two legs into opposite pin orders:

```
leg A:  Q2 (low)  then Q1 (high)   ->  GND  at x = 130.08,  +60V at x = 142.54
leg B:  Q3 (high) then Q4 (low)    ->  +60V at x = 157.54,  GND  at x = 175.08
```

Leg A therefore wants +60 V on its **right**; leg B wants it on its **left**. Every bridge
ceramic was placed at 0°, which puts pad 1 (+60V) on the left — correct for leg B, backwards
for leg A. Nobody chose this: it is the library default orientation meeting a constraint that
came from thermals.

| | before | after |
|---|---|---|
| CH1 A loop | 17.72 / 17.79 mm | **12.89 / 13.08 mm** |
| CH2 A loop | 17.72 / 17.79 mm | **12.89 / 13.08 mm** |
| CH1 B loop | 16.73 / 16.81 mm | 16.73 / 16.81 mm |
| CH2 B loop | 16.73 / 16.81 mm | 16.73 / 16.81 mm |
| board worst-case loop | 17.79 mm | **16.81 mm** |
| courtyard overlaps | 0 | **0** |
| heatsink-shadow intrusions | none | none |

**27 % off leg A for a rotation.** Ten parts — C3, C5, C6, C7, C8 and C212, C214, C215, C216,
C217 — 0° → 180°. X, Y, nets and courtyards unchanged; pad 1 keeps net `+60V` and simply lands
on the other side of the body. Leg B’s ceramics (C11–C15, C219–C223) stay at 0°, where
rotating them would make things worse: 16.73 → 22.26 mm.

Applied by `tools/rot_ceramics.py --write` with KiCad closed. 80 lines changed of 59,584.

### The file format was established, not assumed

A 0 → 180 rotation was not guessed at. It was derived by diffing U1 (0°) against U2 (180°) —
the same SOIC-8 footprint, in this same board file:

```
U1   (at 132.5 77)       Reference (0 -3.5 0)    fp_text ${REFERENCE} (0 0 90)
U2   (at 162.5 77 180)   Reference (0 -3.5 180)  fp_text ${REFERENCE} (0 0 270)
```

So KiCad adds the angle to the footprint’s own `(at)` and adds 180 to the angle field of every
`(at)` inside a `property` or `fp_text` sub-block, leaving local offsets, pads and graphics
alone — 8 `(at)` lines per capacitor here. Patching only the footprint angle would have left
these ten silkscreen designators stored differently from every other rotated part on the board.

### The check lives in the tool

`rot_ceramics.py` refuses to run while `~final_lev.kicad_pcb.lck` exists, so the "no file
surgery while KiCad is open" rule is enforced rather than remembered. It reads and writes
bytes, so CRLF survives. After patching it re-parses **its own patched buffer**, recomputes all
four commutation loops and the full 184-footprint courtyard check from the patched geometry,
and writes nothing unless those agree. The numbers it prints are the ones it computed.

---


### The library-mismatch warning it produced, and what that turned out to be

After the rotation, DRC reported ten `lib_footprint_mismatch` warnings, and the flagged list was
exactly the ten rotated parts: C3, C5, C6, C7, C8, C212, C214, C215, C216, C217. None of the
untouched 1210s — C12–C15, C219–C222 — appeared.

That looked conclusive, and it was wrong. The rotation was redone in the KiCad GUI (Orientation
0 → save → Orientation 180 → save) and the ten warnings persisted. Diffing each footprint block
before and after that GUI round trip: **identical, to the byte.**

So the file patch and the editor converge on the same board. The warning is not an artefact of
external editing — it is what KiCad 10 reports for these capacitor footprints at 180°, and it
would have appeared identically had the rotation been done by hand from the start.

The geometry was verified against the actual library file from this machine
(`Capacitor_SMD/C_1210_3225Metric_Pad1.33x2.70mm_HandSolder.kicad_mod`, same `(version
20260206)` as the board). Compared as parsed S-expressions rather than as text, the only
differences are the board placement coordinates and the Reference text offset — and C13, which
differs from the library in *both* Reference offset values and is **not** flagged, rules that
out as the trigger. Pads, courtyard rect, F.Fab rect, both silk lines, `attr` and the 3D model
path are identical.

**Conclusion: cosmetic, cause not isolated, geometry confirmed identical.** Severity set to
Ignore, with this note as the reason. What must *not* be done is **Update Footprints from
Library** — it would replace the board footprints wholesale, and every clearance and loop figure
in this document is measured from that geometry.

### A correction, and then a correction to the correction

This section first claimed the tool "reproduces exactly what the KiCad GUI writes". That was
retracted when KiCad was seen rewriting the patched text-field offsets on save — `(at 0 2.5
180)` came back as `(at 0 -2.5 180)`. The retraction was itself too broad: KiCad normalises
those offsets on load, and after one save cycle the file is byte-identical to the GUI result.
Both statements stay on the record because both were made.

The durable lesson is narrower than "don’t patch files": **a claim about file format is worth
only what a round trip through the application proves.** The patch was correct. The check that
would have shown it was correct — reopen, save, diff — was not run at the time.

---

## 20.7 Open after this phase

| Item | Note |
|---|---|
| ~~2 layers vs 4 layers~~ | **Settled 2026-08-24: four layers, 1 oz inner.** Reasoning in `21_stackup_and_layers.md`; Board Setup reconfigured. |
| ~~CH2 leg swap~~ | **Applied and verified 2026-08-24.** `/CH2/SW_A` 55.6 → 25.8 mm. |
| Coil L, R, k | Still unmeasured. Everything thermal depends on it. |
| §4.1 thermal numbers | Still derived under locked antiphase; must be redone under unipolar. |
| Bus-fault detector §3.2 | Undesigned. |
| ~8.7 W coil/bus copper loss | Known cost, see 20.3. |

The layout is in the same position the schematic was: structurally sound, and resting on a
coil measurement nobody has taken yet.
