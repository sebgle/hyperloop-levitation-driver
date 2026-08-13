# HEMS Slide + LEV EDD — What They Settle, and What I Got Wrong

Levitation coil drive stage · Sebastian · 2026-08-11 · Rev 1
Sources: team slide "Main Objective & Principle"; **LEV EDD 2026 1.pdf**

> **Read this section first.** The EDD contradicts the numbers I was given in the team chat,
> and three of my Day-1 findings were built on the chat's numbers. Those findings are
> **retracted below**. The EDD's numbers survive an independent check; the chat's do not.

---

## 1. Questions the EDD answers

| Q | Answer | Source |
|---|---|---|
| **Q4** — bidirectional? | **YES.** HEMS = PM + coils, "permanent magnets provide a constant attractive force, coils actively regulate." Fig. 3 plots force for **I = −16 A to +12 A**. | EDD §1 |
| **Q1** — peak current? | **60 A continuous / 120 A peak, total.** Both chat figures were right — they were describing different things. | EDD §2.1 |
| **Q5** — series or parallel? | **Parallel.** 2 Ω/coil → 1 Ω/yoke. | EDD §2.2 |
| **Q6** — pack voltage | 60 V is the **max**, not nominal. | EDD §2.1 |
| **Q19** — gap and mass | **8 mm nominal gap, 316 kg pod, ~3100 N.** | EDD §1 |
| — | Coil = **250 turns of 18 AWG**, 4 yokes, U-shaped steel core, PM embedded in each leg | EDD §1, §2.3 |
| — | Yoke envelope **228.6 × 76.2 × 127 mm** | EDD §1 |
| — | **10 AWG** conductors to the yokes | EDD §2.2 |
| — | **50 % duty cycle limit** | EDD §2.2 |

### The Q1 "conflict" was never a conflict

The chat's "minimum is like 60 A total" and the overview PDF's "120 A total" are **both from
the EDD table**: 60 A is *Max Continuous Current*, 120 A is *Peak Current Capability*. That
resolves cleanly and nobody was wrong.

---

## 2. The coil resistance conflict — and an independent check that settles it

**The EDD says 2 Ω per coil. The chat said 4 Ω per coil.** Everything downstream doubles or
halves on this, so I checked it against the physical coil description rather than picking one.

18 AWG copper: 1.024 mm dia, 0.823 mm², **20.95 mΩ/m** at 20 °C. At 250 turns:

| Mean turn length | Wire length | R @ 20 °C | R @ 100 °C |
|---:|---:|---:|---:|
| 200 mm | 50.0 m | 1.05 Ω | 1.37 Ω |
| 300 mm | 75.0 m | 1.57 Ω | 2.06 Ω |
| 400 mm | 100.0 m | 2.09 Ω | 2.74 Ω |
| 450 mm | 112.5 m | 2.36 Ω | 3.09 Ω |

For a yoke of that size, mean turn length lands in the 300–400 mm range, giving
**≈1.6–2.1 Ω cold**. 

> **The EDD's 2 Ω/coil is geometrically consistent. The chat's 4 Ω/coil is not** — it would
> need a ~750 mm mean turn, which the yoke envelope doesn't allow. It was also prefaced with
> "I highkey don't remember," so this is not a surprise.

**Working value: 2 Ω/coil, 1 Ω/yoke — still to be confirmed by measurement.** Note the
temperature term: at 100 °C the coil is ~1.31× its cold resistance, which cuts achievable
current by ~24 % exactly when the system is working hardest.

---

## 3. RETRACTIONS — three Day-1 findings do not survive

I want these on the record explicitly rather than quietly corrected.

### ❌ RETRACTED: "30 A/yoke is exactly 100 % duty, so there is no headroom"

Built on R_yoke = 2 Ω from the chat. With **R_yoke = 1 Ω**:

- Ceiling at 100 % duty = **60 A/yoke**, not 30 A
- The 30 A design point needs only **30 V → 50 % duty** — which is exactly the EDD's stated
  50 % duty limit, so the EDD is internally consistent
- **There is 30 V of voltage headroom at the peak operating point**

This is a materially better design point than the one I analysed.

### ❌ RETRACTED: "100 % duty breaks the bootstrap high-side supply"

At 50 % duty the bootstrap capacitor recharges every cycle. **This is a non-issue.** Still
needs sizing per AN-1123, but it is routine sizing rather than a structural flaw.

### ❌ RETRACTED: "the 45 A over-current trip can never fire"

With a 60 A/yoke ceiling, 45 A is reachable. The trip is a real protection, not decoration.

### ✅ What survives unchanged

