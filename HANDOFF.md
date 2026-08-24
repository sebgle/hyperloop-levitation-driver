# final_lev — machine handoff

**Written:** 2026-08-24, from the original workstation, before moving to a second computer.
**Project:** 2-channel H-bridge levitation coil driver. 60 V bus, 30 A per yoke, two boards per
pod driving four yokes.

**Verified at handoff:** KiCad closed, no lock file, git tree clean, board file matches the last
commit. Nothing is half-applied.

---

## 1. State of the design

| Stage | Status |
|---|---|
| Schematic | **Complete and verified.** ERC 0 errors / 2 intentional dual-name warnings (SW_B/COIL_B, SD_DRV/OK). F8 0/0 at 180 footprints. Independent netlist cross-check exact on all 99 nets / 492 pads. |
| PCB placement | **Complete.** 160 × 140 mm, 184 footprints, **zero courtyard overlaps**, DRC clean except unconnected. |
| CH2 leg swap | **Applied and verified.** `/CH2/SW_A` 55.6 → 25.8 mm. |
| Copper weight | **Fixed.** F.Cu / B.Cu were 0.007 mm; now 0.07 mm (2 oz). Board total 1.600 mm. |
| Layer count | **Decided: 4 layers, 1 oz inner.** Reasoning in `docs/21_stackup_and_layers.md`. |
| Board Setup | **NOT yet reconfigured for 4 layers.** This is the next action. |
| PCB routing | Not started. |

---

## 2. Pick up here — Board Setup for 4 layers

Nothing in the board file has been changed for the layer count yet; only the copper weight fix
is in. Do these four, in order.

**Step 1 — stackup.** File → Board Setup → **Physical Stackup** → set **Copper Layers: 4**, then
enter:

```
F.Mask    0.01
F.Cu      0.07     2 oz   <-- already correct
prepreg   0.2      <-- keeps the GND plane 0.2 mm under the FET row; this is the point
In1.Cu    0.035    1 oz
core      0.97
In2.Cu    0.035    1 oz
prepreg   0.2
B.Cu      0.07     2 oz   <-- already correct
B.Mask    0.01
                   board total should read 1.60 mm
```

**Step 2 — layer types.** Board Setup → **Board Editor Layers** → set **In1.Cu** and **In2.Cu**
type to **power**.

**Step 3 — net classes.** Fix the `HV_POWER` trap described in §4 below.

**Step 4 — ask the fab** whether they do **2 oz outer with 1 oz inner on 4 layers**. Common, but
some low-cost processes only offer 1 oz outer on 4-layer stackups, and 1 oz outer doubles the
pour losses to ~18.6 W. That changes the decision, not just the quote.

Then verify with `python3 tools/lay.py` and start routing at §5.

---

## 3. Layer roles — hold to these during routing

| Layer | Copper | Role |
|---|---|---|
| **F.Cu** | 2 oz | Components, high-current pours, gate-drive loops |
| **In1.Cu** | 1 oz | **Solid GND plane. No routing, ever.** Unbroken under the FET row and the sense pairs — this is what four layers was bought for |
| **In2.Cu** | 1 oz | Paralleled high-current copper stitched to F.Cu, plus +60 V distribution |
| **B.Cu** | 2 oz | Logic and signal routing, GND fill stitched to In1.Cu |

---

## 4. Two hard constraints

### `HV_POWER` is a trap as configured
Track width **3.0 mm**, patterns covering `+60V`, `GND`, `*SW_*`, `*COIL_*`, `*VB_*`, `*VBATT*`.
A 3.0 mm track at 2 oz carrying 30 A gives, by IPC-2221, roughly a **164 °C rise** — 3 mm is 12 %
of the required area. **Route these nets as zones, never as tracks.** 10.7 mm of pour is the
sized width. The 3.0 mm class width is safe only for short stubs and for the genuinely
low-current members of the class (`*VB_*` is bootstrap, milliamps, in this class for its
clearance not its width).

### Via stitching — 20 vias per 30 A layer transition
```
per-via current (25 um plating, IPC-2221 internal)
   0.3 mm drill    0.90 A @ dT=10 C     1.22 A @ dT=20 C
   0.6 mm drill    1.48 A @ dT=10 C     2.01 A @ dT=20 C
vias to carry 30 A between layers
   0.3 mm drill    34 (dT=10)    25 (dT=20)
   0.6 mm drill    21 (dT=10)    15 (dT=20)
```
The `HV_POWER` via is already 1.2 mm / 0.6 mm drill — right size. Twenty per transition is
dT = 10 °C with margin. Vias are a thermal limit here, not a resistive one: forty 0.3 mm vias in
parallel are 0.023 mΩ against 2.25–2.77 mΩ pours.

---

## 5. Routing order

The loops that determine whether the board works get the copper first; the signals that merely
need to arrive get routed around them.

