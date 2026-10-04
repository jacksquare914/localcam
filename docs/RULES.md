# LocalCam-1 PCB stack-up and design rules

## Stack-up: JLCPCB JLC04161H-7628 (4-layer, 1.6 mm)  — source: jlcpcb.com/impedance
| # | Layer | Material | Thickness | Er | Role |
|---|---|---|---|---|---|
| L1 | F.Cu | Cu 1 oz | 0.035 mm | – | Signals: MIPI pairs, USB pair, all components |

Seven copper+dielectric rows sum to **1.5862 mm**, matching JLCPCB's stackup table exactly; KiCad shows 1.6062 mm because it also counts the two 0.01 mm solder masks.

| – | Prepreg 7628 | FR-4 | 0.2104 mm | 4.4 | |
| L2 | In1.Cu | Cu 0.5 oz | 0.0152 mm | – | **Solid GND** (reference for every L1 trace) |
| – | Core | FR-4 | **1.065 mm** | 4.6 | JLCPCB published value. Their "1.1 mm H/HOZ with copper" note is the core *plus* both inner foils — do not derive the dielectric from it. |
| L3 | In2.Cu | Cu 0.5 oz | 0.0152 mm | – | Power pours: +5V, +3V3, +1V8 islands, GND fill |
| – | Prepreg 7628 | FR-4 | 0.2104 mm | 4.4 | |
| L4 | B.Cu | Cu 1 oz | 0.035 mm | – | GND fill, slow signals only if needed |

## Controlled-impedance geometry (L1 over L2, IPC-2141 coupled microstrip; solder mask lowers ~3-5%, so targets sit slightly high)
| Net class | Target | Width | Gap | Model |
|---|---|---|---|---|
| MIPI_100R (`CSI_*`) | 100 Ω diff | 0.22 mm | 0.18 mm | 103 Ω |
| USB_90R (`USB_D*`) | 90 Ω diff | 0.27 mm | 0.18 mm | 91 Ω |
| 50 Ω single-ended (none required) | 50 Ω | 0.35 mm | – | 50 Ω |
**Final widths are confirmed in JLCPCB's impedance calculator at order time**; with "impedance control" ticked, JLCPCB tunes widths to the measured stack. Never route a controlled pair over an L2 gap.

## MIPI CSI-2 (D-PHY) routing rules
- Lanes: CLK, D0, D1 on L1 only, no layer change between module and J3 (short, <40 mm expected).
- Intra-pair skew ≤ 0.1 mm (≈ 0.7 ps). Inter-pair (lane-to-lane and lane-to-clock) ≤ 1.0 mm.
- Keep ≥ 3× gap (0.55 mm) from other signals; ground on both sides of the FPC connector pairs already in the pinout.
- No stubs, no test points on pairs.

## USB 2.0 rules
- Pair on L1, ESD part U2 in-line within 5 mm of J1, pair length match ≤ 1.0 mm.

## Fab limits used (JLCPCB 4-layer, 1 oz outer) — source: jlcpcb.com/capabilities/pcb-capabilities
| Rule | JLCPCB minimum | Design value used |
|---|---|---|
| Track width / spacing | 0.09 / 0.09 mm | **0.15 / 0.15 mm** default; 0.127 allowed near fine-pitch |
| Via hole / diameter | 0.15 / 0.25 mm | **0.30 / 0.70 mm** |
| Annular ring | 0.20 mm | 0.20 mm ((0.70−0.30)/2) |
| Copper to board edge | 0.20 mm | **0.30 mm** |
| Hole to hole | 0.20 mm (via) | 0.25 mm |
| Solder-mask bridge | 0.20 mm | default |
| Power tracks | – | +5V/+3V3 ≥ 0.50 mm on L1; 1 mm where feasible |

## Assembly constraints (JLCPCB SMT, top side only)
- Passives 0603 preferred (Basic parts); 0402 acceptable where the KiCad footprint already is 0402 — decide per part in the BOM pass.
- Core1106 module hand-soldered after assembly (castellated). Keep 1.0 mm clear around it for iron access.
- Hirose FH12 FPC and HRO USB-C, DM3AT microSD: confirm LCSC stock in the BOM task; substitute compatible footprints if not.
