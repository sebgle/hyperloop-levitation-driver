# Design Sheet Rev 0 — Values to Draw Tonight

Levitation coil drive stage · Sebastian · 2026-08-11
**Status: provisional. Every assumption is registered in §2 with a change path.**

---

## 1. Decisions locked for this revision

| Decision | Choice | Why this one |
|---|---|---|
| **Topology** | Full H-bridge per yoke | Bidirectional confirmed (EDD Fig. 3, −16 A to +12 A) |
| **Board** | **One 2-channel board**, build two | Subset that works either way; halves bus current to 60 A; smaller layout is achievable tonight |
| **Design current** | 30 A/yoke, 15 A/coil | EDD peak, safe upper bound |
| **Design PWM** | 32 kHz (thermal worst case) | Their stated ceiling |
| **Modulation** | **Hardware-agnostic — see §3.1** | Assumption eliminated, not logged |

---

## 2. Assumption register

**This is the important artifact.** Put a copy in the schematic as a text block so it travels
with the design instead of living in your head.

| # | Assumption | Value used | Basis | Confidence | If wrong → | Change cost |
|---|---|---|---|---|---|---|
| A1 | Coil resistance | 2 Ω/coil, **1 Ω/yoke** | EDD §2.2, confirmed by independent geometry calc (250 t × 18 AWG ⇒ 1.6–2.1 Ω) | **High** | If 4 Ω: peak current halves, duty doubles to 100 %, bootstrap breaks | Rework gate drive. **Measure this first.** |
| A2 | Coil inductance | 10 mH/coil, k = 0.85, **L_yoke = 9.25 mH** | Chat recollection + my magnetic-circuit estimate (10–13 mH) | **Low** | Bus energy 2.1–5.9 J | **Nothing** — §3.2 removes the dependency |
| A3 | Modulation scheme | Unknown | — | — | — | **Nothing** — §3.1 removes the dependency |
| A4 | Logic level | 3.3 V or 5 V | Unknown | — | — | **Nothing** — §3.3 removes the dependency |
| A5 | Peak duration | **Continuous** | Deliberately conservative; EDD implies seconds | Conservative | Over-designed heatsink | None — just oversized |
| A6 | Ambient temperature | **40 °C** | Standard assumption, nobody has stated it | **Low** | Heatsink resizes linearly | Swap heatsink. Mechanical only. |
| A7 | Aux rails | Board generates its own 12 V and 3.3 V from the 60 V bus | Nobody has said the pod supplies them | Medium | If pod supplies them, DNF the regulator | **DNF one part** |
| A8 | 30 A/yoke is real | Design to 30 A | Safe upper bound whether real or inherited | Conservative | Over-designed | None |
| A9 | Bus voltage | 60 V **max** (not nominal) | EDD §2.1 states "Input Voltage (Max)" | High | If nominal, top-of-charge ~67 V → 100 V FETs get tight | Re-check FET margin |
| A10 | Board outline | **160 × 100 mm** (Eurocard) | Decided 2026-08-14, no upstream constraint stated. Set by the 8× TO-220 row (~120 mm) and the §4.2 heatsink estimate (~150 × 100 mm) | Decision, not measurement | Outline changes | Re-do placement. No schematic impact. Cheapest thing here to change *before* routing, expensive after |
| A11 | Mounting | **4 × M3**, Ø3.2 mm, on a 150 × 90 mm rectangle | Decided 2026-08-14. Standard PCB standoff hardware | Decision | Hole pattern moves | Move 4 holes + keepouts. Trivial before routing |
| A12 | Chassis bond | Mounting holes **isolated**; 0 Ω 1206 jumper to GND fitted at the bus-entry hole, **DNF** | Yokes float; only common point is at the motor-controller negatives (`03_open_questions.md`). A bonded screw creates an unplanned 60 A return path through the pod structure | Medium | If chassis bonding is required | **Stuff one 0 Ω part.** No re-spin — this is why the provision exists |
| A13 | Harness entry | Bus in on one short edge, coils out on the other; logic on the far long edge | Decided 2026-08-14. Follows the current path: bus → bulk → bridge → shunt → coils | Decision | Connector edges move | Re-do placement of 4 connectors and the high-current pours |
| A14 | **Modulation scheme** | **Unipolar (3-level) PWM** — leg A at D, leg B at 1−D; the two channels interleaved **180°** | Decided 2026-08-14. Bus ripple, plus linearity through zero | Decision | If locked antiphase is mandated: bus ripple 52 A rms against a ~14 A bank | **Capacitor bank moves to polymer or film.** BUS sheet respin + BOM |