1. **Commutation loops** — bridge ceramics to FET drains and sources. Shortest, fattest, F.Cu.
2. **Gate loops** — gate and return as a tight pair per FET, over In1.Cu.
3. **Sense pairs** — Kelvin from the shunts to the INA240s, over unbroken plane, no crossings.
4. **High-current pours** — coil and bus zones on F.Cu, paralleled on In2.Cu, 20 vias per transition.
5. **Bulk to bridge** — the ~81 mm feed.
6. **Logic and signals** on B.Cu.
7. **GND fill and stitching**, then DRC.

---

## 6. Verification

```powershell
py tools\lay.py
```

Run from the project root in **PowerShell**. If `py` is not on PATH try `python tools\lay.py`;
`python3` is a Linux/macOS name and usually does not exist on Windows. The script is stdlib-only
(`re`, `math`, `sys`, `os`) and reads the board file as explicit UTF-8, so it is safe on a
Windows locale. Re-derives everything from the board file: courtyard overlaps,
switching-node spans, commutation loops, mounting-hole and outline clearances, heatsink-shadow
intrusions, plus a leg-membership audit and a selection-window check.

Current expected output: `/CH2/SW_A` **25.8 mm**, courtyard overlaps **0**, CH2 commutation loops
**17.7 / 16.7 mm**, no heatsink intrusions.

Note the script's `SHIFT` table still describes the leg swap, which is now applied — its
"SIMULATED" section would move the legs a *second* time. It is there as a record of the edit;
ignore that section, or delete the `SHIFT` block once you no longer want it.

---

## 7. Moving the project to the second computer

**This repository has no git remote.** Options, in order of preference:

1. **Add a remote** (GitHub/GitLab, private), then `git push -u origin master`. Best — real sync
   rather than one-shot copies, which matters now that two machines are in play. Requires you to
   create the repo and authenticate.
2. **`git bundle`** — one file carrying the entire history. One has been generated at
   `final_lev.bundle` in the project root and delivered into the chat, so it can be downloaded
   on the other machine directly. To restore:
   ```powershell
   git clone .\final_lev.bundle final_lev
   cd final_lev
   git remote remove origin
   ```
   Do **not** join those with `&&` — Windows PowerShell 5.1 does not support it. Use separate
   lines, or `;` between them.
   To regenerate later: `git bundle create ..\final_lev.bundle --all`
3. **Copy the folder.** `.gitignore` excludes `.history/`, `_old/`, `_to_delete/` and KiCad local
   files. **`lib.pretty/` must travel** — it holds the custom Molex 38969-0002 footprint
   (`389690002.kicad_mod`, registered as `lev_lib` via `fp-lib-table`). Without it the board will
   not open cleanly.

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
| `09_design_sheet_rev0.md` | Assumption register **A1–A14**. A14 is the modulation commitment |
| `15_sheet_annotations.md` | On-sheet annotation text |
| `16_adversarial_review.md` | 19 findings + Addendum 1 (5) + Addendum 2 (14) |
| `17_rev0_fix_plan.md` | Historical. Block 7 superseded |
| `18_firmware_interface.md` | MCU contract |
| `19_bom_caveats.md` | Cases where the symbol name ≠ the ordering part number |
| `20_layout_phase.md` | Floorplan, verified placement metrics, the leg-swap analysis |
| `21_stackup_and_layers.md` | **Copper weight, layer count, the reasoning, and the routing order** |

---

## 9. Open items

| Item | Note |
|---|---|
| Board Setup for 4 layers | §2. The immediate next action. |
| Fab confirmation | 2 oz outer / 1 oz inner on 4 layers. Blocking — 1 oz outer would double pour losses. |
| **Coil L, R, k unmeasured** | Once measured, re-derive bus ripple, per-device loss, heatsink, bootstrap sizing and OCP timing **in one pass** — they are coupled, and point-fixing them one at a time is what drove the 19 → 5 → 14 review-finding sequence. |
| §4.1 thermal numbers | Still derived under locked antiphase; must be redone under unipolar. |
| Bus-fault detector §3.2 | Undesigned. |
| ~9.3 W coil/bus copper loss | Drops to ~6.2 W with the inner layer stitched. `docs/21_stackup_and_layers.md` §21.2. |
| `_to_delete/` | Board backups and stale git lock files. Safe to delete; this session could not remove files on the mount. In PowerShell: `Remove-Item -Recurse -Force .\_to_delete`. Then `git gc --prune=now` to sweep stray `tmp_obj_*` files from `.git/objects`. |

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
- **No file surgery while KiCad is open.**
- When patching files: preserve CRLF, back up first, and have the script print the number it
  *computed*, not just the number it wrote.
- Shell commands are for **Windows PowerShell**: no `&&`, backslash paths, `py` (or `python`)
  rather than `python3`, `Remove-Item` rather than `rm`. Any script written for this project
  opens files with an explicit encoding, never the platform default.
