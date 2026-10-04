# LocalCam-1 Rev A2 — design intent

Why this board is laid out the way it is. Written so that in six months you can open
the file, disagree with something, and know what you are trading away.

---

## 1. What the board is

A local-only WiFi camera. A Luckfox Core1106 module (Rockchip RV1106G3) takes a MIPI
CSI-2 sensor over an FPC, encodes H.264/H.265 on-chip, serves RTSP to Frigate, and runs
cat detection on its own 1 TOPS NPU. Nothing leaves the LAN. The board is 75 × 44 mm,
four layers, 1.6 mm, built by JLCPCB.

Everything on this board exists to do one of four things: get 5 V in, get the camera
in, get video out over WiFi, and let you recover the thing when it will not boot.

---

## 2. The stack-up, and why it decides everything else

    F.Cu      35 µm    signal — short horizontal runs, all the fine-pitch escapes
    prepreg  210.4 µm  7628, Er 4.4     <-- this number sets the impedance
    In1.Cu    15.2 µm  SOLID GROUND. Nothing else is allowed on it.
    core    1065   µm  Er 4.6
    In2.Cu    15.2 µm  power rails
    prepreg  210.4 µm
    B.Cu      35 µm    signal — vertical runs and everything crossing under the module

JLCPCB's **JLC04161H-7628**. The 0.2104 mm of 7628 between F.Cu and the ground plane is
the entire reason the camera pairs can be 100 Ω: a microstrip 0.22 mm wide over that
dielectric is 100 Ω differential at a 0.18 mm gap (IPC-2141). **If you let JLCPCB pick a
different stack-up at order time, the pairs stop being 100 Ω** and nothing on the board
tells you. That is why the order settings are spelled out in `make-fab.sh`.

In1.Cu is a plane and not a routing layer. That is not tidiness — it is the return path.
A MIPI pair's return current flows in the copper directly beneath it, and a slot cut in
that plane forces the return to detour around it. That is the classic failure where a
camera link works on the bench and drops frames when the enclosure warms up. The router
physically cannot put a non-GND track on In1.Cu; the layer is pre-loaded as GND in its
occupancy model, so anything else is a collision.

In2.Cu carries the rails. It is not a second ground.

---

## 3. Routing philosophy

The brief was: do not make it look like a machine did it. Concretely that meant:

**Orthogonal, with exactly one exception.** Every trace on this board runs parallel or
perpendicular to a board edge. 461 of 479 segments are orthogonal; the other 18 are
45° chamfers and **all 18 belong to the six camera-pair traces** — three per trace, in
one corridor. Nothing else on the board turns at an angle, and the build fails if it
does: the geometry gate allows a 45° only on a CSI net, and a repair pass rebuilds
anything else as an L or removes it and reports it.

Why the camera pairs are the exception, and nothing else is: a square corner needs the
full trace width plus clearance to turn, twice, where a chamfer turns inside the trace's
own width. Three pairs share one channel from the FPC to the module, and routed fully
orthogonal the clock pair could not stay coupled — it came out at **3.0 mm intra-pair
skew against a 100 µm budget**, which is a dead MIPI link. Eighteen chamfers in one
corridor buys back 0 µm on all three pairs. Everywhere else on this board there is room,
so there is no reason to cut a corner and it does not.

**Layers have a direction.** F.Cu trends horizontal, B.Cu trends vertical. The router
pays a cost penalty for going against the grain, and its maze search moves on four
neighbours, not eight, so an oblique run is not merely discouraged — it is unreachable. This is the oldest convention in the
trade and it is why you can follow a net by eye: if it turns, it changed layer, and
there is a via there.

**Escapes are perpendicular.** A trace leaves a pad along the pad's own long axis,
straight, before it turns. On the module's castellated 1.0 mm pitch and the FPC's
0.5 mm pitch there is no other legal way out, and it is also simply what a person draws.

**Shapes before search.** The router tries clean L and Z shapes first and only falls
back to a maze search when geometry cannot do it. A maze path is recognisably
machine-made; an L is not.

**Necked escapes.** A 0.5 mm power rail cannot physically leave a 1.0 mm-pitch
castellated pad at 0.2 mm clearance — the arithmetic does not close. So rails leave at
0.3 mm and fatten once clear of the pad field, and USB stubs leave 0.5 mm-pitch
connector pads at 0.2 mm. This is standard fanout practice, not a compromise.

---

## 4. The decisions worth arguing about

### 4.1 The camera pairs are routed as one trace, then split