- **The connector conflict** — and it got worse. See §5.
- **120 A of PDU copper** — the total is still 120 A peak.
- **Fast decay / negative voltage is required** — and Q4 confirming PM bias makes the full
  H-bridge the right answer. Document 02's decision rule resolves to the H-bridge branch.
- **Fuse voltage rating** — ANL/MIDI at 32 V DC is still invalid on a 60 V bus.
- **Coil dissipation is large** — though half what I said. See §4.

---

## 4. What I now find in the EDD

### 4.1 ✅ The 18 AWG thermal claim actually checks out

EDD §2.3 claims 18 AWG rated 7 A continuous "safely absorbs the 15 A peak during brief
lift-off transients." That sounded optimistic — 15 A in 0.823 mm² is **18.2 A/mm²**, which is
far above any continuous winding current density. So I checked the transient.

Copper mass ≈ 0.55–0.74 kg per coil → thermal mass ≈ 213–284 J/K.
At 15 A into 2 Ω = 450 W per coil:

- **Adiabatic temperature rise: 1.6–2.1 K/s**
- **47–63 seconds to rise 100 K**

**The claim holds, provided "brief" means seconds and not minutes.** This is a genuine
strength of the design and the reasoning behind it is sound. What is still missing is a
*stated* maximum duration and the insulation class — Q3 remains open, but it is now a
question about where between 1 s and 60 s the limit sits, not an open-ended unknown.

Peak dissipation for reference: **450 W/coil, 900 W/yoke, 3.6 kW across the pod.**

### 4.2 ⚠️ The series-vs-parallel justification in EDD §2.2 is wrong

> *"the parallel configuration yields a 1 Ω equivalent load, allowing the system to reach
> peak current at 30 V. This avoids the 120 V requirement of a series configuration."*

The 120 V figure assumes you need **30 A through the series pair**. You don't. Force depends
on MMF = N·I per coil, so the required *per-coil* current is 15 A either way:

| | Per-coil current | Yoke R | Yoke voltage | Yoke current | Power |
|---|---:|---:|---:|---:|---:|
| Parallel | 15 A | 1 Ω | **30 V** | 30 A | 900 W |
| Series | 15 A | 4 Ω | **60 V** | 15 A | 900 W |

Series needs **60 V, not 120 V.**

**The conclusion is still right — parallel is the correct choice — but for a different
reason.** Series at 60 V sits at exactly 100 % duty with zero headroom for the current loop;
parallel at 30 V sits at 50 % duty with 30 V spare. *That* is why parallel wins. It is worth
correcting because the stated reason would lead someone to the wrong answer if the bus
voltage ever changed.

### 4.3 ⚠️ Nowhere in any document is the coil inductance stated

The EDD gives turns, wire gauge, geometry, resistance, force curves — and **no inductance**.
It is the one parameter that sets the current-loop dynamics, and it is still unmeasured.
From the magnetic circuit (two 8 mm gaps plus two PMs in series, 250 turns) I estimate
**10–13 mH per coil**, which is consistent with the chat's remembered 10 mH. But that is my
estimate, not their data.

### 4.4 ⚠️ "Motor Driver Limit: 30 A (per driver)" is a legacy constraint, not a requirement

This describes the motor controllers they use **today** — the ones you are replacing. It
should not silently become a specification for your board. Worth confirming whether 30 A/yoke
is a physics requirement or an artefact of the part they happened to have.

---

## 5. The connector conflict is now concrete and unambiguous

EDD §2.2 specifies **10 AWG conductors** to the yokes, sized per NEC for 30 A.

The Molex 0389220002 your lead specified accepts **AWG 12–26** and is rated **20 A**.

> **10 AWG wire will not physically fit in the connector, and the connector is rated at
> two-thirds of the current the EDD requires.**

This is no longer a judgement call about derating — it is a dimensional incompatibility. It
needs resolving with your lead before any footprint goes on a board.

---

## 6. Revised dynamics — using their gap, their mass, their force curve

### 6.1 Plant instability

An attractive suspension is open-loop unstable. Two estimates:

| Method | Unstable pole | Time to double |
|---|---:|---:|
| 1/x² approximation, √(2g/x₀) at 8 mm | 49.5 rad/s (7.9 Hz) | 20 ms |
| **From the Fig. 3 force–gap slope (~300 kN/m at 316 kg)** | **30.8 rad/s (4.9 Hz)** | **32 ms** |

The second is the better number because it uses their own simulated force curve rather than
an idealised 1/x². *Caveat: I read that slope off the graph image. The controls team should
compute it from the underlying simulation data.*

**This is more benign than I feared on Day 1** — my earlier table assumed a 1–2 mm gap, and
8 mm is a much slower plant.

### 6.2 Current loop vs. plant

