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

> **Superseded 2026-08-27 by 20.11.** The conclusion reached in this section, that the
> `lib_footprint_mismatch` warnings were unexplained and safe to ignore, was wrong. The
> warning was correct and the cause is isolated in 20.11. Everything else in this section
> stands. It is left in place because the reasoning that produced the wrong call is the
> point of keeping it.

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

## 20.9 Block-by-block placement review

**2026-08-24.** Placement had been called complete and verified, and it was, on the six things
`lay.py` measured. A remark from outside the project ("the filter capacitors for the I/O should
be close to the pins") found a whole category the checker was blind to. Rather than re-place the
board, the eight functional blocks were walked one at a time: what each is for, what the file
measures, whether it meets the intent.

`lay.py` was extended first with eight new checks, so the review's findings are reproducible
rather than anecdotal. See the PLACEMENT CHECKS section of that script; its thresholds are named
constants with the reasoning above them.

### What each block came to

| Block | Verdict |
|---|---|
| 1 bridge | Meets intent. Loops 12.9 / 16.7 mm, FET bodies flush on the heatsink face, thermal order preserved |
| 2 gate drive | Meets intent. Loops 32.9 to 37.4 mm, channels matched within 0.4 mm, bootstrap 10.3 to 10.8 mm |
| 3 current sense | One finding: `C211` on the wrong side of `U203` |
| 4 protection | Six findings: every capacitor around both comparators |
| 5 logic and MCU | One finding: `R238` |
| 6 bus and bulk | No findings. Bulk bank within 1.9 mm of uniform. Two open questions |
| 7 coil paths | **Structural.** The coil pours cannot go on F.Cu |
| 8 mechanical | Sound. One stale register entry, A11 |

### The pattern worth naming

Four separate findings were the same underlying mistake: **a block mirrored for CH2 where one
part kept CH1's geometry.** The bridge ceramics facing the wrong way (§20.8), `C211` left above
a package that had been rotated 180°, `R238` translated with the block instead of mirrored with
it, and the CH2 leg order itself (§20.4). Anything added to this board should be checked against
that first.

### Moves applied

Eight parts, by `tools/place_caps.py`, from the decoupling failures:

```
C20  -> U3.6      58.17 mm -> 2.36      C213 -> U203.6   38.95 -> 2.34
C1   -> U1.5       6.26    -> 2.76      C2   -> U1.5      4.31 -> 2.19
C227 -> U206.5     6.26    -> 2.76      C228 -> U206.5    4.31 -> 2.19
C209 -> J202.15   19.89    -> 2.37      C210 -> J202.16  28.60 -> 2.43
```

Eight more by `tools/place_review.py`, from the block walk:

```
C211 -> U203.8     7.05 mm -> 3.41      R238 -> U207.1   46.87 -> 26.57
C25  -> U4.3       5.56    -> 2.39      C235 -> U204.3    5.56 -> 2.31
C26  -> U4.6      12.78    -> 2.39      C237 -> U204.6   12.78 -> 2.31
C27  -> U4.2      10.46    -> 2.62      C239 -> U204.2   10.46 -> 3.12
```

`lay.py` placement checks went **7 FAIL / 16 warn** to **1 FAIL / 10 warn**. The remaining
failure is the absence of test points; the remaining warnings are supply pins in the 3.8 to
5.3 mm band and the two `/RESET` time-constant capacitors, which the checker cannot distinguish
from noise filters and therefore reports rather than grades.

Courtyard overlaps stayed at 0 and the commutation loops stayed at 12.9 / 16.7 mm through both
batches.

### Things checked that turned out fine, recorded so nobody checks them twice

- The 81 to 93 mm PWM runs from buffer to driver need no series termination. Round-trip delay
  1.12 ns against a 2 ns edge; reflections settle inside the edge.
- The 3.3 V buffers drive the IR2184 inputs with 0.6 V of margin. VIH is 2.7 V minimum and the
  part is specified 3.3 V logic compatible.
- The 45 mm shutdown run at 767 Ω picks up about 38 mV from a 0.5 V/ns neighbour through a
  plausible 0.1 pF. Nowhere near a logic threshold.
- All six bulk electrolytics share one polarity orientation, which is a deliberate assembly
  safeguard.

### Open, and belonging to somebody else

The TVS clamps sit 70 mm from the bus connector and 53 mm from the bridge, and the bridge has no
room for them: respecting the heatsink shadow and every courtyard, the closest either can get is
27.5 and 37.2 mm. What they are for should be settled before spending a rearrangement on them.
Separately, this board has no surge protection where the harness lands.

Bleed timing, for anyone about to probe it: 62 second time constant, below 50 V in 11 seconds,
below 5 V in two and a half minutes, 5.1 J stored at 60 V.

---

## 20.10 Test points

Thirteen test points were added to the schematic and placed on 2026-08-27. Before this the
board had nowhere to put a probe, and adding probe points after routing means ripping up
copper to make room for them.

| Ref | Net | Why it is there |
|---|---|---|
| TP201 / TP202 | `/ISNS1`, `/ISNS2` | The amplifier output. This is the one signal that has to be believed, because the overcurrent trip is derived from it. |
| TP203 / TP204 | `/CH1/SD`, `/CH2/SD` | Shutdown. Tells you whether the driver was commanded off or fell over on its own. |
| TP205 / TP206 | `/CH1/FAULT_N`, `/CH2/FAULT_N` | The latch output. Says a fault was captured even after the event has passed. |
| TP207 / TP208 | GND | Ground reference for the six signals above, one per channel. |
| TP209 / TP210 / TP211 | +12V, +5V, +3.3V | Rail check at the regulators, not at a load. |
| TP212 | GND | Ground reference for the three rails. |
| TP213 | GND | Bridge-side ground, in the clear channel between the two channels. |

### Ground first, then signals

The placement rule was that a signal measurement is only as good as its ground reference, so
the three ground points were placed first, against the part each group serves, and the signal
points were clustered around **their own ground** rather than against the net they measure.
A 6 mm trace out to a test point costs nothing on these signals. A 60 mm probe ground lead
turns a clean edge into ringing that is not on the board.

Worst signal-to-ground distance came out at 7.50 mm (TP205), against a limit of 8.0 mm written
into the tool. Every other pair is under 6.5 mm.

### What the first solve got wrong

TP213 landed at (134.6, 62.0), in the 4.5 mm gap between Q2 and Q1 — geometrically legal,
under the heatsink extrusion, and impossible to reach with a probe hook. The same solve also
scattered each channel's ground as far as 45 mm from the signals it was supposed to reference,
which defeats the entire point of having it. Both came from optimising distance-to-net instead
of distance-to-ground, and from a keepout list that had the heatsink shadow but not the
question "can a hand get here."

Re-solved with grounds placed first. TP213 now sits at (183.25, 70.0), in the open channel
between the channels.

### Keepouts the search respected

Courtyards and the board edge, the heatsink shadow, and the four 10.7 mm coil-pour corridors
on B.Cu. That last one matters because these are through-hole wire loops: a barrel dropped in
a corridor punches a hole through a pour that has to carry 30 A.

### One silkscreen collision, fixed by moving the label

TP204 and TP208 sit 3.72 mm apart and both inherited the library's default reference position
at (0.7, 2.5), which put their labels 3.60 mm apart in x against a 3.75 mm text width. TP204's
label moved to (-2.6, 0), to the left of the loop. Nothing electrical moved. `check_silk` now
reports zero overlapping pairs.

### State after

`tools/place_testpoints.py`, dry run then `--write`, backup to `final_lev.kicad_pcb.bak1`.

```
test points patched  : 13
silk labels moved    : 1  TP204
line endings         : CRLF 62554 -> 62554   bare LF 0 -> 0
courtyard overlaps   : 0
```

`tools/lay.py`: **0 FAIL, 10 warn**, down from 1 FAIL / 10 warn. Commutation loops unchanged
at 12.9 / 13.1 / 16.7 / 16.8 mm, heatsink shadow still clear, 197 footprints.

### A12 corrected as a consequence

Pushing the test points to the board produced `No net found ... no pin 1 in symbol` on H1-H4.
My first answer, that the holes are plain unplated-net holes with no pad and no net, was
**wrong**, and is corrected here. They are `MountingHole_3.2mm_M3_Pad`: a plated 3.2 mm hole
with a 6.4 mm pad on all four copper layers, carrying no net. The warning comes from the
symbol, which has no pin for the pad to take a net from. The A12 row had separately claimed a
0 Ω 1206 chassis-bond jumper fitted DNF; that part does not exist in the netlist and never
did. A12 now records both facts and the real fix, which is a symbol swap rather than a re-spin.

The wrong answer came from a parser of mine that searched for `(net <number> "NAME")`. This
file writes `(net "NAME")` with no number, on all 506 pads. The regex matched nothing, returned
an empty list, and I read empty as *absent* instead of *unmatched*. Same failure mode as 20.8
and as the first version of `check_pad_orientation`: my own tool's silence was taken as
evidence. Every parser here should assert that it matched something before anyone believes
what it did not find.

---

## 20.11 The footprint-mismatch warning was real, and 20.8 was wrong about it

`§20.8` looked at KiCad's `lib_footprint_mismatch` warnings, checked the geometry against the
library, found it identical, failed to isolate a cause and set the severity to Ignore. That was
the wrong call, and this section replaces it. The warning was accurate. Something in those
footprints genuinely did not match the library, and it was not cosmetic.

### What the DRC report actually contained

Run 2026-08-27 13:47 on KiCad 10.0.5, two separate things:

| Kind | Count | Meaning |
|---|---|---|
| `unconnected_items` | ~300 | The board has 0 tracks, 0 vias and 1 zone, so every connection is unrouted. This is the routing to-do list, not a fault. It also confirms the netlist pushed cleanly: every pad carries the net it should. |
| `lib_footprint_mismatch` | 18 | All capacitors. This one was real. |

### The defect

A pad's `(at x y angle)` in this file is the pad's **absolute** angle, so a body rotated to 90
normally has its pads written at 90. Twenty footprints did not follow their body:

```
C1  C20  C227  C213  C239        pads 90 deg off  -> the 1.175 x 1.450 mm pad turned across the part
C3  C5  C6  C7  C8  C210
C212 C214 C215 C216 C217
C235  C237                       pads 180 deg off -> same rectangle, cosmetic
```

Off by 180 a rectangle is unchanged. Off by 90 the pad's length and width swap and the copper
stops matching the part's terminations. Five parts were in that state, and they would have been
fabricated that way.

Cause: `rot_ceramics.py`, `place_caps.py` and `place_review.py` all rewrote a footprint's `(at)`
line and left its pads behind. Every footprint KiCad itself rotated on this board obeys the rule
(C19 at 180 with pads at 180, C25/C26/C27 and C203 at 90 with pads at 90, D1 at 180 with pads at
180), which is the in-file evidence for what the convention is.

### The fix

Pcbnew, **Tools -> Update Footprints from Library**, all footprints, field-reset boxes left
unchecked. KiCad rewrote each footprint body from the library at its existing position and
orientation. No footprint moved or rotated: 197 before, 197 after, all 197 at identical
coordinates. The only other change was 23 reference-designator label positions, which KiCad
re-placed itself, and that incidentally resolved the TP204 / TP208 silkscreen overlap that
`place_testpoints.py` had hand-fixed. `check_silk` still reports 0 overlapping pairs.

### The check, and the mistake inside the first version of it

`lay.py` gained `check_pad_orientation`. Its first version assumed a pad's angle should equal its
body's angle, which flagged D2 and D205, the two SMC TVS clamps, as broken. They are not.
`Diode_SMD:D_SMC_Handsoldering` declares its pads 90 degrees off its own outline in the library,
and D2 and D205 inherit that honestly. Running the library update proved it: KiCad rewrote both
from the library and left them exactly where they were.

The rule is therefore not "pad angle equals body angle" but **"pad angle minus body angle is the
same for every placement of the same library footprint."** The baseline is whatever that
footprint's other instances use. That is what the check now does, and it is what made the five
real failures visible in the first place: 5 parts sitting at 90 in a population of 41 that was
otherwise 0.

Regression tested both ways. Against the pre-update board it reports the 5 FAIL and 13 warn.
Against the current board it reports zero, and no longer accuses D2 or D205.

### Worth naming

The 20.8 error and the first-version-of-the-check error are the same error twice: **a check I
wrote said the geometry was fine, so a warning the application raised got suppressed.** KiCad was
right both times. A tool's warning outranks my tool's clean bill of health until my tool has been
shown to look at the same thing the application is looking at.

### State after

`tools/lay.py`: **0 FAIL, 10 warn.** 197 footprints, 0 courtyard overlaps, commutation loops
unchanged at 12.9 / 13.1 / 16.7 / 16.8 mm, heatsink shadow clear, 13 test points, 0 silkscreen
collisions.

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
