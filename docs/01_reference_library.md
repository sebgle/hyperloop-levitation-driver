# Reference Library — Levitation Coil Drive Stage

Every link below was opened and verified against its claimed content. Aggregator sites
(alldatasheet, datasheet4u, scribd, academia.edu) were rejected — first-party
manufacturer domains only. Items that could not be verified are listed as **not found**
rather than substituted with a guess.

Last verified: 2026-08-11

---

## 1. Gate drive

| Document | What it solves | Read |
|---|---|---|
| **IR2184 datasheet** (PD60174 Rev. G, Infineon/IR) ⚠️ *the link resolves to a file named `infineon-ir21844s-datasheet-en.pdf`; the IR21844 is a different part with an adjustable deadtime pin, so confirm this is the IR2184 before relying on it* · [PDF](https://www.infineon.com/assets/row/public/documents/24/49/infineon-ir21844s-datasheet-en.pdf) | The driver in the current BOM. 600 V floating channel, 1.4 A source / 1.8 A sink, programmable deadtime 280–520 ns. | The **V_BS UVLO 8.0–9.8 V rising** spec — this is what sets your bootstrap refresh requirement. And the **R_DT deadtime table**. |
| **AN-1123** *Bootstrap Network Analysis* (Infineon) · [PDF](https://www.infineon.com/assets/row/public/documents/24/42/infineon-bootstrap-network-analysis-applicationnotes-en.pdf) | **The single most important document for this design.** Quantifies why a bootstrap supply fails at high duty cycle. | **§2.2 pp. 5–6**: ΔV_BS = Q_TOT/C_boot, and Eq. 7 giving the duty-cycle boundary D < 4·R_boot·C_boot/T_S. **§3 pp. 11–13**: worked sizing examples. |
| **AN_2203** *Gate drive for power MOSFETs in switching applications* (Infineon, V1.0 2022) · [PDF](https://www.infineon.com/assets/row/public/documents/24/42/infineon-gate-drive-for-power-mosfets-in-switchtin-applications-applicationnotes-en.pdf) | Gate resistor selection and the alternatives to bootstrap. | **§4** gate drive voltage/current and R_G selection. **§6.1–6.7** floating/high-side drive: pulse transformers, half-bridge driver ICs, isolated drivers. |
| **SLVA444** *Providing Continuous Gate Drive Using a Charge Pump* (TI, Feb 2011) · [PDF](https://www.ti.com/lit/an/slva444/slva444.pdf) | The concrete fix if you must run 100 % duty. | **§3 pp. 4–6**, Figure 4 (NE555 charge pump) and Figure 6. |

> **Not found:** IR Design Tip **DT04-4**. Only aggregator copies exist; Infineon does not
> host the legacy IR design tips. AN-1123 + AN_2203 cover the same material.

---

## 2. MOSFET selection, loss and thermal

| Document | What it solves | Read |
|---|---|---|
| **IRF100B201 datasheet** (Infineon/IR, 2015) · [PDF](https://www.infineon.com/assets/row/public/documents/24/49/infineon-irf100b201-datasheet-en.pdf?fileId=5546d462533600a4015355f5c82f1b41) | The FET in the current BOM. 100 V, R_DS(on) 3.5 mΩ typ / 4.2 mΩ max, **Q_g 170 nC typ**, R_thJC 0.34 °C/W, TO-220AB. | **Fig. 10 p. 5** safe operating area. **Fig. 14 p. 6** transient thermal impedance — this is the curve you need for pulsed peak current. |
| **AND9083/D** *MOSFET Gate-Charge Origin and its Applications* (onsemi, Rev. 2) · [PDF](https://www.onsemi.com/pub/Collateral/AND9083-D.PDF) | Closed-form loss equations. | **Eq. 7** — switching loss for **inductive (hard-switched)** loads, which is your case: P_SW = ½·V_DD·I_D·(t_SW(ON)+t_SW(OFF))·f_SW. Eq. 4 gate-charge loss, Eq. 5–6 switching time from Q_SW, R_DR, R_G. |
| **AND8220/D** *How To Use Thermal Data Found in Data Sheets* (onsemi, Rev. 1 2022) · [PDF](https://www.onsemi.com/download/application-notes/pdf/and8220-d.pdf) | Why R_thJA numbers mislead, and how to build an honest junction-to-ambient budget. | **pp. 6–7** θ_JA vs. copper area curves per copper weight. **pp. 3–4** worked heatsink example. |
| **AN-949** *Current Rating of Power Semiconductors* (Vishay Siliconix, doc 91419) · [PDF](https://www.vishay.com/docs/91419/appnote9.pdf) | Sanity check against over-trusting datasheet current ratings. | Notes that typical TO-220/TO-247 heatsinking yields only **60–70 % of rated current at 40 °C ambient**. The IRF100B201's headline 192 A is not a real number. |

---

## 3. Current sensing

| Document | What it solves | Read |
|---|---|---|
| **INA240 datasheet** (SBOS662C, TI) · [PDF](https://www.ti.com/lit/ds/symlink/ina240.pdf) | The sense amp in the current BOM. CM range −4 V to +80 V (your 60 V bus fits), DC CMRR 132 dB, **AC CMRR 93 dB at 50 kHz**. | **§8.3.1.1** how the enhanced PWM rejection works. **§9.2.1** a worked inline motor current-sense design. |
| **SBOA174D** *Current Sensing in an H-Bridge* (TI, rev. Apr 2023) · [PDF](https://www.ti.com/lit/sboa174) | **The decision document for where to put your shunt.** | **Table 2 + Figure 3**: high-side vs. in-line vs. low-side, with explicit trade-offs. Note that low-side is cheap but **cannot detect a shorted load**. |
| **SBOA172** *Current Sensing for Inline Motor-Control Applications* (TI, Oct 2016) · [PDF](https://www.ti.com/lit/pdf/sboa172) | Why inline sensing is hard, and measured evidence that the INA240 handles it. | Read alongside SBOA174 **before** committing to inline sensing at 32 kHz. Also the source for the input RC filtering approach. |
| **Vishay doc 30405** *TCR for Current Sensing* (white paper, Rev. May 2020) · [PDF](https://www.vishay.com/docs/30405/whitepapertcr.pdf) | Shunt accuracy over temperature. | Key takeaway: at 1 mΩ the **copper terminations dominate TCR**, so spec the *component* TCR, not the element TCR. Also covers PCR self-heating drift and the Manganin/Zeranin/Evanohm comparison. |
| **Bourns e/N2210** *Using Current Sense Resistors for Accurate Current Measurement* · [PDF](https://www.bourns.com/docs/technical-documents/technical-library/current-sense-pulse-power-high-power-resistors/application-notes/bourns_n1702_current_sense_accurate_measurement_appnote.pdf) | Practical Kelvin layout. | **Figures 3–6**, the four-wire connection geometry. This is the part people get wrong in KiCad. |

> **Not found:** a first-party resistor-vendor app note covering shunt **parasitic
> inductance (ESL)**. Bourns, Vishay and Isabellenhütte all cover Kelvin, TCR and
> self-heating but none address ESL. At 15–30 A with 32 kHz edges this matters; the
> mitigation (reverse-geometry or four-terminal metal-strip element + input RC filter) is
> covered in SBOA172 instead.

---

## 4. Inductive-load drive topology

| Document | What it solves | Read |
|---|---|---|
| **SLVA321A** *Current Recirculation and Decay Modes* (TI, rev. Apr 2021) · [PDF](https://www.ti.com/lit/pdf/slva321) | **The justification document for the topology choice.** The definitive short treatment of coast-vs-brake. | **§2.1 + Fig. 2-1** fast decay · **§2.2 + Fig. 2-3** slow decay · **§2.3 + Fig. 2-5** mixed decay. |
| **SLVAE59A** *Using Motor Drivers to Drive Solenoids* (TI, Apr 2022) · [PDF](https://www.ti.com/lit/pdf/slvae59) | The closest published analogue to driving an electromagnet coil. | **§3.1 peak-and-hold current control** — energize hard, then hold at low current to cut dissipation. Directly relevant to the 1800 W coil dissipation problem. **§2.1** freewheel/flyback paths, **§3.2** fast-discharge clamping. |

---

## 5. Bus protection

| Document | What it solves | Read |
|---|---|---|
| **Littelfuse MIDI HP, 70 V-SF36** bolt-down fuse · [PDF](https://www.littelfuse.com/assetdocs/littelfuse-datasheet-4998-midihp70v?assetguid=b72fcd7a-c66d-4916-844c-ac55ebed196c) | **The correct fuse family for a 60 V DC bus.** 70 V DC, 30–200 A, 2500 A interrupting at 70 V DC, M6 bolt-down. | **Time-current curve, p. 3.** |
| **Littelfuse MIDI 32 V** bolt-down fuse · [PDF](https://www.littelfuse.com/assetdocs/midi-32v-bolt-down-series-data-sheet?assetguid=b55e8034-180d-40f6-a0a7-bebc2d4a94f5) | ⚠️ **Included as a warning, not a recommendation.** | This is what dominates search results and it is **rated 32 V DC — do not use it on a 60 V bus.** DC interrupting capability does not extrapolate upward. |
| **Littelfuse TVS application note** (automotive SAD, ©2023) · [PDF](https://www.littelfuse.com/assetdocs/tvs-diode-sad-silicon-avalanche-diode-application-note?assetguid=e4e5626b-a7b4-4098-8b9d-49424e2cfdcc) | TVS selection method: standoff voltage, breakdown, clamping, peak pulse power. | **pp. 6–10** the selection methodology with SOA curves. Limitation: framed around automotive load dump, so the *method* transfers but the *pulse waveforms* do not — your pulse is the coil energy dump. |
| **Littelfuse 5.0SMDJ series** TVS datasheet (Rev. 4, 2026) · [PDF](https://www.littelfuse.com/assetdocs/littelfuse_tvs_diode_5_0smdj_datasheet.pdf?assetguid=2b2f4a8c-2e81-4894-8d41-3d748bb79e68) | The numbers to actually pick a part. 5000 W at 10/1000 µs. | Full V_RWM / V_BR / V_C / I_PP table. **Fig. 2** power vs. pulse width, **Fig. 3** temperature derating. **5.0SMDJ70A** (V_R = 70.0 V) is the natural fit above a 60 V bus. |

> **Not found:** a Littelfuse **ANL** fuse datasheet. ANL is an Eaton/Bussmann style, not a
> Littelfuse series. The overview document's "125 A ANL/MIDI fuse" should become a MIDI HP
> 70 V part — and note that standard ANL fuses are commonly only rated 32 V or 80 V DC,
> which is a real problem on a 60 V pack that needs to interrupt a fault.

---

## 6. PCB current capacity

IPC-2152 itself is paywalled. These are the best legitimate free substitutes, both hosted
on IPC's own domain:

| Document | What it gives you | Limitations (stated honestly) |
|---|---|---|
| **The Value of IPC-2152**, M. R. Jouppi · [PDF](https://www.electronics.org/system/files/technical_resource/E7&S22_03.pdf) | **Actual conductor-sizing charts**: current vs. cross-sectional area with temperature-rise curves for ½, 1, 2 and 3 oz copper, still air and vacuum. | Conference paper, not the standard. No forced-air data. No flex charts. Missing Appendix A correction factors for board thickness, adjacent planes, via arrays. |
| **IPC-2152 front matter + full table of contents** · [PDF](https://www.electronics.org/TOC/IPC-2152.pdf) | Scope, definitions, and the complete figure list (Figs. 5-1…5-17 sizing charts; Figs. A-15…A-88 by copper weight). | Use this to decide whether buying the standard is worth it. Appendix A is exactly the heavy-copper derating material a 30 A design needs, and no free source reproduces it. |

Two counterintuitive results from the Jouppi paper worth knowing before you size the PDU
copper:

1. The old **IPC-2221 internal-conductor chart actually represents a conductor in free
   air** — which is why IPC-2221 has been simultaneously over- and under-conservative for
   decades. My first-pass numbers used IPC-2221 and should be re-derived against 2152.
2. **For the same cross-sectional area, 1 oz copper runs cooler than heavier copper.** A
   wider, thinner conductor spreads heat better. This cuts against the instinct to just
   ask the fab for 2 oz.

---

## 7. Published reference designs — triage

### Genuinely relevant

**TIDA-00365 — 75 V / 10 A Protected Full-Bridge Power Stage for Brushed DC Drives** ⭐ *best structural match*
https://www.ti.com/tool/TIDA-00365
75 V nominal / 100 V max bus · 10 A · discrete full bridge, four 100 V NexFETs, SM72295
100 V full-bridge gate driver with integrated current-sense amps, **bipolar high-side
current sensing**, ±1 % calibrated accuracy. 95 % efficiency at **16 kHz PWM, no heatsink
at 25 °C**.
*Full schematic (TIDRN75), BOM (TIDRN76), layout (TIDRN78), Gerbers (TIDCCJ2) and design
guide (TIDUBV7) all downloadable.*
**Why it matters:** voltage class, topology, PWM frequency and the bidirectional-sense
problem all line up with your design. Current is 10 A vs. your 15–30 A, so scale copper
and thermals — but the protection architecture and layout are directly transferable.

**TIDA-00620 — 12 V to 24 V, 27 A Brushed DC Motor Reference Design** ⭐ *best current-level match*
https://www.ti.com/tool/TIDA-00620
12–24 V bus · up to 27.5 A continuous, 343 W RMS · discrete N-channel H-bridge, 60 V
NexFETs at 1.8 mΩ, MCU-commanded, current sensing for protection.
*Design guide TIDUAW3, schematic TIDRI70, BOM TIDRI71, layout TIDRI73, Gerbers TIDCB82.*
**Why it matters:** the bus voltage is too low for your FET/driver selection to transfer,
but this is the best available reference for **27 A-class layout, shunt placement and
thermal handling** in a discrete H-bridge. Use TIDA-00365 for voltage, TIDA-00620 for
current density.

### Marginal — open only for layout and overcurrent-detection ideas

**TIDA-00436 — 36 V / 1 kW BLDC Drive with <1 µs Stall Current Limit**
https://www.ti.com/tool/TIDA-00436
30–42 V · 32 A RMS · **three-phase** bridge (not an H-bridge), 60 V NexFETs + DRV8303.
Wrong topology and wrong voltage. Worth a look only for its 32 A discrete-MOSFET layout
and its sub-microsecond stall detection, which is a reasonable model for coil fault
protection.

### Not relevant — skip

- **TIDA-01605** — isolated SiC gate driver board for 800 V automotive traction. The
  isolation and negative-bias complexity buy nothing at 60 V, where the IR2184 bootstrap
  approach is correct.
- **TIDA-00638** — reinforced-isolation IGBT gate driver for 400/690 V AC solar
  inverters. Mains-voltage isolation, IGBT-oriented, and a gate-driver brick rather than a
  bridge power stage.

---

## Two flags carried out of this research

1. **The IRF100B201's 170 nC gate charge is heavy for the IR2184's 1.4 A / 1.8 A output.**
   Gate-resistor and driver-loss calculations (AND9083 Eq. 4–6) should be done *before*
   committing to this pairing. This is a calculation, not an opinion, and it is on the list.
2. **The 32 V MIDI fuse that dominates search results is not rated for a 60 V DC bus.**
   The overview document's fuse selection needs revisiting on voltage rating, separately
   from the current-rating problem already noted.

---

## 8. PCB layout — the switching power loop

**Added 2026-08-24**, during layout, when `21_stackup_and_layers.md` §21.7 step 1
("commutation loops … on F.Cu") turned out not to be routable as written.

| Document | What it solves | Read |
|---|---|---|
| **SNVA803** *Improve High-Current DC/DC Regulator EMI Performance for Free With Optimized Power Stage Layout* (Timothy Hegarty, TI, September 2019) · [PDF](https://www.ti.com/lit/an/snva803/snva803.pdf) | The **vertical vs lateral power loop** — the decision behind returning bridge GND through the In1.Cu plane rather than running it beside the +60 V copper on F.Cu. | The vertical construction: layer 2 used as the power-loop return directly beneath the top layer, so the opposing currents give **field self-cancellation**. Quantified: switching loop area **2 mm² against almost 20 mm²**, parasitic loop inductance **below 500 pH against more than 1 nH**, and roughly **4 V** less switch-node overshoot. |

**Caveat, stated:** SNVA803 is written for a synchronous buck. Each leg of this H-bridge is a
half-bridge with the same commutation loop — high-side drain, low-side source, and the ceramics
across the bus — so the loop argument transfers directly. What does **not** transfer is anything
in it about the output inductor, the feedback network, or the IC-integrated power stage; this
board uses discrete TO-220s on a heatsink, which is a physically larger loop than the paper
assumes. Treat its 2 mm² as the direction, not the target.

> **Unresolved tension with §6.** The 10.7 mm pour width and the 10.7 mm `HV_POWER` DRC rule
> are both derived from **IPC-2221**, and §6 above already records that the IPC-2221 chart is
> effectively a free-air conductor and that these numbers should be re-derived against
> **IPC-2152**. That re-derivation has not been done. It is the same class of error as the
> unmeasured coil: a number in daily use resting on a source the project has already
> questioned in writing.