τ = L(1+k)/R per coil, where k is the coupling between the two coils on the shared circuit
(a result derived in §7 — τ is the same for series and parallel):

| L/coil | k | L_yoke | τ | 1/τ | vs. plant |
|---:|---:|---:|---:|---:|---:|
| 5 mH | 0.85 | 4.63 mH | 4.63 ms | 216 rad/s | **7.0×** |
| 10 mH | 0.50 | 7.50 mH | 7.50 ms | 133 rad/s | 4.3× |
| 10 mH | 0.85 | 9.25 mH | 9.25 ms | 108 rad/s | **3.5×** |
| 13 mH | 0.85 | 12.0 mH | 12.0 ms | 83 rad/s | **2.7×** |

Rule of thumb wants 5–10× separation. At the likely inductance this lands at **2.7–3.5×**,
which is tight but not disqualifying — and the 30 V of headroom means the current loop can
overdrive rather than being limited to the natural L/R response:

    di/dt available at the 30 A point = 30 V / 9.25 mH ≈ 3.2 A/ms

**This is a controls-team question, and now I can hand them real numbers instead of a
worry.** It remains the strongest argument for the current sensing.

---

## 7. Mutual inductance — a correction to my own model

Both coils sit on the **same magnetic circuit**, so they are strongly coupled (M = k·L). The
effective inductance is not the naive combination of two independent coils:

| | Inductance | Resistance | Time constant |
|---|---|---|---|
| Series-aiding | 2L(1+k) | 2R | **L(1+k)/R** |
| Parallel-aiding | L(1+k)/2 | R/2 | **L(1+k)/R** |

**τ is identical either way.** Series vs. parallel changes current capability, not speed —
which usefully removes one variable from that decision.

Consequence for measurement: **one coil measured in isolation is not enough.** Measure the
yoke as wired, and measure one coil with the other **open** (gives L) and with the other
**shorted** (gives L(1−k²)). Those two readings give k directly.

### 7.1 ⚠️ REVISED AND WORSE: the coil energy dump

With the higher parallel-yoke inductance, this got worse rather than better:

| L_yoke | Coil energy at 30 A | Bus peak if the battery is absent |
|---:|---:|---:|
| 4.63 mH | 2.08 J | 112 V |
| **9.25 mH** | **4.16 J** | **146 V** |
| 12.0 mH | 5.40 J | 163 V |

Against 100 V FETs and 100 V bus caps. To hold the peak below 85 V on the bus capacitor
alone would need **~2300 µF per yoke**, versus the 470 µF in the current BOM.

This does not mean 2300 µF is the answer — the battery normally absorbs this energy, and the
real fix is likely a combination of a properly sized TVS, more bulk capacitance, and making
sure the bus can never be opened under load. But it does mean **the 470 µF figure was chosen
without this calculation behind it**, and the failure mode (fuse opens or a connector bounces
at peak current) is one that plausibly happens on a pod.

---

## 8. Open questions after the EDD

**Resolved:** Q1, Q4, Q5, Q6, Q19 · **Partly resolved:** Q3 (bounded to seconds, exact limit
still needed)

| Q | Still open |
|---|---|
| **Q2** ⬆ | Measure L and R on a real yoke. Now the single biggest unknown — and specifically **R (is it 2 Ω or 4 Ω?)**, **L**, and **k** (open vs. shorted readings). |
| **Q3** | Maximum duration at peak current, and the coil insulation class. |
| **Q7** | Can the pod fly on two yokes? |
| **Q8** | Where the yokes physically sit relative to the electronics. |
| **Q10** ⬆ | Connector — now a dimensional conflict, not a derating argument. |
| **Q20** | What current-loop bandwidth do controls need? Give them §6. |
| **Q21** | Gap sensor spec — type, range, bandwidth, output. It's in the architecture and I have no spec for it. |
| **NEW Q22** | Is 30 A/yoke a physics requirement, or inherited from the 30 A motor drivers being replaced? |
| **NEW Q23** | Where does the 50 % duty limit come from — thermal, control, or the existing driver? |
| **NEW Q24** | Is the EDD current (rev 1, 2026)? Does it describe the yoke on the pod today? |

---

## 9. Bottom line

The EDD is a much better source than the overview PDF, and the design it describes is more
coherent than the numbers I was working from. The operating point is **30 A/yoke at 50 %
duty with 30 V of headroom** — comfortable, not marginal.

Three things still need attention:

1. **Measure the yoke.** R, L and k. Everything dynamic hangs on numbers nobody has measured.
2. **The connector is dimensionally incompatible** with the specified 10 AWG wire.
3. **The bus energy-dump case was never calculated** and the existing 470 µF does not cover it.
