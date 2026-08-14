# Adversarial review — full schematic, rev 0

Levitation coil drive board · Sebastian · 2026-08-14

Method: five independent hostile reviewers, each given only the extracted netlist and the
operating point, each instructed to break the design rather than bless it. Every surviving
finding was then re-checked against the primary manufacturer datasheet by a sixth reviewer
whose job was to REFUTE. Nine claims went to that pass; two came back overstated and one
came back with its recommended fix inverted. Those corrections are in §5 at the end.

Ground truth for connectivity is a fresh hierarchical netlist rebuilt from raw `.kicad_sch`
geometry — 83 nets, 414 component pins, four sheets, two instances.

**Bottom line: the connectivity is sound and nothing here is rework of what you drew.**
What the review found is a protection architecture that fails in the wrong direction, a
capacitor bank sized against a modulation scheme the thermal design does not use, and four
parts whose datasheets do not support what the design asks of them. Seven items should be
fixed before layout because they add or change parts. The rest are firmware, BOM lines, or
rev 1.

---

## 0. Scoreboard

| # | Finding | Sev | Cost to fix |
|---|---|---|---|
| **1** | Reset during a fault **re-enables** the bridge — 74HC74 with both async inputs low gives Q = H *and* /Q = H | CRITICAL | 1 gate, or relatch |
| **2** | RESET at 3.3 V is not a guaranteed HIGH into a 5 V 74HC74 | CRITICAL | 74HCT74, 1 BOM line |
| **3** | PWM low turns the **low side ON**, and the MCU has no way to command shutdown at all | CRITICAL | 1 gate + 1 pin |
| **4** | IR2184 IN pins float if +3.3 V drops; +3.3 V is the only rail with no hold-up | CRITICAL | 4 R + 1 D + 1 C |
| **5** | Bulk cap ripple: the bank is sized for one modulation scheme, the thermals for another | CRITICAL | firmware, or the bank |
| **6** | C101–C106 footprint is Ø18 mm; 470 µF/100 V does not exist in Ø18 | MAJOR | footprint swap |
| **7** | Shunt is a 1.0 W part; the design sheet specified ≥2 W | MAJOR | 0.5 mΩ + INA240A2 + R15 |
| 8 | FAULT is active-high push-pull — a dead board reads "healthy" | MAJOR | invert to open-drain |
| 9 | FAULT injects 9–19 mA into a 3.3 V MCU pin through 100 Ω | MAJOR | divider, or fold into 8 |
| 10 | SD driven at 5 V is outside the IR2184's recommended operating conditions | MAJOR | 1 resistor |
| 11 | No blanking, no threshold bypassing on the OCP comparators | MAJOR | 6 passives |
| 12 | LM393 is a 0–70 °C part on a 54 W board | MAJOR | LM2903B, 1 BOM line |
| 13 | TVS clamps at 113 V; the FETs are 100 V parts | MAJOR | see §13 — no clean fix |
| 14 | No bus voltage sense, no temperature sense anywhere | MAJOR | ~$0.25, 2 pins |
| 15 | VS has no series resistor and no VS→COM Schottky | MAJOR | 4 R + 4 D |
| 16 | Dead time 280 ns min vs an estimated 430–520 ns turn-off | INVESTIGATE | measure first |
| 17 | Bleed resistor marginal; τ = 62 s; 5.1 J stored with no indicator | MINOR | 2 × 2512 + LED |
| 18 | No reverse-polarity protection on a hand-bolted ring terminal | MINOR | system-level |
| 19 | J202 pinout: RESET adjacent to GND, ISNS pair adjacent | MINOR | repin, free |

---

## 1. The one that matters most — the fault latch is not set-dominant

The sheet annotation says *"FAULT LATCH — 74HC74, set-dominant."* It is not, and the
consequence is the opposite of what the annotation claims.

TI's SN74HC74 function table, third row:

```
 PRE   CLR   CLK   D         Q       /Q
  L     H     X    X         H       L
  H     L     X    X         L       H
  L     L     X    X       H (1)   H (1)

 (1) This configuration is nonstable; that is, it does not persist
     when PRE or CLR returns to its inactive (high) level.
```

On this board `/S` is FAULT_N, `/R` is RESET, and **`/Q` is the SD net**. So with a fault
present *and* RESET asserted, `/Q = H` → **SD high → both half-bridges enabled**, for as
long as RESET is held.

