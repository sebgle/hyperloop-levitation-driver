# final_lev — machine handoff

**Written:** 2026-08-24, before moving to a second computer.
**Updated:** 2026-08-24 on the second machine, after Board Setup, net classes and the
leg-A ceramic rotation. Section 2 now points at routing.
**Project:** 2-channel H-bridge levitation coil driver. 60 V bus, 30 A per yoke, two boards per
pod driving four yokes.

---

## 1. State of the design

| Stage | Status |
|---|---|
| Schematic | **Complete and verified.** ERC 0 errors / 2 intentional dual-name warnings (SW_B/COIL_B, SD_DRV/OK). F8 0/0 at 180 footprints. Independent netlist cross-check exact on all 99 nets / 492 pads. |
| PCB placement | **Complete.** 160 × 140 mm, 184 footprints, **zero courtyard overlaps**, DRC clean except unconnected. |
| CH2 leg swap | **Applied and verified.** `/CH2/SW_A` 55.6 → 25.8 mm. |
| Copper weight | **Fixed.** F.Cu / B.Cu were 0.007 mm; now 0.07 mm (2 oz). |
| Stackup | **Applied.** 4 copper layers, 1 oz inner, board total **1.600 mm** verified from the file. |
| Layer types | **Applied.** In1.Cu and In2.Cu typed `power`. |
| Net classes | **Applied.** `HV_POWER` split into `HV_POWER` / `HV_BOOT` / `PWR_GND`. Register **A16**. |
| Custom DRC rules | **Applied, NOT yet proven.** See §4. |
| Leg-A ceramics | **Rotated 180°.** CH1 A and CH2 A commutation loops 17.72 → 12.89 mm. `docs/20` §20.8. |
| PCB routing | **Not started.** This is the next action — §2. |

Current stackup, as read back from `final_lev.kicad_pcb`:

```
F.Mask    0.01
F.Cu      0.07     2 oz
prepreg   0.2      <-- the GND plane sits 0.2 mm under the FET row; this is the point
In1.Cu    0.035    1 oz     type: power
core      0.97
In2.Cu    0.035    1 oz     type: power
prepreg   0.2
B.Cu      0.07     2 oz
B.Mask    0.01
                   1.600 mm total
```

`0.97` is not a stocked core thickness — it is the residue that makes the total land on 1.600.
Only the **0.2 mm F.Cu→In1.Cu prepreg** carries design weight. Logged as **A15**; replace all
three dielectric rows with the fab's own table at quote time.

---

## 2. Pick up here — routing, starting with the commutation loops

Routing order is `docs/21` §21.7. **Step 1 of that order needs amending before it is followed**,
and the amendment has not been designed yet.

As written, §21.7 step 1 says to run the commutation loops "shortest, fattest, on F.Cu". That
does not work as stated. The bridge ceramics' `+60V` and `GND` pads alternate along the row at
3.1 mm pitch, so a single F.Cu `+60V` region and a single F.Cu `GND` region have to
interdigitate — and in leg A the two would have to cross outright, because the leg's `GND` pad
(Q2.3, x = 130.08) sits left of its `+60V` pad (Q1.2, x = 142.54) with three ceramics in between.

The intended resolution is the thing four layers was bought for:

> **`+60V` stays on F.Cu. The `GND` return drops to the In1.Cu plane directly underneath it.**
> Loop area then goes as path × 0.27 mm instead of path × lateral separation.

That needs via placement and zone outlines with real coordinates, and it has not been worked
out. It is the first thing to do.

The rest of the routing order is unchanged:

1. **Commutation loops** — as amended above.
2. **Gate loops** — gate and return as a tight pair per FET, over In1.Cu.
3. **Sense pairs** — Kelvin from the shunts to the INA240s, over unbroken plane, no crossings.
4. **High-current pours** — coil and bus zones on F.Cu, paralleled on In2.Cu, 20 vias per transition.
5. **Bulk to bridge** — the ~81 mm feed.
6. **Logic and signals** on B.Cu.
7. **GND fill and stitching**, then DRC.