**Three of the four blockers are removed by design in §3, not by assumption.** Only A1 and A2
really matter, and A2 is neutralised.


### A14 — why unipolar, in full

This is the assumption the capacitor bank rests on, so the reasoning is written out rather
than left implicit.

The coil is effectively a DC source to the bus — its own ripple is 0.15 A pk-pk against 30 A —
so whatever fraction of the period the bridge draws from the bus, it draws the *full* 30 A.
That fraction is what sets the bus RMS ripple, and it differs by a factor of three across the
three candidate schemes:

| Scheme | Bus draws for | AC ripple, 1 ch | 2 ch in phase | 2 ch interleaved 180° |
|---|---|---:|---:|---:|
| Locked antiphase | the whole period, sign-reversing | 25.98 A | **51.96 A** | 30.0 A |
| Sign-magnitude | D = 0.5 | 15.00 A | 30.0 A | ≈ 0 |
| **Unipolar (3-level)** | \|2D−1\| = 0.5 | **15.00 A** | 30.0 A | **≈ 0** |

Six Rubycon ZLH cans give roughly **14 A**. Locked antiphase is off the table on that alone.

Between the other two, the deciding factor is **behaviour at zero current, not ripple** —
they are identical on ripple. HEMS force goes as (B_pm ± B_coil)², so with the magnets
carrying static weight the coil current trims about zero and crosses it routinely.
Sign-magnitude cannot cross zero continuously: the direction leg has to flip, which puts a
deadband and a discontinuity exactly at the operating point the loop lives at. Unipolar is
linear through zero — D = 0.5 means zero volts, zero coil current, and **zero bus draw**.

Unipolar also halves the coil's own ripple and doubles its frequency, because the coil sees
+V / 0 / −V at 2·f_sw.

**Cost, stated honestly.** Dead time now distorts both legs rather than one, so there is a
small duty-dependent error near zero that firmware may need to compensate. That is a
calibration, not a topology problem. And the 180° interleave has to be real — if both
channels share a carrier with no phase offset, the bus ripple doubles to 30 A and the bank is
marginal again. **The interleave is a hard requirement of this assumption, not an
optimisation.**

**What this supersedes.** `16_adversarial_review.md` §5 recommended sign-magnitude. That was
right about locked antiphase being unaffordable and wrong to stop there — it optimised for
bus ripple alone and did not check the zero-crossing behaviour against the PM-biased
operating point. Unipolar gives the same ripple without the deadband.

**What still needs doing.** `09_design_sheet_rev0.md` §4.1 sizes the FET losses under
"Antiphase (design to this)". Those numbers need re-deriving for unipolar before the thermal
design is final — switching loss should fall, because each leg hard-switches less often.

---

## 3. Design moves that make assumptions not matter

### 3.1 Two independent PWM inputs per channel — kills the modulation-scheme blocker

Instead of building a logic block that converts PWM+DIR into gate signals, **bring one PWM
input per half-bridge straight to the connector.** Two PWM lines per yoke, plus one shared
shutdown.

The IR2184 already provides deadtime and shoot-through interlock internally, so each
half-bridge is safe driven from a single logic input. That means:

- **Sign-magnitude:** firmware PWMs one leg, holds the other static
- **Locked antiphase:** firmware drives both complementarily
- **Independent/mixed decay:** also available

All three in firmware, **zero hardware change**. The question I couldn't get answered stops
mattering. Cost: one extra signal wire per channel.

Per channel: `PWM_A`, `PWM_B`, `/SD`, `ISENSE_OUT`, `/FAULT`, `AGND`, `DGND`.

### 3.2 Slow-decay-on-fault — kills the bus energy-dump problem

At 30 A the yoke stores 4.2 J (up to 5.9 J at worst-case L). Dumped into bus capacitance with
the battery absent, the bus reaches **146–169 V** against 100 V parts. Capacitance cannot fix
this — even 1000 µF only gets you to 109–124 V.

**The fix is a rule, not a component.** On bus fault (undervoltage or overvoltage detected),
turn **both low-side FETs on** instead of tri-stating. The coil current then circulates
`coil → Q2 → Q4 → coil` and its energy dissipates in the coil's own 1 Ω:

    τ = L_yoke / (R_coil + 2·R_ds(on)) = 9.1–12.8 ms → fully decayed in 46–64 ms