That is the exact sequence any sane firmware will write: *"OCP tripped → assert RESET →
wait → release → resume."* Against a persistent fault — a shorted coil, a failed FET, a
stalled pod — the reset pulse is a command to reconnect 60 V to the fault. It also fires at
every power-up, because R18/C22 hold RESET low for about 1 ms while the analog rails are
still coming up and FAULT_N is undefined.

Four of the five reviewers found this independently. Verified against the primary datasheet.

**Fix.** Make the reset physically impossible while a fault is live:
`/R_effective = RESET AND FAULT_N` — one 74HCT1G08 (SOT-353) per channel. Alternative: a
cross-coupled NAND latch, which is genuinely set-dominant. Either way the annotation text
has to change; it currently asserts a property the part does not have.

---

## 2. RESET is the one logic line with no level translation, and it needs one

Every PWM line gets a 74LVC2G17 Schmitt buffer. RESET gets a 100 Ω series resistor and
nothing else, straight into the `/R` pins of two 74HC74s running on +5 V.

74HC74 VIH is specified at only three rails — 1.5 V at VCC 2.0 V, **3.15 V at 4.5 V**,
**4.2 V at 6.0 V**. There is no 5.0 V row. VIH tracks 0.7·VCC, so at 5.0 V the requirement
is **3.5 V**, and at 5.25 V it is 3.675 V.

The node actually sits at (5.0 × 100 + 3.3 × 5000) / 5100 = **3.33 V** — the 3.3 V MCU
driving through R205 = 100 Ω against R18 ∥ R223 = 5 kΩ to +5 V. **170 mV short at a nominal
rail, and it only passes if the 5 V rail happens to run ≥5 % low.**

Indeterminate `/R` on its own would be bad. Combined with §1 it is worse: if `/R` reads as
asserted while a fault is present, `/Q` goes high and the bridge stays on through the
overcurrent, while FAULT still reads "faulted" to the MCU.

The circuit works today only because the power-on reset happens while the MCU pin is
high-Z. It fails in the mode firmware will actually use — driving the pin high to release
reset.

**Fix.** **74HCT74** — pin-identical, same package, same price, VIH = 2.0 V over
VCC = 4.5–5.5 V. One BOM line, zero layout change. Setting the MCU pin to open-drain is a
valid immediate mitigation but is not the fix.

---

## 3. "PWM low" is not "off", and there is no way to command "off"

From the IR2184's own parameter definition — this is how the datasheet names the row; there
is no printed truth table anywhere in it:

> **VIL** — *"Logic '0' input voltage for HO & logic '1' for LO"*

So IN low → HO low **and LO high** → the low-side FET turns **ON**. Three consequences.

**(a) The pulldowns give a defined state, not a safe one.** R201–R204 hold the four PWM
inputs low when the MCU is unplugged, not booted, or crashed. That puts all four low-side
FETs on — both coils short-circuited across the bridge, not tri-stated. At standstill that
is harmless. On a moving pod it is an uncommanded eddy brake plus total loss of lift
authority.

**(b) A single open PWM pin produces about 30 A of uncommanded DC current.** If PWM_A backs
out of J202, half-bridge A latches to GND while half-bridge B keeps switching at the last
commanded duty. The coil sees a DC average and the current runs up to V/R. At the stated
1 Ω that is 30 A at D = 0.5 — **below the 45 A trip, so no fault is ever reported.** One
yoke goes to a large uncommanded force with the telemetry reading normal.

**(c) The MCU cannot assert shutdown.** Tracing the netlist: SD is driven only by U5.6, and
RESET reaches only `/R`, which can only *clear*. U5.2 (D) and U5.3 (CLK) are tied to GND, so
the synchronous path is unused. The MCU's only way to stop the coil is to stop toggling
PWM — which per (a) turns both low sides on. The design intent says a trip makes the bridge
"tri-state, hard off." True for an OCP event; **false for every MCU-initiated stop, which is
the case that will actually happen.**

**Fix.** `SD_final = /Q AND EN`, with EN from the MCU and a 10 k pulldown on the board side.
One 74HCT1G08 per channel plus one J202 pin. Unplugged, unbooted or dead MCU → EN low →
genuine tri-state. The same gate then lets firmware run a power-up self-test of the whole
OCP chain before the pod takes load, which is the cheapest diagnostic available here.

