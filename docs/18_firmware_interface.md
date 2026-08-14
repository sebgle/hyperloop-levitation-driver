# Levitation coil drive board — firmware interface

Rev 0 · 2026-08-14 · one board drives **2 yokes**; the pod uses **two identical boards**.

Read this before writing the control loop. Three things changed on 2026-08-14 that firmware
cannot discover by probing, and **two of them will present as a dead board** if you don't
know about them:

1. **`EN` is new and defaults to off.** No EN, no output. The board will look dead.
2. **`FAULT` became `OK` and the polarity inverted.** HIGH is healthy now.
3. **The current scale changed to 25 mV/A** (was 20). Old firmware reads 25 % low.

---

## 1. Connector J202 — Molex Micro-Fit 3.0, 2×8, part 43045-1600

Mating half for the harness: **43025-1600** housing + 16 crimp terminals.

| Pin | Signal | Dir | Notes |
|---|---|---|---|
| 1 | GND | — | |
| 2 | GND | — | |
| 3 | PWM_A1 | in | channel 1, leg A |
| 4 | PWM_A2 | in | channel 2, leg A |
| 5 | PWM_B1 | in | channel 1, leg B |
| 6 | PWM_B2 | in | channel 2, leg B |
| 7 | GND | — | |
| 8 | GND | — | |
| 9 | **EN1** | in | channel 1 enable — **must be driven HIGH** |
| 10 | **EN2** | in | channel 2 enable — **must be driven HIGH** |
| 11 | RESET | in | active LOW, clears both fault latches |
| 12 | **OK1** | out | **HIGH = healthy** |
| 13 | GND | — | |
| 14 | **OK2** | out | **HIGH = healthy** |
| 15 | ISNS1 | out | analog, 1.65 V ± 25 mV/A |
| 16 | ISNS2 | out | analog |

All logic is 3.3 V compatible. Inputs go to TTL-threshold parts (74HCT, V_IH = 2.0 V), so a
3.3 V push-pull GPIO is fine on every one — including RESET, which used to need care.

Rails arrive separately on **J201**: +12 V, +5 V, +3.3 V, GND. The board generates nothing.

---

## 2. EN — the new hardware interlock

`SD_final = (no fault) AND EN`. Either condition alone shuts the bridge down.

- On-board **10 kΩ pulldown**. Unplugged, unbooted or crashed MCU ⇒ EN low ⇒ both
  half-bridges tri-state. That is the intended safe state.
- Per channel, so you can disable one yoke without touching the other.
- **You must drive EN high before any PWM has an effect.** There is no way to command the
  bridge on without it.

### Use it for a power-up self-test — this is free and you should do it every boot

```
1. EN = 0, PWM idle.        Read OK.  Expect LOW.
2. EN = 1.                  Read OK.  Expect HIGH.
3. EN = 0.                  Read OK.  Expect LOW again.
4. Only now enable PWM.
```

That verifies the entire shutdown path — gate, latch, and driver enable — before the pod
takes load. If step 2 does not produce a HIGH, do not proceed: either the +5 V rail is
missing, the latch is stuck, or a fault is already asserted.

---

## 3. OK — polarity is inverted from the old FAULT signal

| Condition | OK reads |
|---|---|
| Enabled, no fault | **HIGH** (~3.0 V) |
| Over-current latched | LOW |
| EN commanded low | LOW |
| +5 V rail lost | LOW |
| Board unpowered | LOW |
| Connector unplugged / wire broken | LOW *(enable your internal pulldown)* |

The point of the inversion: every failure mode now reads *not healthy*. Under the old
active-high FAULT signal, an unpowered board, a broken wire and an unplugged connector all
read "no fault" — indistinguishable from a healthy idle channel.

**Enable an internal pulldown on the OK pins** so a broken wire reads LOW rather than
floating. This is required for the above table to hold.

Note OK is `enabled AND no-fault`, not just `no-fault` — so it goes low when *you* command
EN low. That's deliberate: it's a readback of the actual bridge state, not just the latch.