The three CSI pairs are not two traces that happen to run near each other. A single
centreline is routed at the full pair width (2 × 0.22 + 0.18 = 0.62 mm), and the two
traces are generated as parallel offsets of it. The consequence is that the gap is
constant by construction, the corners are mirrored, and the lengths are identical.

    CSI_D1   14.51 / 14.51 mm     skew 0 µm
    CSI_CLK  14.72 / 14.72 mm     skew 0 µm
    CSI_D0   14.92 / 14.92 mm     skew 0 µm

Measured off the finished file by a script that did not do the routing, not claimed by
the router.

Budget was 100 µm intra-pair and 1000 µm between pairs. Actual: **0 µm** and 410 µm.
No pair changes layer, no pair has a via, and all three stay on F.Cu over unbroken
In1.Cu the whole way. They are routed in the physical order they appear on the FPC so
the bus nests instead of crossing.

The order the three are routed in matters: whichever goes first shapes the channel for
the other two. The build tries several orderings and keeps the one that couples all
three. That is worth knowing if you move a part and one pair suddenly routes loose.

### 4.2 The USB-C data pads cross without a single via

A 12-pin USB-C receptacle interleaves its two D− pads with its two D+ pads
(B7 D−, A6 D+, A7 D−, B6 D+, at 0.5 mm pitch). To short A6–B6 and A7–B7 for reversible
orientation the two links **must** cross exactly once.

The obvious answer — a via pair — does not fit. A 0.6 mm via needs 0.5 mm of clear
radius and the neighbouring pad edge is 0.35 mm away. It is not a question of trying
harder; the geometry is closed.

So the crossing is a **bowtie**: one net crosses *above* the pad row, inside the
connector body where the board is empty, and the other crosses *below* it. They never
meet, so nothing has to change layer. No vias, no stubs, no compromise.

### 4.3 The USB pair is not coupled, and that is deliberate

U2 (the USBLC6 ESD part) has its **+5V pin physically between D− and D+**. There is no
way to route a coupled pair into that pinout. The U1↔U2 run is therefore two
single-ended traces at the correct 0.27 mm width.

Over ~8 mm at USB 2.0 full/high speed this is not a problem in practice, but it is a
known deviation rather than an oversight. If you want it coupled, U2 has to move or be
replaced with a part whose D± pins are adjacent.

The J1↔U2 stubs are routed at the default 0.2 mm rather than 0.27 mm. Holding them to
the USB class made them unroutable through U2's pad field, and 5 mm of 0.2 mm trace is
roughly 95 Ω instead of 90 Ω — an irrelevant discontinuity at USB 2.0. The
impedance-controlled run is U1↔U2 and it keeps the class.

### 4.4 Power: one via per group, and the rails live on In2.Cu

Rail pads that sit near each other are joined on the top layer as a local group, and
each group drops **one** via into the power layer. The alternative — a via at every rail
pad — is electrically slightly better and visually much worse, and on this board it
crowded the pull-up resistors and decoupling caps around the camera bus badly enough
that their own signals could not escape.

The rails are traces on In2.Cu, not pours. 0.5 mm of 1 oz outer copper carries 1.44 A at
a 10 °C rise (IPC-2221); the module draws about 0.6 A. That is 2.4× margin, and a routed
power layer is easier to read and to change than a set of overlapping pours.

**+5V and VBUS_IN vias are doubled.** A single plated barrel carrying an entire rail is
the classic warm-attic failure — barrel fatigue accelerates with thermal cycling, and
when it goes the module loses its supply. Companion vias cost nothing and halve the
current per barrel.

### 4.5 Ground is a plane plus stitching, not a net to be routed

GND pads connect through the F.Cu and B.Cu pours. The stitching vias are not there to
make the connection — they are there to give each pad a short path to the In1.Cu plane,
which is what actually matters for return current. They are placed last, into whatever
space is left, which is the correct order: they are the most flexible thing on the board.

Some pads have no room for a stitching via. They are still connected through the pour;
they just have a longer return path. The build lists them by name rather than quietly
skipping them.

### 4.6 Pad-to-pad clearance is the footprint's problem, not the trace's

A 0.5 mm-pitch FPC pin offers exactly 0.35 mm of lateral room, and a 0.2 mm trace at
0.15 mm clearance needs exactly 0.35 mm. Enforced naively, *nothing can ever leave an
FPC pad*. The clearance rule is therefore not applied inside a pad's own footprint area
— the fab guarantees the pad gaps, and this is how every real router behaves. Outside
the pad, full clearance applies.

---

## 5. What changed in Rev A2, and why

These came out of an independent review and are real defects, not polish.

