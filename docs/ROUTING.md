# LocalCam-1 Rev A — hand-routing sheet

Board is placed, netted and set up. Nothing is routed. Everything below is already
configured in the project — you should not have to type a number in.

## What's already set

| | |
|---|---|
| Stack-up | JLCPCB **JLC04161H-7628**, 4 layer, 1.6 mm. L1 signal / **L2 solid GND** / **L3 power (free)** / L4 signal |
| Impedance reference | 0.2104 mm of 7628 prepreg, Er 4.4, from L1 down to the L2 ground plane |
| Zones | GND on **F.Cu, In1.Cu, B.Cu**. **In2.Cu is left free** — it is the power layer |
| Net classes | assigned automatically by name — see below |
| DRC limits | set to JLCPCB's real capability, not a house style. DRC complains only if the fab would |

## Net classes (applied by pattern, nothing to select)

| Class | Nets | Track | Clearance | Via | Diff pair |
|---|---|---|---|---|---|
| **MIPI_100R** | `CSI_*` | 0.22 | 0.18 | 0.45/0.25 | **0.22 W / 0.18 gap** → 100 Ω |
| **USB_90R** | `USB_D*` | 0.27 | 0.18 | 0.45/0.25 | **0.27 W / 0.18 gap** → 90 Ω |
| **Power** | `+5V` `+3V3` `+1V8` `GND` `VBUS_IN` | 0.5 | 0.2 | 0.9/0.4 | – |
| Default | everything else | 0.2 | 0.15 | 0.6/0.3 | – |

Select a pair and use **Route → Differential Pair (6)**; KiCad picks the width and gap
from the class. `Ctrl+Shift+H` while routing swaps sides.

## DRC constraints = JLCPCB capability

| Constraint | Set to | Why |
|---|---|---|
| Min track / clearance | 0.09 / 0.09 mm | JLCPCB 4-layer, 1 oz outer |
| Min via diameter / drill | 0.25 / 0.15 mm | their absolute minimum (costs extra below 0.45/0.25) |
| Min annular ring | 0.13 mm | |
| Min hole-to-hole | 0.20 mm | |
| Copper to board edge | 0.20 mm | |

The dropdowns are pre-loaded with 0.15 / 0.2 / 0.22 / 0.27 / 0.3 / 0.4 / 0.5 / 0.8 / 1.0 mm
tracks and 0.6/0.3, 0.45/0.25, 0.9/0.4 vias, so you can pick rather than type.

## The power layer (In2.Cu)

In2.Cu has **no zone on it** on purpose. It is yours to carve into rails.

To make a power island: switch to In2.Cu, `Ctrl+Shift+Z` (Add Filled Zone), draw the
outline, pick the net (`+5V`, `+3V3`, `+1V8`), and set **Priority 2**. If you later want
GND filling the leftovers on that layer, add a GND zone over the whole layer at
**Priority 0** — higher priority fills first, so the rails win and GND flows around them.

**Vias must be placed while routing, not standalone.** Start a track from the pad, press
**`V`** mid-route: the via inherits the net and drops you onto the other layer. A via
placed on its own with the via tool has no net, and nothing will connect to it.

### Zones and vias — how the connection actually happens

A zone bonds to pads and vias **that are already on its net**, and carves a clearance
moat around everything else. It does not hand its net to whatever lands inside it.
So the workflow is: route +5V on F.Cu, press `V` to drop a via (the via inherits +5V),
and where it lands inside the +5V pour on In2.Cu it bonds automatically — no track needed
on the inner layer. A via with no net just gets a hole cut around it.

Three things to remember:
- **Press `B` to fill zones.** An unfilled zone connects nothing and DRC will show the
  pads unconnected. Zones do not auto-fill on save.
- **Priority decides overlaps.** Higher fills first. Rails at priority 2, a GND
  catch-all at priority 0, and ground flows around the rails instead of over them.