---

## 4. +3.3 V is the fragile rail, and it is the one carrying the protection

+12 V has D201 + C201 (220 µF). +5 V has D202 + C202. **+3.3 V has neither.** It arrives
over a Micro-Fit from off-board with 100 nF decouplers and one 10 µF.

That rail carries: both INA240 supplies, both INA240 REF2 pins (the 1.65 V zero-current
point), both threshold dividers R14/R15/R16, and both 74LVC2G17 PWM buffers.

Four facts compound:

1. The 74LVC2G17 has Ioff partial-power-down — **its outputs go high-Z at VCC = 0.**
2. The PWM pulldowns R201–R204 are on the *connector* side of the buffer, so they do nothing
   for its output.
3. The nets PWM_A1 / PWM_B1 / PWM_A2 / PWM_B2 have exactly **two** pins each — buffer output
   and IR2184 IN. **There is no pulldown at the driver.**
4. The IR2184's IN pin has no internal pulldown (IIN− ≤ 1 µA).

So on a 3.3 V dropout: +12 V and +5 V ride through on their 220 µF, SD stays released, and
the four gate-driver inputs **float** with 60 V on the bus. Meanwhile ISNS, the 1.65 V
reference and both thresholds collapse together, so whether the OCP notices is a race
between two things falling at once. That indeterminacy is itself the finding — the safety
behaviour on loss of the most fragile rail is not designed, it is emergent.

**Fix — two parts, both already proven on the same sheet.** 10 k to GND on each of the four
PWM nets at the IR2184 IN pin, and SS34 + 220 µF on +3.3 V matching what the other two rails
already have. There is no defensible reason the two rails that only feed logic get hold-up
while the rail carrying the current reference and the trip thresholds does not.

---

## 5. The capacitor bank is sized for a modulation scheme the thermal design does not use

This one is my error in the earlier documents, and it is worth stating plainly.

`09_design_sheet_rev0.md` §4.1 sizes the FET losses under **"Antiphase (design to this)"**.
`13_schematic_review_power_channel.md` §3.1 sizes the capacitor bank on **15 A RMS per
channel** — which is the **sign-magnitude** number. The two sections designed against
different modulation schemes and nobody noticed, because the coil, the FETs and the ripple
were reviewed on different days.

The arithmetic, treating the coil as a DC source — its own ripple is 0.15 A pk-pk, so to the
bus it looks like a 30 A battery:

| Modulation | Bus AC ripple, 1 ch | 2 ch in phase | 2 ch interleaved 180° |
|---|---:|---:|---:|
| Locked antiphase, D = 0.75 | 25.98 A | **51.96 A** | 30.0 A |
| Sign-magnitude, D = 0.5 | 15.00 A | 30.0 A | **≈ 0** |

Note also that "30 A at 50 % duty" and "locked antiphase" cannot both be true — locked
antiphase at D = 0.5 puts zero average volts across the coil. For 30 V into 1 Ω the
antiphase duty is 0.75. The 50 % figure in the design sheet is a sign-magnitude duty.

Against that, six 470 µF/100 V cans provide roughly **8–14 A rms** depending on series
(see §6), before any allowance for imperfect sharing.

**So the bank is adequate for exactly one case — sign-magnitude with the two channels
interleaved 180° — and short by 2× to 4× for every other case.**

**The cheapest fix on the whole board is a firmware decision.** Commit to sign-magnitude,
interleave the two channels 180°, and the existing six cans are comfortable. It also roughly
halves the switching loss, because each bridge then hard-switches one leg instead of two.
You have a full H-bridge, so sign-magnitude still gives bidirectional current — the thing
the topology exists for. If locked antiphase is genuinely required for a control reason, the
bank has to change technology (polymer or film), not just count.

Either way this has to be written down as a **design commitment**, not left as an
assumption, because two sheets of this design currently depend on opposite answers.

---

## 6. The bulk capacitor footprint is for a part that does not exist

C101–C106 carry `Capacitor_THT:CP_Radial_D18.0mm_P7.50mm`.

Every mainstream 470 µF / 100 V part is **Ø16 mm**:

| Series | Part | Size | Ripple @ 105 °C, 100 kHz |
|---|---|---|---|
| Nichicon UPW | UPW2A471MHD | Ø16 × 30.5 | 1.31 A |
| Rubycon ZLH | 470 µF 100 V | Ø16 × 31.5 | **2.40 A** |
| Nichicon UVR | UVR2A471MHD | Ø16 × 25 | 1.00 A (85 °C part) |

Ø18 mm cases at 100 V are used for *adjacent* values — 390 µF, 560 µF, 1000 µF. A 470 µF /
100 V in Ø18 was not found in Nichicon UPW, Nichicon UVR, Rubycon ZLH or Panasonic FR-A.

Same class of error as the D2 SMA/SMC one: a footprint that will not take the part. Free to
fix now, a re-spin after routing.

**Fix.** `CP_Radial_D16.0mm_P7.50mm`, and specify **Rubycon ZLH** or another low-Z series —
the 2.4 A part gives 14.4 A of bank capability against the UPW's 7.9 A, for the same money
and the same board area. Given §5, that difference is what decides whether the bank has any
margin at all.

---

## 7. The shunt does not meet the design's own written requirement

`09_design_sheet_rev0.md` §4.4: *"Shunt — 1 mΩ, 4-terminal, **≥2 W**."*

Vishay WSK2512, verified: **1.0 W at 70 °C**, derating linearly to zero at 170 °C. TCR for
the 0.001–0.0029 Ω range is **±250 ppm/°C**.

| Condition | Dissipation | % of P₇₀ |
|---|---|---|
| 30 A design current, continuous | 0.90 W | **90 %** |
| 45 A trip threshold | 2.03 W | 203 % |
| 60 A device ceiling | 3.60 W | 360 % |

At 90 % of rating the element runs roughly 90 °C above its local ambient, on a board whose
heatsink edge is calculated above 100 °C. At that temperature ±250 ppm/°C gives about
**+2.6 % on the resistance** — and because it is driven by self-heating it is a
*current-dependent* shift, so it is a nonlinearity, not a calibratable gain error. For
scale, the INA240's own max gain error is 0.20 %. The shunt's thermal drift is thirteen
times larger than everything else in the chain combined.

**Fix.** Go to **0.5 mΩ WSK2512 + INA240A2 (gain 50)**:

- Dissipation drops to **0.45 W at 30 A** (45 % of rating) and 1.01 W at the trip.
- Same 2512 four-terminal Kelvin footprint, same amplifier pinout, same package.
- Scale becomes **25 mV/A**, not 20, so **one threshold resistor changes**: R15 24 k → **43 k**
  (R14 and R16 stay 10 k). That puts VTH_HI at 3.3 × 53/63 = 2.776 V and VTH_LO at
  3.3 × 10/63 = 0.524 V, i.e. a trip at **±45.05 A** — the same trip point as today.
- Full scale becomes ±66 A instead of the claimed ±82 A, which is a better match to the
  60 A device ceiling and lands inside the INA240's real guaranteed output swing.

**CORRECTION, same day:** the first version of this section claimed 0.5 mΩ × gain 50 kept
20 mV/A and left the divider untouched. That is wrong — 0.5 mΩ × 50 = 25 mV/A. Holding
20 mV/A at gain 50 would need a 0.4 mΩ shunt, and the WSK2512 does not go below 0.5 mΩ.
The corrected answer is above: keep 0.5 mΩ, change R15. My arithmetic error, caught while
writing the step-by-step plan.

The obvious alternative — WSLP2512 at 3.0 W — is **two-terminal**, which would undo the
whole Kelvin fix from 08-13. Do not take it.

---

## 8–10. The J202 boundary fails toward "healthy"

**8. FAULT is active-high push-pull from a +5 V rail.** So: board unpowered → reads no
fault. Wire broken → reads no fault. Connector unplugged → reads no fault. +5 V lost → both
channels are dead (R19 correctly pulls SD low) and **both FAULT flags read healthy.**

Combine that with the fact that a dead INA240 stuck mid-scale reads exactly 1.65 V — which
is arithmetically identical to "commanded zero current, working fine" — and the board has
**two telemetry signals and both of them fail toward OK.** An open coil, a backed-out pin, a
lost rail and a dead sensor all produce the same reading as a healthy idle channel.

