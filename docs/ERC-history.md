# LocalCam-1 Rev A — KiCad project

**Requires KiCad 8 or newer.** The schematic is written in KiCad 7 format (so 7/8/9 all
read it), but Luckfox's official Core1106 **footprint** is KiCad 8 format
(`version 20240108`) and will not load in KiCad 7.

**Validated with KiCad's own parser** (`kicad-cli sch export netlist`): the schematic
loads, and the netlist KiCad derives from it matches `spec.py` exactly — 36 nets,
28 components, every footprint assigned.

**`spec.py` is the source of truth.** It holds every part and every net.
`LocalCam1.kicad_sch` is a build output — regenerate it, don't hand-edit it:

    python3 gen.py

The schematic uses **global labels on every pin** rather than drawn wires, so it
is clean by construction: no junctions, no crossings, no floating segments.

## Design rules baked in
- The Core1106 has an **onboard PMIC**. Feed 5 V to `VCC5V0_SYS` (pads 79/80/81).
  `VCC_3V3` (78) and `VCC_1V8` (77) are **outputs** — never drive them. No external buck.
- Pads **37–46** (eMMC) and **48/63/68** (WiFi control) are used internally — do not route.
- Debug UART is **UART2 on the M1 mux** (pads 72/73); the M0 mux collides with the SD bus.
- Recovery is an ADC key on `SARADC_IN0` (pad 26), or `reboot loader` in software.
- microSD works, but card-detect (pad 48) is taken by the WiFi — mark the slot non-removable.
- J3 is our own camera FPC; grounds flank each differential pair.

## Net classes (pre-set in the .kicad_pro)
`MIPI_100R` for `CSI_*` (100 Ω differential) · `USB_90R` for `USB_D*` (90 Ω) ·
`Power` for the rails · `Default` for everything else.

## Audit findings applied (Rev A, pre-layout)
| # | Finding | Fix |
|---|---|---|
| 1 | Camera I²C pull-ups went to **+3V3**, but pads 13/14/15/18/19 are a **1.8 V IO bank** (VCCIO7, "1.8V only") — over-drives the inputs | R5/R6 now pull to **+1V8** (pad 77, a module output). `+1V8` also routed to J3-21 so the camera board shares one 1.8 V I/O reference |
| 2 | **USB_VBUSDET (pad 24) floating** — module cannot detect USB presence | R7/R8 100 k 2:1 divider from +5V into pad 24 (`VBUS_DET`) `[verify divider ratio vs RV1106 datasheet]` |
| 3 | `ADC0_RECOV` is a **1.8 V SARADC input** brought to a header next to +3V3 — over-voltage hazard | R9 1 k in series (`RECOV_HDR` on the header) |
| 4 | TVS **SMAJ5.0CA**: V_RWM = 5.0 V vs VBUS max 5.25 V — sits in the leakage knee at normal operating voltage | **SMAJ6.0CA** (V_RWM 6.0 V > 1.05 × 5.25 = 5.51 V) |
| 5 | No decoupling on **+3V3** at the FPC, or at the **microSD** VDD | C3/C4 (10 µF + 100 nF) at J3; C5/C6 at J2 |
| 6 | Bulk **10 µF** gives ~2 V droop for a 0.4 A WiFi TX step over 50 µs | C1 → **47 µF** (~430 mV; add more if bring-up shows brownouts) |
| 7 | LED resistor 1 k → 0.3 mA with a green/blue LED (invisible) | **330 R** + red LED specified (~4 mA) |

### Confirmed correct (no change)
- **5.1 kΩ ×2 CC pulldowns**, one per CC pin — USB Type-C R2.0 Table 4-25 Rd for a sink.
- **4.7 kΩ I²C pull-ups**: t_r = 119–199 ns at 30–50 pF, inside the 300 ns fast-mode limit; R_min at 1.8 V is 533 Ω, so 4.7 k is safe.
- **3V3 budget**: 0.26 A external + ~0.3 A RV1106 IO = 0.56 A against the module buck's ~1.6 A → 2.9× margin.
- **Polyfuse 1.5 A hold**: load ~0.79 A at 5 V; derated 1.08 A at 60 °C (1.4×). Marginal at 85 °C — if the enclosure runs hotter, move to 2.0 A.

## ERC log