---

## 3. Layer roles — hold to these during routing

| Layer | Copper | Role |
|---|---|---|
| **F.Cu** | 2 oz | Components, high-current pours, gate-drive loops |
| **In1.Cu** | 1 oz | **Solid GND plane. No routing, ever.** Unbroken under the FET row and the sense pairs — this is what four layers was bought for. Enforced by a DRC rule, §4 |
| **In2.Cu** | 1 oz | Paralleled high-current copper stitched to F.Cu, plus +60 V distribution |
| **B.Cu** | 2 oz | Logic and signal routing, GND fill stitched to In1.Cu |

---

## 4. The two custom DRC rules — applied, and NOT yet proven

`final_lev.kicad_dru`:

```
(rule "HV_POWER conductors must be sized for 30 A"
	(constraint track_width (min 10.7mm))
	(condition "A.hasNetclass('HV_POWER')"))

(rule "In1.Cu carries no tracks"
	(constraint disallow track)
	(condition "A.Layer == 'In1.Cu'"))
```

These convert two rules that used to live in documents into machine checks: 30 A nets must be
poured, not tracked, and In1.Cu stays a solid plane.

**Neither has been observed to fire.** Prove them before trusting them:

1. Draw a short track on `+60V` on F.Cu. It will come out 10.7 mm wide, because that is now the
   `HV_POWER` class width. Select it, press **E**, set **Width = 3.0 mm**.
2. **Ctrl+Shift+B**. Expect a track-width error naming **"HV_POWER conductors must be sized for
   30 A"**. The rule *name* in the message is the proof — not merely that some check fired.
3. Draw any track on **In1.Cu**. Expect "track is not allowed" naming **"In1.Cu carries no
   tracks"**.
4. Delete both test tracks.

> **The trap, recorded because it already caught us once.** "No violation" is equally consistent
> with *the rule works* and *the condition never matches*. A first attempt at step 1 drew a track
> on `+60V`, got no error, and looked like a broken rule — it was a 10.7 mm track legitimately
> passing a `min 10.7mm` constraint. A rule is not proven until something that should fail does.

`A.hasNetclass('HV_POWER')` is used rather than `A.NetClass == 'HV_POWER'` because KiCad 9+
allows a net to hold more than one class, and the `==` form compares against the whole composite
name — it would stop matching the day a second class is added to `+60V`. The earlier version of
this rule also carried `&& A.Type == 'track'`, which was removed: `track_width` is only ever
evaluated against tracks, and the two sources available disagree on whether that value is
capitalised, so the clause could only cost us.

### Net classes, as applied

| Class | Nets | Track | Clearance | Via |
|---|---|---|---|---|
| `HV_POWER` | `+60V`, `*SW_*`, `*COIL_*` — 7 nets, 62 pads | **10.7 mm** | 0.3 | 1.2 / 0.6 |
| `HV_BOOT` | `*VB_*` — 4 nets, 12 pads | 0.5 mm | 0.3 | 0.8 / 0.4 |
| `PWR_GND` | `GND` — 1 net, 119 pads | 0.5 mm | 0.3 | 1.2 / 0.6 |

10.7 mm is the IPC-2221 external width for 30 A at 2 oz, ΔT = 20 °C. The class now states the
sized width instead of the old 3.0 mm, which reversed out at ~160 °C. `PWR_GND`'s via is 1.2 /
0.6 deliberately: GND is the 30 A return, and undersized stitching fails thermally and
invisibly, so the default is set for the case that can hurt you and logic vias get shrunk
locally. `*VBATT*` matched none of the 99 nets and was deleted.