| # | Change | Why |
|---|---|---|
| A-9 | **R7 moved from +3V3 to +5V** | The "VBUS detect" divider was fed from +3V3, giving a fixed 1.65 V into U1 pad 24 — **below** a 3.3 V input's V_IH, so the pin sat in the indeterminate band. From +5V the divider gives 2.5 V, a valid logic high, and it now does what the netlist comment always claimed. |
| A-10 | **C7 added — 100 nF on +1V8** | There was no decoupling on the 1.8 V rail at all. It feeds the camera's IO reference and the I²C pull-ups. |
| A-11 | **C8 added — 10 µF local +5V bulk** | C1 (47 µF) sits at the fuse, 71 mm and roughly 100 mΩ from the module's power pins — about 60 mV of droop at 0.6 A, with nothing local to absorb a WiFi transmit step. C8 sits beside pads 79–81. |
| A-12 | **Ground pour inset 0.25 mm, following the corner radius** | The pour was the raw 75 × 44 rectangle. It ignored the 2 mm corner fillets and ran flush to the cut line. JLCPCB wants 0.2 mm copper-to-edge. |
| A-13 | **No via may overlap any pad** | Three vias had landed inside pads. Via-in-pad wicks solder paste during reflow and is not offered at this price tier. |
| A-14 | **Via hole-to-hole enforced at 0.55 mm centres** | Two pairs of drills physically overlapped (−0.008 and −0.120 mm). JLCPCB's minimum is 0.20 mm hole-to-hole. |
| A-15 | **+5V and VBUS_IN vias doubled** | See 4.4. |

C7 and C8 change the BOM by two parts. Everything else is layout-only.

---

## 6. Things that are true and that you should not "fix"

- **Pad 76 (VCC3V3_RTC) is deliberately unconnected.** Inside the module it sits behind
  Schottky D1. Tying it to +3V3 shorts across that diode. The Drive design brief has
  this wrong; this file is correct.
- **The I²C pull-ups go to +1V8, not +3V3.** The camera bank (pads 7–20) is a 1.8 V IO
  domain. Pulling those lines to 3.3 V over-drives the pins.
- **Pads 77 and 78 are outputs.** VCC_1V8 and VCC_3V3 come *out* of the module's PMIC.
  Only 5 V goes in, on pads 79/80/81.
- **The camera pairs have no test points and no stubs.** That is not an omission.

---

## 7. How to change this board without breaking it

`spec.py` is the netlist source of truth and `placement.py` is the placement source of
truth. The schematic and the board are **build outputs** — never hand-edit them and
expect the edit to survive.

    python3 gen.py        # -> LocalCam1.kicad_sch
    python3 genpcb.py     # -> LocalCam1.kicad_pcb  (placed, netted, unrouted)
    python3 hroute5.py base2.kicad_pcb routed.kicad_pcb    # route it

Verify with something that did not do the routing:

    python3 continuity.py routed.kicad_pcb --clearance

That rasterises every piece of copper — pads, tracks, vias, filled pours — joins layers
through vias, and counts how many electrically separate islands each net forms.
**One island means the net is whole.** It also reports the true minimum copper-to-copper
distance using a Euclidean distance transform, so the number it prints is the real gap,
not a grid artefact.

Fill the zones in KiCad (press `B`) and save before running it, or the pours are ignored
and ground will look disconnected.

---

## 8. What is still open, and exactly how to close it

Two pads out of 226 are not connected. Verified per-pad by `padaudit.py`, which simulates
the ground pour, so this is not an unfilled-zone artefact:

    SD_D3     J2.2   at (55.77, 28.50)
    VBUS_DET  R7.2   at (19.41, 32.60)

Both were attacked by the router from every direction it has — shape search, two-layer
maze, two rounds of rip-up at widening corridors, and a last-resort pass at
0.15 mm / 0.10 mm. Each time it reported no gain rather than breaking something else to
claim a win. They are placement problems, not routing problems:

- **VBUS_DET R7.2 → U1.24 (21, 30.5).** R7 sits at (18.9, 32.6), directly in the channel
  the USB pair needs between U2 and the module's left edge. Move R7 clear of that
  channel — down toward y ≈ 35.5, or rotate it 90° — and the tap has a straight run.
- **SD_D3 J2.2 → U1.52.** Six SD signals leave the module's bottom edge into one gap
  between the module and the microSD socket, and D3 is the one that does not fit. Either
  give it B.Cu (a via each side, running under the bus) or shift J2 a millimetre.

Either is a two-minute job by hand in KiCad, or change `placement.py` and re-run
`hroute5.py` followed by `hroute6.py`.

**A note on how these were found.** The earlier `continuity.py` island count said a net
was broken but not which pad. `padaudit.py` answers per pad, and with the pour simulated
it caught something the island count had let me wave away: U2's ground pad was fenced in
by the USB traces, so the pour could not reach it and **U2 was not grounded at all**.
That is fixed — it now has its own via to the In1.Cu plane. Run `padaudit.py` after any
change; it is the check that actually tells you the truth about a single pin.