**Fix.** Invert to open-drain active-LOW, pulled up at the MCU's own 3.3 V. Then rail loss,
broken wire, backed-out pin and unplugged connector all assert. Highest-value change in this
section, and it removes finding 9 for free.

**9. 5 V logic into a 3.3 V MCU pin through 100 Ω.** 74HC74 VOH at light load is about
4.9 V, so injection into the MCU's clamp is (4.9 − 4.0)/100 = **9 mA nominal, 19 mA worst
case**. ST specifies I_INJ for FT/TT pins as **−5 / 0 mA** — positive injection is not
permitted at all. Two fault lines is up to 38 mA back-fed into the MCU's rail, enough to
partially power an unpowered MCU. Fix: 10 k / 15 k divider, or fold into finding 8.

**10. SD at 5 V is outside the IR2184's recommended operating conditions.** Verified — and
the datasheet contradicts itself here. The front page advertises *"3.3 V and 5 V input logic
compatible"* while the Recommended Operating Conditions table says
`VIN (IN & SD) = VSS to VSS + 4 V`, with absolute maximum `VSS + 5 V`. A 5 V drive sits *at*
the absolute maximum with zero margin for ringing or ground offset. Fix: 2.2 kΩ in series
between U5.6 and the SD net, against the existing R19 10 k pulldown → about 3.9 V, inside
the 4 V limit and still 1.2 V above the 2.7 V threshold.

---

## 11–12. The OCP comparator path

**11. No blanking, no hysteresis, no threshold bypassing.** The comparators tap ISNS
directly; the 100 Ω / 100 nF filter is on the telemetry path to the connector and does
nothing for protection. VTH_HI and VTH_LO sit at a 7.7 kΩ Thévenin impedance with **no
bypass capacitors at all**, on a board with a 60 V node slewing at roughly 0.5 V/ns.

The margin being defended is small. At 30 A, ISNS is 2.25 V against a 2.55 V threshold —
300 mV at the output, **15 mV referred to the shunt.** That is the entire disturbance budget
for a node whose common mode is a 0–60 V square wave.

And the design is refusing free margin to get it. With L = 9.25 mH and 60 V available, the
current climbs from the 45 A trip to the 60 A ceiling in **2.3 milliseconds**. The
protection could be delayed by 2 ms and still catch every coil-limited overcurrent. It
currently has zero deliberate delay, and total existing latency (INA240 settling + LM393
response) is already 4–11 µs, so nothing is being preserved by leaving it unfiltered.

**Fix, six passives.** 100 nF on each threshold node; 1 kΩ + 4.7 nF between ISNS and the
comparator inputs (4.7 µs, costing 0.03 A of overshoot); about 10 MΩ of hysteresis from each
comparator output back to its non-inverting input.

**12. The LM393 is a 0–70 °C part.** Verified — the base LM393 grade is 0 °C to 70 °C. This
board dissipates 53.8 W with four TO-220s per channel on a 160 × 100 mm card at a 40 °C
target ambient. **LM2903B** is pin-identical and graded −40 to +125 °C. One BOM line.

Its input common-mode ceiling — V+ − 2.0 V = 3.0 V over temperature — is genuinely violated
only above about 67 A, by which point the trip should long since have fired. Real, but do
not rank it above the temperature grade.

---

## 13. The TVS cannot protect the FETs, and no part in the series can

5.0SMDJ70A, verified: V_RWM 70 V, V_BR 77.8–86.0 V, **V_C = 113 V at I_PP = 44.3 A**.
The IRF100B201 is a **100 V** part.

| Part | V_RWM | V_BR min | V_C | Verdict on a 60 V bus with 100 V FETs |
|---|---|---|---|---|
| 5.0SMDJ58A | 58 | 64.4 | 93.6 | clamps low enough, **stands off less than the bus** |
| 5.0SMDJ60A | 60 | 66.7 | 96.8 | standoff exactly equals bus max |
| 5.0SMDJ64A | 64 | 71.1 | 103.0 | standoff OK, **clamp above the FET** |
| **5.0SMDJ70A (fitted)** | 70 | 77.8 | **113.0** | standoff OK, clamp 13 V above the FET |