Clearance stayed at 0.3 mm on evidence. IPC-2221B Table 6-1 at 51–100 V wants 0.13 mm coated and
0.6 mm uncoated; under mask 0.3 mm is 2.3×, and the uncoated case is set by pad geometry rather
than by a net class. Measured across 89 HV pads with true rotated pad outlines, the tightest
60 V pair on the board is **0.635 mm** — the TO-220 lead pitch at Q1/Q2/Q202/Q203 — passing the
uncoated requirement by 6 %. Remember that number before anyone specifies conformal coating or
an altitude rating. Logged as **A16**.

---

## 5. Via stitching — 20 vias per 30 A layer transition

```
per-via current (25 um plating, IPC-2221 internal)
   0.3 mm drill    0.90 A @ dT=10 C     1.22 A @ dT=20 C
   0.6 mm drill    1.48 A @ dT=10 C     2.01 A @ dT=20 C
vias to carry 30 A between layers
   0.3 mm drill    34 (dT=10)    25 (dT=20)
   0.6 mm drill    21 (dT=10)    15 (dT=20)
```

The `HV_POWER` and `PWR_GND` via is 1.2 mm / 0.6 mm drill — the right size. Twenty per
transition is ΔT = 10 °C with margin. Vias are a thermal limit here, not a resistive one: forty
0.3 mm vias in parallel are 0.023 mΩ against 2.25–2.77 mΩ pours.

---

## 6. Verification

```powershell
py tools\lay.py
```

Run from the project root in **PowerShell**. If `py` is not on PATH try `python tools\lay.py`;
`python3` is a Linux/macOS name and usually does not exist on Windows. The script is stdlib-only
(`re`, `math`, `sys`, `os`) and reads the board file as explicit UTF-8, so it is safe on a
Windows locale. It re-derives everything from the board file: courtyard overlaps,
switching-node spans, commutation loops, mounting-hole and outline clearances, heatsink-shadow
intrusions, plus a leg-membership audit and a selection-window check.

Current expected output:

```
courtyard overlaps: 0
/CH2/SW_A   25.8 mm
CH1 A   12.9 mm (C6)   13.1 mm (C7)
CH1 B   16.7 mm (C13)  16.8 mm (C14)
CH2 A   12.9 mm (C214) 13.1 mm (C215)
CH2 B   16.7 mm (C220) 16.8 mm (C221)
heatsink-shadow intrusions: none
```

Note the script's `SHIFT` table still describes the CH2 leg swap, which is now applied — its
"SIMULATED" section would move the legs a *second* time. It is there as a record of the edit;
ignore that section, or delete the `SHIFT` block once you no longer want it.

### `tools/rot_ceramics.py`

The leg-A ceramic rotation, as a re-runnable tool rather than a transcript. It refuses to run
while `~final_lev.kicad_pcb.lck` exists, reads and writes bytes so CRLF survives, re-parses its
own patched buffer to recompute all four commutation loops and the full 184-footprint courtyard
check, and writes nothing unless those agree with the predicted values. Dry run by default;
`--write` to apply. It is idempotent in the sense that re-running it would rotate the parts a
*second* time and the built-in checks would then fail and refuse to write.

---

## 7. Moving the project between machines

**Remote:** `origin` → `https://github.com/sebgle/hyperloop-levitation-driver.git`. Added
2026-08-24, renamed from `final_lev` the same day. GitHub redirects the old URL, but do not
rely on that.

On a new machine:

```powershell
git clone https://github.com/sebgle/hyperloop-levitation-driver.git
cd final_lev
```

**`lib.pretty/` must travel** — it holds the custom Molex 38969-0002 footprint
(`389690002.kicad_mod`, registered as `lev_lib` via `fp-lib-table`). It is tracked in the repo;
confirm with `git ls-files lib.pretty` if a clone ever opens with a missing footprint.

`.gitignore` excludes `.history/`, `_old/`, `_to_delete/`, `*.bak` and KiCad local files, so a
clone is clean but carries none of the local backups.