---

## 4. Current sense — scale changed

    ISNS = 1.65 V + (25 mV/A × I)

    zero current   1.65 V
    +30 A          2.40 V
    −30 A          0.90 V
    full scale     ±66 A  (clipped by the amplifier's output swing)
    trip           ±45 A  → 2.775 V / 0.525 V

**Sign convention:** ISNS **above** 1.65 V means current flowing out of leg A, through the
shunt, into the coil, and back through leg B. That corresponds to **D > 0.5** (see §5).

**Ratiometric.** The 1.65 V zero point and both trip thresholds derive from the same +3.3 V
rail. **Use that same rail as your ADC reference** — if you use an internal reference or a
separate LDO, rail error stops cancelling and you get ±4 A of zero offset for a 5 % mismatch.

**Filtering.** 100 Ω + 100 nF at the connector ⇒ 15.9 kHz corner, ~10 µs group delay. That's
about 3.6° of phase at 1 kHz — negligible for the current loop. Source impedance is 100 Ω,
far inside any ADC's limit.

**Calibrate the zero at every startup** with EN low. It costs nothing and it catches a dead
amplifier — see §7.

---

## 5. Modulation — committed, not a free choice

**Unipolar (3-level) PWM, and the two channels interleaved 90°.**

```
   PWM_A = D
   PWM_B = 1 − D

   V_coil = 60 V × (2D − 1)      D = 0.5 → 0 V, zero current
                                 D > 0.5 → positive current (ISNS > 1.65 V)
```

The IR2184 generates each leg's complement internally and enforces its own dead time, so you
drive **one signal per leg** and never both halves of a bridge.

**The 90° interleave is a hardware requirement, not an optimisation.** Channel 2's carrier
must be phase-shifted a **quarter** period from channel 1's — not half. Under unipolar the
bus draws current twice per carrier period, so the ripple fundamental is at 2·f_sw; a half-
period shift is a full cycle of that and cancels nothing. The bulk capacitor bank is sized on the
assumption that the two channels' bus current pulses do not coincide. A half-period shift, or no offset at all, leaves the bus ripple at 30 A rms against a bank rated 14 A, past what the bank can carry — see A14 in
`09_design_sheet_rev0.md`.

**Do not use locked antiphase.** It needs ~52 A rms of bus ripple against a bank rated for
about 14 A.

**Do not use sign-magnitude.** It has the right ripple but a deadband at zero current, and
with the magnets carrying static weight the coil trims *around* zero — the loop would live
exactly on the discontinuity.

Dead time distorts both legs under unipolar, so expect a small duty-dependent error near
D = 0.5. It is a calibration, not a topology problem.

Switching frequency 16–32 kHz. The coil sees +V/0/−V at **2× f_sw**.

---

## 6. Over-current protection

- Trips at **±45 A**, hardware, no firmware involvement.
- **Latching.** It will not self-clear when the current falls.
- On trip: both half-bridges of that channel tri-state. The other channel is unaffected.
- Clear by pulsing **RESET low**.

### Two things about RESET you must design around

**RESET is shared between both channels.** One pin, both latches. Clearing a fault on
channel 1 also clears channel 2 — including a channel-2 fault you have not read yet. **Read
both OK lines before you reset either.**

**RESET is blocked while a fault is live.** The latch is gated: a reset only takes effect
once the over-current has actually gone away. This is deliberate — it stops the classic
retry loop from reconnecting 60 V into a persistent fault.

So the retry sequence is:

```
1. OK goes low.
2. Stop PWM. Optionally drop EN.
3. Wait for the coil to decay (τ = L/R ≈ 9 ms; allow 50 ms).
4. Pulse RESET low for ≥ 1 ms.
5. Release RESET, then WAIT 10 ms before reading OK.      <-- see timing note
6. Read OK. Still low ⇒ the fault is persistent. Do not loop indefinitely —
   bound it (3 attempts) then latch in firmware and report.
```

**RESET timing — the release is slow, the assert is fast.** The RESET net carries a
power-on-reset RC of 5 kΩ × 2 µF = **10 ms**. Pulling it low is quick (100 Ω series), but on
release it takes about **5 ms** to cross the logic threshold and the latch is not armed until
then. So:

- assert: hold low ≥ 1 ms
- release: **wait 10 ms before trusting OK or enabling PWM**

That RC exists to hold the latch clear through power-up while the over-current thresholds
settle (they have their own 0.84 ms time constant). Do not shorten it in firmware by driving
RESET high — drive it low to assert, then release to high-Z or high and respect the delay.

Do **not** hold RESET low continuously hoping to ride through. It will not work, and if the
gating were ever removed it would be actively dangerous.

---

## 7. What the board cannot tell you — plausibility checks are on you

There is no bus voltage sense, no temperature sense, and no gate-driver fault feedback. Two
signals per channel is all the telemetry there is. Some failures produce **ISNS = 1.65 V and
OK = high**, which is bit-for-bit identical to "healthy, commanded to zero current":

- current-sense amplifier failed mid-scale
- coil open circuit, or a coil connector backed out
- a PWM pin backed out (see below)

Cheap firmware checks that close most of this, all zero hardware cost:

| Check | Catches |
|---|---|
| Commanded \|V_coil\| > 5 V for > 30 ms but \|ISNS − 1.65\| below a floor | dead sensor, open coil |
| \|I\| > 45 A read for > 2 ms | impossible — the OCP would have tripped. Sensor or wiring fault |
| ISNS pegged at 0 V or 3.3 V | sensor rail fault, or a disconnected ISNS pin |
| Both channels reporting *identical* current | shorted ISNS pins in the harness |
| OK low while EN high and no recent trip | rail loss |
| Startup zero-current calibration outside 1.65 V ±50 mV | 3.3 V rail or amplifier fault |

**One specific hazard worth coding against.** If a single PWM pin loses contact, that leg
latches to ground while the other keeps switching. The coil sees a DC average and the current
runs to roughly 30 A — **below the 45 A trip, so nothing reports it.** The plausibility check
that catches it is commanded-duty versus measured-current: if they disagree by a wide margin
for more than a few milliseconds, shut that channel down in firmware.

---

## 8. Startup and shutdown sequence

**Startup**

```
1. Rails up (+12 V, +5 V, +3.3 V). Board comes up with EN low, bridge off.
2. MCU boots. Drive EN low explicitly, PWM idle.
3. Pulse RESET to clear any power-on latch state.
4. Run the §2 self-test.
5. Calibrate ISNS zero (EN still low).
6. EN high, PWM at D = 0.5 (zero current).
7. Close the loop.
```

**Shutdown** — drop **EN**, do not just stop toggling PWM. With PWM idle and EN still high,
both low-side FETs turn on and the coil is short-circuited across the bridge. That is a
braking short, not a safe state. EN low genuinely tri-states.

---

## 9. Known rev-0 limitations

- **No watchdog.** If the MCU crashes mid-PWM the last commanded duty persists indefinitely.
  Nothing on the board notices. Consider a heartbeat that firmware must service, with EN
  driven from it.
- **Hard-off on over-current.** The coil freewheels into the bus through the body diodes. A
  single-channel trip takes the bus to ~89 V against 100 V FETs — acceptable. Both channels
  tripping simultaneously reaches 96–111 V, which straddles the rating. Avoid designing any
  control behaviour that trips both channels at once.
- **The shunt cannot see shoot-through.** It is in the coil path, not the leg. A shorted FET
  or a gate-driver fault is invisible to the OCP.
- **Coil L, k and R are still unmeasured.** Every number here that involves the coil —
  τ = 9 ms, the 2.3 ms from trip to ceiling — assumes 1 Ω and 9.25 mH per yoke.

Full analysis in `16_adversarial_review.md`.