The usable window between "the TVS starts conducting" (77.8 V) and "the FET is over rating"
(100 V) is 22 V wide, and one 5.0SMDJ70A only reaches **28 A** at 100 V. The trip is at
45 A. **This is not a part-selection error you can order your way out of** — a 60 V bus with
100 V FETs and a 45 A trip is not protectable by a single-stage TVS.

The energy arithmetic, for calibration: 45 A in 9.25 mH is 9.37 J, of which about 6.1 J
reaches the bus after coil resistance and body-diode drops. Into 2820 µF from 60 V that is
an **89 V** peak for a single-channel trip — survivable, with 11 V of margin, so the
existing "accepted for rev 0" note is defensible *for that case*. **Both channels tripping
together** gives 96–111 V, straddling the FET rating, and that is not exotic: a bus fault, a
control fault or a shared-rail glitch produces it.

**Options, honestly.**

- (a) Accept it, document the single-channel case as the design basis, and add the bus
  voltage sense from §14 so you can at least see when it happens.
- (b) Move to 150 V FETs at rev 1. A 100 V part on a 60 V hard-switched bridge is only 1.67×
  derating, which is thin before you add a fault.
- (c) Build the slow-decay-on-fault circuit of review §3.2, which removes the dump entirely
  and is what the +12 V and +5 V hold-up caps were already fitted for. **(c) is the right
  answer and it is still undesigned.**

---

## 14–15. Two things that are missing rather than wrong

**14. No bus voltage sense and no temperature sense.** Neither net exists anywhere in the
design. So the MCU cannot verify precharge, cannot detect a welded or open contactor, cannot
see the overvoltage event of §13 even after it happens, cannot compensate its own loop gain
against a battery that swings 20–25 % from full to empty, and cannot detect a heatsink screw
backing out, a silpad pumping out, or a blocked airway. Two dividers, one NTC, two J202
pins, about a quarter of a dollar.

**15. VS has no series resistor and no VS→COM Schottky.** U1.6 ties straight to SW_A with
nothing in between. The IR2184's own note is explicit: *"Logic operational for VS of −5 to
+600 V."* To stay inside −5 V at a 30 A commutation with 0.3–0.65 A/ns of di/dt, the loop
inductance between the low-side source and COM has to be under **8–17 nH**. A single TO-220
lead is about 7 nH, and these are through-hole parts in a row with the bulk cans necessarily
some distance away. Four resistors (4.7–10 Ω) and four Schottkys per board. This is standard
on every IR21xx reference design, and its absence is the classic field-failure mode for the
family.

---

## 16. One thing to measure rather than fix

**Dead time.** Verified: `DT = 280 ns min / 400 typ / 520 max, RDT = 0, CL = 1000 pF,
TA = 25 °C`. The widely quoted "500 ns" is IR's marketing descriptor, not a table value —
and the table is a 25 °C-only spec taken with a 1000 pF load. Your gate load is
Ciss = 9500 pF.

Two independent estimates of the IRF100B201's turn-off through this network — one scaling
the datasheet's own `td(off) + tf` by the loop-resistance ratio, one charge-based at 30 A —
land at **430–520 ns**, against a **280 ns** minimum dead time. The dominant uncertainty is
the IR2184's output impedance, which the datasheet does not publish (only IO− = 1.8 A min).

I am not going to tell you the bridge shoots through, because that estimate has a real error
bar and plenty of IR2184 designs work fine. But the margin is not demonstrable from the
datasheets, and it gets worse at 32 kHz than at 16 kHz, and worse hot than cold.

**Action: measure it on the first board** — gate waveforms on both FETs of one leg at 30 A,
hot. If it is tight, the escape hatch is the **IR21844**: same family, SOIC-14, dead time
programmable with one resistor. Worth laying out so that swap stays possible.

---

## 17–19. Minor

**17. Bleed resistor.** R101 at 22 k dissipates 164 mW. A 1206 is 250 mW at 70 °C, derating
to about 162 mW at 100 °C — right at the edge next to a hot heatsink. A thick-film resistor
run at its limit fails **open, silently**, after which the bus never bleeds at all. τ = 62 s
means 2.6 minutes to 5 V, with 5.1 J stored at 60 V. Fix: two 10 k 2512 in series, plus a
bus-present LED so the discharge state is observable by whoever is unbolting the terminals.