- **Via current:** a 0.3 mm drill with 20 µm plating carries ~**1.5 A** at 10 °C rise.
  The module draws ~0.6 A, so one via is enough — use two for margin and redundancy.

**In1.Cu stays solid GND.** It is the reference plane for every controlled-impedance trace
on F.Cu. Cutting a slot in it under a MIPI pair breaks the return path — that is the
classic reason a camera link works on the bench and fails at temperature.

## Suggested order

1. **MIPI first — CSI_CLK, CSI_D0, CSI_D1** (U1 pads 7–12 ↔ J3 pins 2,3,5,6,8,9).
   Route as differential pairs on **F.Cu only**, no vias, straight across to the FPC.
   They are the reason the board is 4-layer; give them the clean space first.
2. **USB — USB_DP/DM** (U2 ↔ U1 pads 22/23), and USB_DP_CON/DM_CON (J1 ↔ U2).
   Pair, F.Cu, keep U2 in line between connector and module.
3. **Power** — VBUS_IN → F1 → +5V → U1 pads 79/80/81; then +3V3 from pad 78 out to
   J2, J3, H1, C3–C6; +1V8 from pad 77 to R5/R6 and J3 pin 21.
4. **Everything else** — SD bus, UART, I²C, reset, LED, VBUS_DET, recovery. Any layer.
5. **GND last** — poured on F.Cu, In1.Cu and B.Cu, so mostly you are adding stitching
   vias, not tracks. Drop a via next to each GND pad that isn't already touching a pour.

## The rules that actually matter

**MIPI (D-PHY, ~1 Gb/s per lane)**
- Intra-pair skew ≤ **0.1 mm**. Inter-pair (lane-to-lane, lane-to-clock) ≤ **1.0 mm**.
  Use *Route → Tune Differential Pair Skew* — the target lengths are in the class.
- **Never cross a gap in the L2 ground plane.** The return current follows the trace on
  L2; a split under a pair is the classic MIPI failure.
- No vias, no stubs, no test points on the pairs. If you must change layer, both legs
  change at the same point and you add a ground via beside them.
- Keep ≥ 0.55 mm (3× the gap) from any other signal.

**USB 2.0** — same idea, looser. Pair length match ≤ 1.0 mm, keep U2 within ~5 mm of J1.

**Power** — 0.5 mm carries **1.44 A** on an outer layer at 10 °C rise (IPC-2221, 1 oz).
The module draws roughly 0.6 A, so 0.5 mm is ~2.4× margin; 0.3 mm would still do.
Put the +5 V bulk cap C1 between F1 and the module pads, not off to one side.

**Under the module** — Luckfox's own footprint carries keep-out rings; don't put copper
in them. The area inside is otherwise usable, but keeping F.Cu clear under the middle of
the module is tidier, and B.Cu underneath is completely free.

## Done when

DRC reports **0 unconnected**, 0 clearance errors. Expect a handful of silkscreen
warnings near the board edge and a "footprint library not enabled" note for Core1106 —
both cosmetic.

Two offline checkers in this folder, independent of KiCad:

    python3 continuity.py                 # per-net island count + missing connections
    python3 continuity.py --clearance     # also test net-to-net spacing (slower)
    python3 continuity.py --fine          # 0.02 mm grid instead of 0.05

`continuity.py` rasterises all copper — pads, tracks, vias and *filled* zones — joins
layers through vias, and counts how many electrically separate islands each net forms.
**1 island = that net is fully connected.** N islands means N−1 connections still missing.
It tells you *how far* a net is from done, which the ratsnest does not.

Fill your zones (`B`) and save before running it, or pours are ignored and GND will
look disconnected.

`check.py` is the older clearance-only version; `continuity.py` supersedes it.

## If you want the parts somewhere else

Placement lives in `placement.py` — `ref: (x, y, rotation)` in mm, board origin top-left.
Change it and run `python3 genpcb.py` to rebuild the board. Or just drag parts in KiCad;
nothing downstream depends on where they sit.
