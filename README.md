# LocalCam-1 — a local-only WiFi camera

A small 4-layer board that turns a **Luckfox Core1106** system-on-module (Rockchip
RV1106G3) into a network camera that never talks to anyone's cloud. A MIPI CSI-2 sensor
comes in over an FPC, the module encodes H.264/H.265 on-chip, and the stream is served
over RTSP to a local [Frigate](https://frigate.video/) NVR. Object detection runs on the
module's own 1 TOPS NPU, on the camera, not on a server and not on someone else's GPU.

**75 × 44 mm, 4 layers, 1.6 mm, built by JLCPCB.** USB-C in, microSD for storage, a
debug UART header and a recovery button.

> **Status: not ready to order.** 226 of 228 netted pads are connected. Two signals still
> need a trace and both need a part nudged rather than more routing effort — see
> [What is still open](#what-is-still-open). Everything else has been verified; the
> evidence is in [`logs/`](logs/).

---

## Why this board exists

Every consumer camera in this class wants an account, an app, and an outbound
connection. The goal here is the opposite: a camera that is useful precisely because it
is isolated. Four requirements drove the whole design.

1. **Nothing leaves the LAN.** No cloud service, no phone-home, no vendor account. RTSP
   to a local NVR and that is all.
2. **Detection happens on the camera.** The RV1106G3's NPU runs the model, so there is
   no video streaming off-box just so a server can look at it.
3. **It must be repairable and legible.** A board you cannot read is a board you cannot
   fix. That drove the routing style (below) as much as any electrical requirement.
4. **One cable.** USB-C supplies it; everything else is optional.

## What is on it

| | |
|---|---|
| **U1** | Luckfox Core1106 — RV1106G3, Cortex-A7 + RISC-V MCU + NPU + ISP, 256 MB DDR3L, onboard WiFi and 8 GB eMMC options |
| **J3** | 24-pin 0.5 mm FPC to the camera sensor — 2 MIPI data lanes + clock, I²C, MCLK, reset, power-down |
| **J1** | USB-C 2.0 receptacle — power in and USB device, with CC pull-downs and an ESD part (U2) |
| **J2** | microSD (Hirose DM3AT), 4-bit SDMMC, with card-detect |
| **H1** | 5-pin debug header — UART2 plus the recovery line |
| **S1** | reset, **D2** status LED, **F1** 1.5 A polyfuse, **D1** TVS on the 5 V rail |

Full pad-by-pad detail, cross-checked against the vendor pinout, is in
[`docs/pin-assignment-crosscheck.md`](docs/pin-assignment-crosscheck.md).

---

## The design decisions worth arguing about

[`docs/INTENT.md`](docs/INTENT.md) is the long version. The short version:

**The stack-up decides everything.** JLCPCB **JLC04161H-7628**: the 0.2104 mm of 7628
prepreg between F.Cu and the ground plane is the only reason the camera pairs can be
100 Ω. *If you let the fab substitute a stack-up, the pairs silently stop being 100 Ω.*
The order settings are printed by `hardware/make-fab.sh` for exactly that reason.

**In1.Cu is a plane, not a routing layer.** A MIPI pair's return current flows in the
copper directly beneath it; a slot cut in that plane is the classic reason a camera link
passes on the bench and drops frames when the enclosure warms up. The router physically
cannot place a non-GND track there.

**The camera pairs are routed as one trace, then split.** A single centreline is routed
at the full pair width and both traces are generated as parallel offsets of it, so the
gap is constant by construction and the lengths are identical:

| pair | leg / leg | intra-pair skew |
|---|---|---|
| CSI_D1 | 14.51 / 14.51 mm | **0 µm** |
| CSI_CLK | 14.72 / 14.72 mm | **0 µm** |
| CSI_D0 | 14.92 / 14.92 mm | **0 µm** |

Budget was 100 µm. Inter-pair spread is 410 µm against a 1000 µm budget. No pair changes
layer and no pair has a via.

**Orthogonal everywhere, with one deliberate exception.** Every trace runs parallel or
perpendicular to a board edge — 480-odd segments of it — except **18 chamfers, all six
of which belong to camera-pair traces**. Routed fully orthogonal the clock pair could not
stay coupled in the shared FPC channel and came out at 3.0 mm skew, which is a dead MIPI
link. Eighteen chamfers in one corridor buy back 0 µm on all three pairs. Everywhere
else there is room, so nothing cuts a corner.

**The USB-C data pads cross with no vias at all.** A 12-pin receptacle interleaves its
two D− pads with its two D+ pads at 0.5 mm pitch, so the two shorting links must cross
exactly once. A via pair does not fit — a 0.6 mm via needs 0.5 mm of clear radius and the
neighbouring pad edge is 0.35 mm away. So one net crosses *above* the pad row, inside the
connector body, and the other crosses *below* it. They never meet.

**Power rails live on In2.Cu, one via per group.** 0.5 mm of 1 oz outer copper carries
1.44 A at a 10 °C rise (IPC-2221) and the module draws about 0.6 A. +5V and VBUS_IN vias
are doubled, because a single plated barrel carrying a whole rail is the classic
warm-attic failure.

---

## Defects found and fixed along the way

These were real, and most were caught by review rather than by the person who made them.

| # | Defect | Why it mattered |
|---|---|---|
| A-7 | Pad 76 (`VCC3V3_RTC`) had been tied to +3V3 | It sits behind a Schottky inside the module; tying it shorts across that diode. Now deliberately unconnected. |
| A-8 | Camera I²C pull-ups went to +3V3 | Pads 16/17 are in the module's **1.8 V** IO domain — the vendor pinout confirms it. Pulling them to 3.3 V over-drives 1.8 V pins. Now on `+1V8`. |
| A-9 | `VBUS_DET` divider was fed from +3V3 | 100k/100k from 3.3 V gives 1.65 V into pad 24 (`USB_VBUSDET`, a **3.3 V** input) — *below* V_IH, so the pin sat in the indeterminate band. Now from +5V: 2.5 V, a valid high. |
| A-10/11 | No decoupling on +1V8; +5V bulk 71 mm from the module | ~60 mV of droop at 0.6 A with nothing local to absorb a WiFi transmit burst. Added C7 (100 nF on +1V8) and C8 (10 µF local +5V bulk). |
| A-12 | Ground pour ran flush to the board edge | Ignored the 2 mm corner fillets. Now inset 0.25 mm, following the radius. |
| A-13 | Three vias sat **inside pads** | Via-in-pad wicks solder paste during reflow and is not offered at this price tier. |
| A-14 | Two pairs of drills physically overlapped | −0.008 and −0.120 mm hole-to-hole against a 0.20 mm minimum. The fab would have rejected it. |
| A-15 | U2 (the USB ESD part) **was not grounded** | Its ground pad is fenced in by the USB traces, so the pour could not reach it. It now has its own via to the plane. |
| A-16 | The microSD **card-detect pins were not in the netlist at all** | J2 pins 9/10 had no net, so no connectivity check could report them. The stock `Micro_SD_Card` symbol has no such pins; J2 now uses `Micro_SD_Card_Det2`, which matches the DM3AT footprint pin for pin. |

A-15 and A-16 are the instructive ones: both were invisible to a net-level check. A net
with two pads and one trace looks complete whether or not a *third* pad is stranded, and
a pad with no net cannot be reported as disconnected at all. That is what
`tools/padaudit.py` exists to catch.

---

## Repo layout

```
hardware/     the KiCad 10 project — open LocalCam1.kicad_pro
  lib/        the Core1106 symbol and footprint (not in KiCad's stock libraries)
  make-fab.sh one-shot JLCPCB output generator; run it on a machine with KiCad 10
tools/        the sources of truth and the checkers
  spec.py       NETLIST source of truth — 36 parts, 36 nets. Edit this, never the schematic
  placement.py  PLACEMENT source of truth — part positions and the zone list
  gen.py        spec.py  -> LocalCam1.kicad_sch
  genpcb.py     spec.py + placement.py -> LocalCam1.kicad_pcb (placed, netted, unrouted)
  hroute5.py    the router (orthogonal, with coupled differential pairs)
  hroute6.py    the finisher — routes only what is missing, keeping existing copper
  continuity.py per-net island count + true minimum copper-to-copper gap
  padaudit.py   PER-PAD audit with the ground pour simulated  <- the one that finds real bugs
docs/         design intent, the pinout, the cross-check, routing and mechanical notes
vendor/       Luckfox's own Core1106 pinout spreadsheet, module PDF and footprint package
logs/         verification output, kept as evidence rather than summarised
```

## Building and checking it

The schematic and the board are **build outputs**. Do not hand-edit them and expect the
edit to survive.

```bash
cd tools
export KICAD_SYMBOL_DIR=/usr/share/kicad/symbols     # wherever yours live
python3 gen.py        # -> LocalCam1.kicad_sch
python3 genpcb.py     # -> LocalCam1.kicad_pcb  (placed, netted, unrouted)
python3 hroute5.py base.kicad_pcb routed.kicad_pcb   # route it
```

Then check it with something that did not do the routing:

```bash
python3 padaudit.py   ../hardware/LocalCam1.kicad_pcb   # per-pad, pour simulated
python3 continuity.py ../hardware/LocalCam1.kicad_pcb --clearance
```

`padaudit.py` walks every pad that carries a net and answers one question: is this pad in
the same electrical island as the rest of its net? It simulates the ground pour, because
the board ships with pours unfilled so KiCad recomputes them — without that simulation
every GND pad looks disconnected and the answer is useless.

**Fill the zones in KiCad (press `B`) and save before plotting**, or the pours are not in
the Gerbers and the ground plane simply does not exist.

Requires `numpy` and `scipy`.

## Verified, on the delivered board

```
226 / 228 netted pads connected        (pour simulated)
499 segments: 481 orthogonal, 18 chamfers on camera pairs, 0 other angles
108 vias, all 0.6 / 0.3 mm             (0.15 mm annular ring, min is 0.13)
minimum copper-to-copper gap 0.150 mm  (JLCPCB floor is 0.09)
camera pairs: 0 µm intra-pair skew, 410 µm inter-pair spread
45 of 45 used module pads agree with the vendor pinout
```

## What is still open

Two signals, both placement problems rather than routing ones:

| Net | Pad | At | What to do |
|---|---|---|---|
| `SD_D3` | J2.2 | (55.78, 28.51) | Six SD signals funnel through one gap between the module and the socket and D3 does not fit. Give it B.Cu with a via each side, or shift J2 about a millimetre. |
| `VBUS_DET` | R7.2 | (19.41, 32.60) | R7 sits in the channel the USB pair needs between U2 and the module edge. Move it clear — toward y ≈ 35.5 — or rotate it 90°. |

The router was given every chance at these: shape search, two-layer maze, two rip-up
rounds at widening corridors, and a last-resort pass at 0.15 mm / 0.10 mm. Each attempt
either gained nothing or broke three other nets to fix one, and reported that rather than
claiming a win.

**Open question for review:** `R7` currently divides **+5V** (post-fuse). Dividing
**VBUS_IN** (pre-fuse) is what the pin name literally means and still reads high if the
polyfuse opens; +5V instead answers "is my rail actually up?". Both give 2.5 V and both
are valid. One line in `spec.py`.

## Reviewing this board — where to look first

If you have ten minutes: [`docs/INTENT.md`](docs/INTENT.md) §4 for the arguable decisions,
then `logs/VERIFY-pads.log` for what is actually connected. If you have an hour, run
`padaudit.py` yourself and disagree with it.

Things I would most like a second opinion on:

- The two open nets above — is nudging R7 and J2 the right call, or should the floorplan
  change more deeply?
- The USB pair is **not** coupled between U1 and U2, because U2's +5V pin sits physically
  between D− and D+. Over ~8 mm at USB 2.0 that should be fine. Second opinion welcome.
- `+5V` reaches the module through a ~71 mm path. C8 was added locally to cover it, but a
  different floorplan would shorten the path instead.
- Whether grounding both card-detect pins is the right choice versus bringing one out to
  a GPIO with a pull-up.

## Sources

- Luckfox Core1106 pinout, schematic and footprint package —
  <https://wiki.luckfox.com/Core1106/Pinout/> (the files are mirrored in `vendor/`)
- Rockchip RV1106 datasheet V1.7 —
  <https://files.luckfox.com/wiki/Luckfox-Pico/PDF/Rockchip%20RV1106%20Datasheet%20V1.7-20231218.pdf>
- Core1106 product page — <https://www.luckfox.com/Core1106>
- Trace current capacity: IPC-2221. Differential microstrip geometry: IPC-2141.
- JLCPCB capabilities and the JLC04161H-7628 stack-up: JLCPCB's own capability pages.

## Licence

No licence has been chosen yet — which by default means all rights reserved, so pick one
before sharing this widely.