**18. Reverse polarity.** J101 is a ring-terminal block a technician bolts by hand.
Reversed, the TVS is a forward diode across the pack, all eight body diodes conduct in
series pairs, and six electrolytics are reverse-biased. This is a system-level item — the
harness fuse decided this morning does not prevent it — but it should become an explicit
written assumption that the pack side is keyed and cannot be reversed.

**19. J202 pinout.** RESET (pin 7) is adjacent to GND (pin 6): one whisker holds `/R`
asserted forever, which per §1 and §2 defeats the OCP while FAULT still reads healthy.
ISNS1 (10) and ISNS2 (11) are adjacent: a short makes both channels report the same averaged
current, so both yokes get corrupt feedback simultaneously — exactly the correlated failure
that redundancy analysis assumes cannot happen. Repinning is free, and if you take the EN
pin from §3 you are going to 16-way anyway, which is the moment to do it.

---

## 4a. Corrections to my own earlier documents

Recorded here because these documents are the record:

1. **`15_sheet_annotations.md`, FAULT LATCH block** says *"74HC74, set-dominant."* It is
   not. Rewrite before that text goes on the sheet.
2. **The ripple/modulation contradiction in §5 is mine** — two sections of
   `09_design_sheet_rev0.md` and `13_schematic_review_power_channel.md` designed against
   different modulation schemes.
3. **`14_power_channel_closeout.md` §3** says a 16 mm can at 470 µF/100 V "is unusual." The
   opposite is true: 16 mm is the only size the value exists in, and the 18 mm footprint now
   on the board is the anomaly.
4. **Today's earlier log entry** says the eight TO-220 tabs sit at "six different
   potentials." It is **five** — four tabs at +60 V, plus four distinct switch nodes.

---

## 5a. What the verification pass killed

Not everything the reviewers found survived. Recorded so the same claims do not come back:

| Claim | Verdict |
|---|---|
| "Move the 74LVC2G17 buffers to +5 V — free fix for the IR2184 VIH margin" | **Wrong, and it would have made things worse.** The IR2184's recommended max input is VSS + 4 V. 3.3 V is the compliant choice; 5 V is not. The 500 mV VIH margin at 3.3 V is real, but it is the correct side of the trade |
| "INA240 driving 100 nF exceeds its 1 nF max capacitive load → oscillation" | **Overstated.** The 1 nF spec governs capacitance driven *directly* off the pin; a series resistor ahead of it is the standard isolation technique. Downgraded to a bandwidth/impedance note |
| "No fuse on the board" | Not a defect — the fuse moved to the harness by decision this morning. It does have to actually exist there |
| "The heatsink cannot work at tube pressure" | Speculation until someone says whether the electronics bay is pressurised. A **question to ask**, not a finding |
| "LM393 common-mode range is violated" | True only above about 67 A, past where the trip should have fired. The temperature grade is the real issue |
| "500 ns dead time" | Neither the reviewers' 280 ns alarm nor the design's 500 ns comfort — 280/400/520 at 25 °C with a 1000 pF load. See §16 |

---

## 6a. Suggested order

**Before layout** — these change the schematic: **1, 2, 3, 4, 6, 7**, and the modulation
commitment in **5**. Then 8/9/10 and 11/12 while you are in there; between them that is
about twelve passives and two BOM lines.

**Decisions that need a person, not a resistor:** the modulation scheme (§5); whether to
accept §13 or finally build the slow-decay circuit; and whether the pod's electronics bay is
at atmospheric pressure.

**Rev 1:** more FET voltage headroom, a watchdog, isolation, and a DC-link current sense
that can see the bridge-internal faults the in-line shunt is structurally blind to.

Nothing above requires redrawing what you have. The netlist was right; the parts around it
need to catch up with it.

---

## Sources

Primary datasheets fetched and quoted during this review: Infineon IR2184(4)(S) ·
Infineon IRF100B201 · TI SN74HC74 and Nexperia 74HC/HCT74 · Nexperia 74LVC2G17 ·
TI INA240 · TI LM393 · Vishay WSK2512 and WSLP2512 · Vishay ES1D and SS34 ·
Littelfuse 5.0SMDJ · Nichicon UPW and UVR · Rubycon ZLH · United Chemi-Con KY ·
Vishay CRCW e3 · Bergquist Sil-Pad 400 / 2000 / K-10 · Molex 38969-0002 ·
STMicroelectronics STM32F407 and STM32G474.
