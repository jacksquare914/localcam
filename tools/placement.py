# ============================================================================
#  LocalCam-1 Rev A  --  PCB PLACEMENT SOURCE OF TRUTH  (mm, KiCad frame: y down)
#  Board-first floorplan; a case is printed around this outline afterwards.
#  Rotation follows KiCad: positive = counter-clockwise on screen.
# ============================================================================
BOARD_W, BOARD_H = 75.0, 44.0          # outline, origin top-left
CORNER_R = 2.0                          # rounded corners
HOLES = [(3.0,3.0),(72.0,3.0),(3.0,41.0),(72.0,41.0)]   # M2, 2.2 mm

# Module pad-1 is top-left. Left edge: camera 7-19, USB 22-24, ADC 26.
# Right edge: UART 72/73, nPOR 74, 1V8 77, 3V3 78, 5V 79-81, LED 58 (low).
# Bottom edge: SD 49-54 (right half).
PLACE = {
 # ref : (x, y, rot)          # rationale
 'U1' : (36.0, 21.0, 0),      # module centred; x 21..51, y 6..36
 # --- front (left edge): camera ---
 'J3' : ( 5.2, 18.0, 270),    # FH12 cable exits over the left edge; pins face module CSI pads (y 13.5-18.5)
 'C3' : (11.5, 21.5, 0),      # 10u  at J3 +3V3 pins (18/19)
 'C4' : (11.5, 19.0, 0),      # 100n at J3 +3V3 pins
 'R5' : (15.5, 20.0, 90),     # I2C pull-ups next to module pads 16/17 (y 22.5/23.5)
 'R6' : (17.5, 20.0, 90),
 # --- rear-left (bottom edge): USB-C and 5 V chain ---
 'J1' : (11.0, 38.5, 0),      # receptacle opening on the bottom edge
 'R1' : ( 9.0, 31.8, 0),      # CC1 5k1 near A5
 'R2' : (16.5, 32.6, 0),      # CC2 5k1 near B5
 'U2' : (17.0, 30.0, 0),      # USBLC6 in-line between J1 D+/D- and module pads 22/23 (y 28.5/29.5)
 'R7' : (18.9, 32.6, 0),      # VBUS_DET divider near pad 24 (y 30.5)
 'R8' : (18.9, 26.8, 0),
 'R9' : (18.9, 34.8, 90),     # 1k series on SARADC_IN0 (pad 26, y 32.5)
 'F1' : ( 9.0, 29.5, 0),      # polyfuse first in the VBUS chain
 'C1' : (13.2, 29.5, 0),      # 47u bulk on +5V
 'C2' : (12.5, 31.8, 0),      # 100n on +5V
 'D1' : (14.0, 25.0, 0),      # TVS on +5V
 # --- side (right edge): microSD, power test points ---
 'J2' : (63.5, 30.18, 90),     # card inserts from the right edge; housing front 2.6 mm inside the edge so the card tip protrudes ~2 mm
 'C5' : (55.0, 21.0, 0),      # SD VDD decoupling, above the socket
 'C6' : (58.5, 21.0, 0),
 # Rev A2: local decoupling at the module's own power pads.  Pad 77 (+1V8) is at
 # (51,14.5) and pads 79-81 (+5V) at (51,10.5-12.5); the channel at x=53 between the
 # module edge (51.75) and the test-point pads (54.25) is the only place these belong.
 'C7' : (53.0, 15.5, 90),     # 100n on +1V8, 2.5 mm from pad 77
 'C8' : (53.0, 11.5, 90),     # 10u local bulk on +5V, beside pads 79-81
 'TP1': (55.0,  8.0, 0),      # +5V  (pads 79-81 at y 8.5-10.5)
 'TP2': (55.0, 11.0, 0),      # +3V3 (pad 78 at y 13.5)
 'TP3': (55.0, 14.0, 0),      # GND
 'R3' : (55.0, 17.5, 0),      # nPOR pull-up at pad 74 (y 17.5)
 'D2' : (56.0, 40.0, 0),      # status LED, rear-right corner, visible
 'R4' : (60.0, 40.0, 0),
 # --- top edge: debug header and reset ---
 'H1' : (48.0,  2.5, 90),     # 1x5 header along the top edge, pin 1 at x=48
 'S1' : (66.0,  3.0, 0),      # reset button, top-right corner
}

for i,(x,y) in enumerate(HOLES): PLACE[f'MH{i+1}']=(x,y,0)
EXTRA = {}

# Copper zones: (net, layer, priority)  -- full-board polygons, filled by KiCad
# Copper zones: (net, layer, priority). Higher priority fills first and wins overlaps.
#   In1.Cu  = SOLID GND. This is the impedance reference for every L1 trace - never break it.
#   In2.Cu  = POWER layer, deliberately left free of zones so rails can be poured as islands
#             (+5V / +3V3 / +1V8). A full-board GND pour here would block power vias.
#   F.Cu / B.Cu = GND fill around the routing.
ZONES = [('GND','In1.Cu',0), ('GND','B.Cu',0), ('GND','F.Cu',0)]