**All 4.2 J stays in the coil. The bus never sees it.** Costs nothing but a comparator and a
local hold-up capacitor on the 12 V gate-drive rail so the FETs can still be driven for those
~60 ms.

This also makes A2 (inductance) irrelevant to the protection design — which is why the one
assumption I have least confidence in stops being a risk.

*This is what the original design's "let the coil freewheel rather than actively reverse"
instinct was reaching for. It just wasn't extended to the fault case.*

### 3.3 Schmitt-buffer the control inputs — kills the logic-level blocker

**74LVC2G17** (dual Schmitt buffer) on each channel's PWM inputs, supplied from the local
3.3 V rail. Inputs are 5 V-tolerant, so 3.3 V and 5 V MCUs both work with no change. Also
cleans up edges on a long noisy harness.

*Upgrade path:* if inter-board ground offset becomes a problem (I flagged it — the INA240
outputs sit on grounds carrying 30–60 A of switching current), swap to a digital isolator
(ISO7721 / Si8621). **Lay the footprint out to accept either** and you keep that option free.

### 3.4 Design thermals for the worst modulation

Antiphase switches all four FETs; sign-magnitude switches two. Size the heatsink for
antiphase at 32 kHz and you are safe under any answer. Costs a bigger heatsink, which is the
cheapest possible insurance.

---

## 4. Component values — ready to draw

### 4.1 Power stage (per channel)

| Item | Value | Note |
|---|---|---|
| Q1–Q4 | **IRF100B201** TO-220AB | 100 V, 4.2 mΩ max, Q_g 255 nC max, R_thJC 0.34 °C/W |
| Bus bulk | 2× **470 µF 100 V** electrolytic | Normal ripple; the fault case is handled by §3.2 |
| Bus ceramic | 4× **1 µF 100 V** 1210 + 4× **100 nF** 0805 | Right at the bridge, tight loop |
| Bus TVS | **5.0SMDJ70A** | V_R 70 V, V_BR 77.8–86 V. Residual clamp only |

**Losses at 30 A, 125 °C junction, R_ds(on) = 6.72 mΩ hot:**

| | Sign-magnitude | Antiphase (design to this) |
|---|---:|---:|
| Conduction, per channel | 12.1 W | 12.1 W |
| Switching @32 kHz, per switching FET | 3.70 W | 3.70 W |
| **Channel total** | 19.5 W | **26.9 W** |
| **Board total (2 ch)** | 39.0 W | **53.8 W** |
| Worst single FET | 6.73 W | 6.73 W |

### 4.2 Heatsink

    R_th(s-a) ≤ 1.35 °C/W

Derived at T_a = 40 °C, T_j = 125 °C, TIM = 1.5 °C/W (silpad), 53.8 W board, 6.73 W worst FET.

⚠️ **1.35 °C/W in natural convection needs a substantial extrusion** — roughly 150 × 100 mm
with 40 mm fins. With any forced air it becomes easy. **This is why ambient temperature and
airflow (question C20) matter** — it is the one open question that directly affects a
mechanical part you have to buy.

### 4.3 Gate drive (per channel: 2× IR2184)

| Item | Value | Basis |
|---|---|---|
| C_boot | **1 µF X7R 25 V** | Q_tot ≈ 405 nC → **0.41 V droop**. Budget is 1.5 V (11.3 V start − 9.8 V UVLO max) |
| R_boot | **1 Ω** | Gives **D_max = 94 %** at 16 kHz. At the 50 % design point this is enormous margin |
| D_boot | **ES1D** 200 V ultrafast | Must block the full bus |
| R_gate on | **10 Ω** | → I_g 0.70 A, t_sw 64 ns |
| R_gate off | **4.7 Ω** + parallel diode | Faster turn-off, protects against dv/dt-induced turn-on |
| Deadtime | IR2184 internal ~500 ns | Adequate against ~200 ns turn-off. Do not defeat it |
| VCC decoupling | 1 µF + 100 nF at each driver | |

### 4.4 Current sense (per channel)

