# LocalCam-1 mechanical facts (Phase 2 inputs)

## Core1106 module (U1)
| Item | Value | Source |
|---|---|---|
| Outline | 30.00 x 30.00 mm | Waveshare dimension drawing `Core11061408-details-size.jpg` |
| PCB thickness | 1.60 +/- 0.1 mm | same |
| Component side | **top only**; underside is flat | same (side view) |
| Max component height | 4.20 mm above PCB (5.50 mm total) | same |
| Castellations | 112, 1.00 mm pitch, 28 per side, pad 0.7 x 1.5 mm at +/-15.0 mm | `Core1106-SMT.kicad_mod` |
| Pin 1 | top-left corner (triangle marker), numbering runs down the left edge | drawing + PinOut.xls |
| Antenna | **IPEX 1.0 (u.FL) connector on the module, bottom-right corner**, external antenna required | Waveshare page + module schematic ANT1 (GND/DATA/GND) + drawing |
| Carrier copper under module | allowed, except Luckfox's keep-out ring (F&B.Cu: no tracks/vias/pads/pour) at x[-12.15,11.40] y[-11.65,9.02] rel. module centre, 0.25 mm wide | `Core1106-SMT.kicad_mod` zones |
| Carrier cut-out under module | **not required** (flat underside) | drawing |

## Consequences for the carrier
- No copper antenna keep-out on the carrier (antenna is external via IPEX). Reserve headroom above the module's bottom-right corner for the u.FL pigtail and pick an antenna mount point on the case.
- Case must clear 5.5 mm above the carrier's top surface over the module footprint, plus pigtail bend radius (~5 mm) at the IPEX corner.
- All carrier components on the top side (JLCPCB single-side assembly); nothing under the module on the bottom is needed.
- Module is hand-soldered (castellated, not on JLCPCB's placement list); the carrier pads follow Luckfox's footprint exactly.

## Camera I2C pad choice (Phase 2 finding A-8)
Module schematic labels pads 16/17 as `MIPI_I2C_SCL/SDA` (= I2C4_M2 per PinOut.xls). Pads 14/15 are I2C3_M2 - electrically valid but not what Luckfox's stock camera device-tree expects. Spec moved CAM_SCL/CAM_SDA to 16/17 so the SDK's default camera config works unmodified.
