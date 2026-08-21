# final_lev — machine handoff

**Written:** 2026-08-21, from the original workstation, immediately before moving to a second
computer.
**Project:** 2-channel H-bridge levitation coil driver. 60 V bus, 30 A per yoke, two boards
per pod driving four yokes.

---

## 1. State of the design

| Stage | Status |
|---|---|
| Schematic | **Complete and verified.** ERC 0 errors / 2 intentional dual-name warnings (SW_B/COIL_B, SD_DRV/OK). F8 update 0/0 at 180 footprints. Independent netlist cross-check exact on all 99 nets / 492 pads. |
| PCB placement | **Complete.** 160 × 140 mm, outline (100,50)–(260,190), 184 footprints, **zero courtyard overlaps**, DRC clean except unconnected. |
| PCB routing | Not started. |
| Blocking decision | **2 layers vs 4 layers** — settle before routing. |

**Verified at handoff time, against the board file:** all 41 parts of the pending CH2 leg swap
are at their original coordinates, nothing is parked off-board, and J203 now sits fully inside
the outline. The board is in a clean, consistent state. Nothing is half-applied.

---

## 2. The one edit that is pending

A CH2 leg A / leg B position swap. Fully analysed and verified; **not yet applied.**

The reasoning, the before/after numbers, and the two findings that make it safe are in
`docs/20_layout_phase.md` §20.4. Short version: CH2 was built as a +65 mm translation of CH1,
but the coil connectors are mirrored, so CH2's leg A ends up furthest from its own shunt and
its SW_A node has to cross leg B's territory. Swapping the legs makes CH2 a true mirror.

`SW_A span 55.6 → 25.8 mm.` Cost: `COIL_B2 97.0 → 105.8 mm`. Zero courtyard overlaps either
way; commutation loops unchanged (17.7 mm leg A, 16.7 mm leg B, before and after) and the
C-H-C-H thermal ordering of the FET row preserved.

### Steps 1–3 — the swap

Use **right-click → Positioning Tools → "Move Exactly…"** on each selection (menu path, so no
shortcut guessing). Drag selection windows **left-to-right** so only fully-enclosed items are
caught. Each window below was verified to catch exactly 21 footprints — no extras, nothing
missing.

Do not try to exclude the bridge ceramics. They are spaced at exactly the shift distance and
land on each other's old coordinates, so including them produces an identical board — see
§20.4.

**Step 1 — park leg A out of the way**
Rubber-band from **(183.0, 57.5)** to **(213.5, 91.5)**.
Move Exactly: **X = 0, Y = 150**.
The block lands off the bottom edge around y = 209–240. If it goes off the *top* instead
(y ≈ −91 to −60), that is equally fine — that space is empty too. Just note which way it went.

**Step 2 — move leg B left into leg A's old slot**
Rubber-band from **(213.6, 57.5)** to **(244.5, 91.5)**.
Move Exactly: **X = −30, Y = 0**.

**Step 3 — bring leg A back into leg B's old slot**
The parked block is the only thing outside the outline, so drag a window comfortably around it.
Move Exactly: **X = 30, Y = −150**  (use **Y = +150** if it parked upward).

**Then re-run DRC.** Expect unconnected-item errors only.

### Step 4 is already done
J203's courtyard was 0.050 mm outside the board edge. It has been moved to
**x = 107.5, y = 157.5, rotation 90**, giving a 0.450 mm margin. Nothing further needed.

### Expected final coordinates — verification table

Leg B block, X − 30. Y and rotation unchanged on every part:

```
D207 217   -> 187      R224 217.5 -> 187.5    R226 217.9 -> 187.9    Q203 220   -> 190
R229 221.5 -> 191.5    C226 221.5 -> 191.5    C230 223   -> 193      U207 227.5 -> 197.5
C229 227.5 -> 197.5    D206 234   -> 204      Q204 235   -> 205      D208 235   -> 205
R225 235.5 -> 205.5    R227 236   -> 206      R228 238.5 -> 208.5    R231 242   -> 212
C219 222.5 -> 192.5    C220 228.5 -> 198.5    C221 234.5 -> 204.5
C222 240.5 -> 210.5    C223 231.5 -> 201.5
```

Leg A block, X + 30. Y and rotation unchanged on every part:

```
R213 186   -> 216      R232 186   -> 216      R215 189.5 -> 219.5    R217 189.5 -> 219.5
Q202 190   -> 220      D204 191   -> 221      D209 193   -> 223      C228 195.5 -> 225.5
U206 197.5 -> 227.5    C227 197.5 -> 227.5    C231 201   -> 231      R212 203.5 -> 233.5
Q201 205   -> 235      R214 205.5 -> 235.5    R216 206.5 -> 236.5    D203 208   -> 238
C212 192.5 -> 222.5    C214 198.5 -> 228.5    C215 204.5 -> 234.5
C216 210.5 -> 240.5    C217 201.5 -> 231.5
```