| Run | Tool | Errors | Warnings | Notes |
|---|---|---|---|---|
| Rev A.0 | KiCad 10.0 GUI | 78 | 170 | 69 x pin_not_connected (all deliberately unused pads, verified against spec.py), 7 x pin_not_driven (same pins), 2 x power_pin_not_driven (J2 VDD/VSS - no power-output on rails), 167 x endpoint_off_grid (metric origins vs 50 mil grid), 3 x lib_symbol_mismatch (KiCad 7 libs vs 10) |
| Rev A.1 | generated | - | - | Fixes: PWR_FLAG on +5V/+3V3/+1V8/GND; part origins snapped to 1.27 mm; explicit no_connect on all 69 unused pins. Netlist re-verified against spec.py via kicad-cli (36/36 nets match). |
| Rev A.1 | KiCad 10.0 GUI | 2 | 3 | 2 x Output+PowerOutput conflict (U1 77/78 typed "output" by Luckfox vs my PWR_FLAG) ; 3 x lib_symbol_mismatch (cosmetic, KiCad 7 vs 10 stock libs) |
| Rev A.2 | generated | - | - | lib/Core1106.kicad_sym pins 76/77/78 -> power_out, 79/80/81 -> power_in (patch_core1106.py). PWR_FLAG kept only on +5V and GND. Netlist re-verified 36/36. |
| Rev A.2 | KiCad 10.0 GUI | 1 | 3 | PowerOutput+PowerOutput: U1 76 (VCC3V3_RTC) tied to U1 78 (VCC_3V3) in spec. |
| Rev A.3 | generated | - | - | **Spec error fixed.** Module schematic (PART A) shows VCC_3V3 -> D1 RB521S-30 -> pad 76 -> R14 100R -> RTC_AVDD3V3. Pad 76 is the RTC backup-battery tap, not a supply; tying it to +3V3 shorted across D1. Now NC (passive). Future: coin cell / supercap on pad 76 for RTC hold-up. Netlist re-verified 36/36. |

### Audit addendum (Rev A.3)
| # | Finding | Severity | Source | Fix |
|---|---|---|---|---|
| A-7 | Pad 76 VCC3V3_RTC was on +3V3, shorting the module's RTC isolation diode D1 | Medium (defeats backup design; no damage) | Core1106 schematic PART A, D1/R14/C26 | Pad 76 -> NC in spec.py; documented as future backup tap |
| Rev A.3 | KiCad 10.0 GUI | 0 | 3 | lib_symbol_mismatch x3 (J1, J2, D2): generated from KiCad 7 stock libs. |
| Rev A.4 | generated | - | - | Generator now reads the workstation's KiCad 10.0 stock libraries and emits the native 20260101 dialect. KiCad 10 renamed shield pins: J1 S1->SH, J2 9->SH (footprints match). verify10.py rebuilds the netlist from file geometry alone: 36/36 nets, 216/216 pins accounted for. |
| Rev A.5 | generated | - | - | **A-8**: camera I2C moved from pads 14/15 (I2C3_M2) to 16/17 (I2C4_M2), which Luckfox's module schematic labels MIPI_I2C and their stock camera DTS expects. Pads 14/15 now NC. Pad 24 (USB_VBUSDET) confirmed 3.3 V domain per PinOut.xls, so the 2.5 V divider is in range. See MECH.md. |

## Phase 2 - PCB

Board 75 x 44 mm, 4-layer (JLCPCB JLC04161H-7628), 4 x M2 holes. Generated by `genpcb.py`
(placement, from `placement.py`) then `route.py` (autorouted). `check.py` is the independent
geometric oracle: it rasterises every pad/track/via at 0.02 mm and reports any pair of
different nets closer than the clearance.

| Stage | Result |
|---|---|
| Placement | 32 footprints, no courtyard overlaps |
| Routing | 52/52 connections, 1267 segments, 87 vias |
| GND | 49 pads stitched to the In1.Cu plane; the rest connect through the F.Cu pour |
| check.py | **0 clearance violations** at 0.02 mm resolution |
| Left for interactive routing | `CSI_CLK/D0/D1` pairs, `USB_DP/DM` - net classes preset (100R: 0.22/0.18, 90R: 0.27/0.18) |

Design choices the router enforces:
- F.Cu is kept clear under the centre of the module (inside Luckfox's keep-out rings); a
  ~4 mm annulus inside the pad ring is used for escape routing. B.Cu underneath is free.
- Signals 0.15 mm (needed to escape the 0.5 mm-pitch FPC and USB-C), +3V3 0.4 mm,
  +5V/VBUS_IN 0.5 mm, +1V8 0.3 mm.
- Every GND pad gets its own via to the ground plane where there is room for one.