| Item | Value | Basis |
|---|---|---|
| Shunt | **1 mΩ, 4-terminal, ≥2 W** | 0.90 W at 30 A. Use a metal-element 4-terminal part, not a 2512 thick film |
| Amp | **INA240A1** (gain 20) | 30 A → 600 mV. Full scale **±82 A**. 1 A → 20 mV |
| Reference | **1.65 V** from the 3.3 V rail | Bidirectional, centred |
| Placement | **In-line with the coil** | Only placement that sees true bidirectional coil current. This is what the INA240's PWM rejection exists for — TI SBOA174 Table 2 |
| Input filter | RC, corner ≫ control bandwidth | Set generously; tune once question B10 is answered |

### 4.5 Over-current protection (per channel)

| Item | Value | Basis |
|---|---|---|
| Threshold | **±45 A** | 30 A legitimate, 60 A ceiling |
| Comparator | **LM393** (dual = window comparator) | Trips at **2.55 V** and **0.75 V** against the 1.65 V ref |
| Latch | **74HC74** set-dominant, drives `/SD` low | ⚠️ The old BOM had no latch. Without one the fault self-clears and chatters |
| Reset | MCU line or power cycle | |

**Why LM393 is fine here** — its 1.3 µs propagation delay looked slow, so I checked it:
worst-case di/dt is (60 V + 30 V)/9.25 mH = 9730 A/s. In 1.3 µs the current rises **12.6 mA**.
The load inductance protects you. The fast fault is shoot-through, and the IR2184's interlock
handles that.

### 4.6 Aux rails

| Item | Value | Note |
|---|---|---|
| 60 V → 12 V | **LM5164** (100 V, 1 A synchronous buck) | Powers gate drivers. Needs ~100 mA |
| 12 V hold-up | **220 µF** local | **Required for §3.2** — the FETs must stay driven for ~60 ms after bus loss |
| 12 V → 3.3 V | Small LDO | INA240 supply, 1.65 V reference, Schmitt buffers |

*If the pod supplies 12 V and 3.3 V (question B17), DNF the LM5164 and feed the rails
directly. One part.*

### 4.7 Connectors — **and the answer for your lead**

| Connection | Part | Rating |
|---|---|---|
| **Yoke output**, battery in | **Molex 38969-0002** | **50 A, 600 V, 20–8 AWG**, 12.7 mm pitch, 2 position, PCB mount |
| Signals | Molex 0389220002 (the lead's part) | 20 A, 300 V, 12–26 AWG — fine for logic |

**This is the pitch to your lead:** same manufacturer, same barrier-strip style, PCB mount —
but **50 A and it accepts the 10 AWG the EDD specifies**. It satisfies the intent of the
constraint while meeting the actual requirement. The 20 A part stays on the signal side where
it is entirely appropriate.

---

## 5. For the LTspice build

Parameterise the two things you don't know, so a corrected measurement is a one-line change:

```
.param Rcoil=2      ; ohm per coil      -- A1, EDD, med-high confidence
.param Lcoil=10m    ; H per coil        -- A2, ESTIMATED, low confidence
.param kcpl=0.85    ; coupling          -- A2, ESTIMATED, low confidence
.param Vbus=60
.param Fpwm=32k
```

**Sweep, don't confirm.** Run `.step param Lcoil list 5m 10m 13m` and look at what actually
moves. That tells you how sensitive the design is — which is real information. Running one
sim at an assumed value and calling it verified is the previous revision's mistake.

Worth simulating tonight, in priority order:

1. **Bootstrap hold-up** across the duty range — confirms §4.3
2. **Slow-decay-on-fault** — force the bus open at 30 A and confirm the bus stays under 100 V
3. **Current ripple** vs. modulation scheme — antiphase ripple is much worse than
   sign-magnitude and this is where you'd see it
4. **OCP trip timing** into a shorted coil

---

## 6. When the answers land

| Answer | What changes |
|---|---|
| A1 = 4 Ω, not 2 Ω | **Significant.** Peak current halves, duty → 100 %, bootstrap needs a charge pump. Rework gate drive |
| A2 measured L | Nothing structural — §3.2 removed the dependency. Update the sim and the ripple numbers |
| A3 modulation | **Nothing** — §3.1 covers all cases |
| A4 logic level | **Nothing** — §3.3 covers both |
| A6 ambient ≠ 40 °C | Swap the heatsink. Mechanical only |
| B11 two-yoke flight | Board count only. Schematic unchanged |

**A1 is the one that hurts.** It is also the one with the highest confidence and the easiest
measurement. If you get one number from the lev team, get that one.