Note: **git writes fail through the Cowork device bridge** — the mount forbids deletion, so
`.git` lock files persist. Run git from a normal Windows terminal.

### Starting the next session
A Cowork session is bound to one machine for its life and cannot be moved. On the new computer:
open the Claude desktop app, start a **new** task, and in the "Run this task" picker at the top
right choose **On your computer** — or, if it runs in the cloud, connect the `final_lev` folder.

Open with:

> Read `HANDOFF.md` and `docs/21_stackup_and_layers.md` in final_lev, then give me Step 1.

The conversation history does not travel. The documents do.

---

## 8. Document map

| File | What it is |
|---|---|
| `00_design_log.md` | Running log, including explicit retractions of earlier wrong claims |
| `09_design_sheet_rev0.md` | Assumption register **A1–A16**. A14 modulation, A15 stackup, A16 net classes |
| `15_sheet_annotations.md` | On-sheet annotation text |
| `16_adversarial_review.md` | 19 findings + Addendum 1 (5) + Addendum 2 (14) |
| `17_rev0_fix_plan.md` | Historical. Block 7 superseded |
| `18_firmware_interface.md` | MCU contract |
| `19_bom_caveats.md` | Cases where the symbol name ≠ the ordering part number |
| `20_layout_phase.md` | Floorplan, verified placement metrics, the leg-swap analysis, **§20.8 the ceramic rotation** |
| `21_stackup_and_layers.md` | Copper weight, layer count, the reasoning, and the routing order |
| `tools/lay.py` | Layout checker of record. Every clearance and loop number in these documents comes from it |
| `tools/rot_ceramics.py` | The leg-A ceramic rotation, with its own self-checks |

---

## 9. Open items

| Item | Note |
|---|---|
| **Routing** | §2. Not started, and §21.7 step 1 needs the In1.Cu-return amendment designed first. |
| **DRC rules unproven** | §4. Two minutes with a deliberately-too-thin track. |
| **Fab: 1 oz inner must be ordered explicitly** | 2 oz outer is a standard FR4 option and 1 oz inner is available, but inner **defaults to 0.5 oz**. Left at the default, the In2.Cu saving falls from 9.30 → 6.20 W to 9.30 → 7.44 W. An ordering checkbox, easy to lose. |
| **Coil L, R, k unmeasured** | Once measured, re-derive bus ripple, per-device loss, heatsink, bootstrap sizing and OCP timing **in one pass** — they are coupled, and point-fixing them one at a time is what drove the 19 → 5 → 14 review-finding sequence. |
| §4.1 thermal numbers | Still derived under locked antiphase; must be redone under unipolar. |
| Bus-fault detector §3.2 | Undesigned. |
| ~9.3 W coil/bus copper loss | Drops to ~6.2 W with the inner layer stitched at 1 oz. `docs/21` §21.2. |
| A10 / A13 vs reality | A10 corrected to 160 × 140. Worth a pass over the rest of the register for other placement-era staleness. |

---

## 10. Standing ground rules

- Assumptions allowed **only if logged** in the assumption register with a stated way to change
  them later.
- Reference material must be **real industry documents** — actual datasheets and application notes.
- **Documentation is a deliverable.**
- Instructions must be **concrete actions** with exact coordinates and rotations, one step at a
  time in chat — not zones, not principles, not written to a file. (This handoff is the standing
  exception, by request.)
- Only list what is **not already done**.
- Verify against the `.kicad_sch` / `.kicad_pcb` files, never screenshots.
- **No file surgery while KiCad is open.** `tools/rot_ceramics.py` now enforces this itself.
- When patching files: preserve CRLF, back up first, and have the script print the number it
  *computed*, not just the number it wrote.
- Shell commands are for **Windows PowerShell**: no `&&`, backslash paths, `py` (or `python`)
  rather than `python3`, `Remove-Item` rather than `rm`. Any script written for this project
  opens files with an explicit encoding, never the platform default.