The ceramics landing exactly on each other's old coordinates is the check that they were safe
to include.

### Verify it worked

```
python3 tools/lay.py
```

Run from the project root. It re-derives everything from the board file: courtyard overlaps,
switching-node spans, commutation loops, mounting-hole and outline clearances, heatsink-shadow
intrusions, the leg-membership audit, and the selection-window check. It also simulates the
swap, so before applying the edit you can confirm the numbers independently rather than
trusting the tables above.

After the swap, `/CH2/SW_A` should read **25.8 mm**, courtyard overlaps should still be **0**,
and the CH2 commutation loops should still read 17.7 / 16.7 mm.

Note the leg-membership audit and the selection-window check in that output. They are the two
things that make the edit safe, and if either ever stops reading clean the coordinates in this
file are no longer trustworthy.

---

## 3. Moving the project to the second computer

**This repository has no git remote.** `git remote -v` is empty, so there is nothing to push
to. Transfer options, in order of preference:

1. **Add a remote** (GitHub/GitLab, private), then `git push -u origin master`. Best option —
   you get real sync instead of one-shot copies, which matters now that two machines are in
   play. Requires you to create the repo and authenticate; I can't do either for you.
2. **`git bundle`** — one file carrying the entire history:
   ```
   git bundle create ../final_lev.bundle --all
   ```
   Copy `final_lev.bundle` across, then on the new machine:
   ```
   git clone final_lev.bundle final_lev
   cd final_lev && git remote remove origin
   ```
3. **Copy the folder.** If you do this, `.gitignore` excludes `.history/`, `_old/` and KiCad
   local files — those do not need to travel. **`lib.pretty/` does**: it holds the custom
   Molex 38969-0002 footprint (`389690002.kicad_mod`, registered as `lev_lib` via
   `fp-lib-table`). Without it the board will not open cleanly.

### Starting the next session

A Cowork session is bound to one machine for its whole life and cannot be moved. On the new
computer: open the Claude desktop app, start a **new** task, and in the "Run this task" picker
at the top right choose **On your computer** — or, if it runs in the cloud, connect the
`final_lev` folder so the device bridge can reach it.

Then open with:

> Read `HANDOFF.md` and `docs/20_layout_phase.md` in final_lev, then give me Step 1.

The conversation history does not travel. The documents do.

---

## 4. Document map

| File | What it is |
|---|---|
| `00_design_log.md` | Running log, ~1400 lines, including explicit retractions of earlier wrong claims |
| `09_design_sheet_rev0.md` | Assumption register **A1–A14**. A14 is the modulation commitment |
| `15_sheet_annotations.md` | On-sheet annotation text |
| `16_adversarial_review.md` | 19 findings + Addendum 1 (delta review, 5) + Addendum 2 (full re-review, 14) |
| `17_rev0_fix_plan.md` | Historical. Block 7 is superseded |
| `18_firmware_interface.md` | MCU contract |
| `19_bom_caveats.md` | Cases where the symbol name ≠ the ordering part number |
| `20_layout_phase.md` | **This layout phase**: floorplan, verified metrics, the leg swap analysis |

---

## 5. Open items

| Item | Note |
|---|---|
| **2 layers vs 4 layers** | Blocking routing. |
| CH2 leg swap | Steps 1–3 above. |
| **Coil L, R, k unmeasured** | Once measured, re-derive bus ripple, per-device loss, heatsink, bootstrap sizing and OCP timing **in one pass** — they are coupled, and point-fixing them one at a time is what drove the 19 → 5 → 14 review-finding sequence. |
| §4.1 thermal numbers | Still derived under locked antiphase; must be redone under unipolar. |
| Bus-fault detector §3.2 | Undesigned. |
| ~8.7 W coil/bus copper loss | Known cost, `docs/20_layout_phase.md` §20.3. |

---

## 6. Standing ground rules

- Assumptions are allowed **only if logged** in the assumption register with a stated way to
  change them later.
- Reference material must be **real industry documents** — actual datasheets and application
  notes.
- **Documentation is a deliverable.**
- Instructions must be **concrete actions** with exact coordinates and rotations, one step at
  a time in chat — not zones, not principles, not written to a file. (This handoff is the
  standing exception, by request.)
- Only list what is **not already done**.
- Verify against the `.kicad_sch` / `.kicad_pcb` files, never screenshots.
- **No file surgery while KiCad is open.**
