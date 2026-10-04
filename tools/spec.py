# ============================================================================
#  LocalCam-1 Rev A2  --  NETLIST SOURCE OF TRUTH
#  Edit this file only. The schematic is a build output; never hand-edit it.
# ============================================================================
import os

# Where the KiCad stock symbol libraries live, and the Core1106 symbol that ships
# with this repo.  Override either with an environment variable so this runs on a
# machine other than the one it was written on:
#
#   KICAD_SYMBOL_DIR=/usr/share/kicad/symbols python3 gen.py
#
_HERE = os.path.dirname(os.path.abspath(__file__))
SYMLIB   = os.environ.get('KICAD_SYMBOL_DIR') or os.path.join(
               os.path.dirname(_HERE), 'hardware', 'lib', 'kicad-symbols')
if not os.path.isdir(SYMLIB):
    for _c in ('/usr/share/kicad/symbols',
               '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols',
               r'C:\Program Files\KiCad\10.0\share\kicad\symbols'):
        if os.path.isdir(_c): SYMLIB = _c; break
CORE_SYM = os.environ.get('CORE1106_SYM') or os.path.join(
               os.path.dirname(_HERE), 'hardware', 'lib', 'Core1106.kicad_sym')

# ---- Core1106 ground pads (from Core1106-PinOut.xls) ----
U1_GND = [21,25,28,29,36,47,55,56,57,75,82,83,84,89,112]

PARTS = {
 # ref : (symbol lib, symbol name, value, footprint, sheet position mm)
 'U1' : ('Core1106','Core1106','Core1106 (RV1106G3)','Core1106:Core1106-SMT',(40,30)),
 'J1' : ('Connector','USB_C_Receptacle_USB2.0_16P','USB-C 2.0',
         'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',(70,250)),
 'U2' : ('Power_Protection','USBLC6-2SC6','USBLC6-2SC6','Package_TO_SOT_SMD:SOT-23-6',(155,250)),
 'F1' : ('Device','Polyfuse','1.5A hold','Resistor_SMD:R_1206_3216Metric',(200,240)),
 'D1' : ('Device','D_TVS','SMAJ6.0CA','Diode_SMD:D_SMA',(230,250)),
 'C1' : ('Device','C','47uF/16V','Capacitor_SMD:C_0805_2012Metric',(260,250)),
 'C2' : ('Device','C','100nF','Capacitor_SMD:C_0402_1005Metric',(280,250)),
 'R1' : ('Device','R','5.1k','Resistor_SMD:R_0402_1005Metric',(310,250)),
 'R2' : ('Device','R','5.1k','Resistor_SMD:R_0402_1005Metric',(330,250)),
 'R3' : ('Device','R','10k','Resistor_SMD:R_0402_1005Metric',(350,250)),
 'S1' : ('Switch','SW_Push','RESET','Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2',(380,250)),
 # Micro_SD_Card has no pins 9/10, so the detect switch could not be drawn.
 # Micro_SD_Card_Det2 has 1-10 + SH, matching the DM3AT footprint pin for pin.
 'J2' : ('Connector','Micro_SD_Card_Det2','microSD (DM3AT)','Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5',(110,330)),
 'J3' : ('Connector_Generic','Conn_01x24','FPC 0.5mm 24p to SC3336',
         'Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal',(230,345)),
 'H1' : ('Connector_Generic','Conn_01x05','DEBUG UART',
         'Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical',(330,330)),
 'R5' : ('Device','R','4.7k','Resistor_SMD:R_0402_1005Metric',(380,330)),
 'R6' : ('Device','R','4.7k','Resistor_SMD:R_0402_1005Metric',(400,330)),
 'R4' : ('Device','R','330R','Resistor_SMD:R_0402_1005Metric',(430,330)),
 'R7' : ('Device','R','100k','Resistor_SMD:R_0402_1005Metric',(430,240)),
 'R8' : ('Device','R','100k','Resistor_SMD:R_0402_1005Metric',(450,240)),
 'R9' : ('Device','R','1k','Resistor_SMD:R_0402_1005Metric',(410,300)),
 'C3' : ('Device','C','10uF/16V','Capacitor_SMD:C_0805_2012Metric',(170,345)),
 'C4' : ('Device','C','100nF','Capacitor_SMD:C_0402_1005Metric',(190,345)),
 'C5' : ('Device','C','10uF/16V','Capacitor_SMD:C_0805_2012Metric',(60,330)),
 'C6' : ('Device','C','100nF','Capacitor_SMD:C_0402_1005Metric',(80,330)),
 'D2' : ('Device','LED','STATUS red Vf~2.0V','LED_SMD:LED_0603_1608Metric',(460,330)),
 # Rev A2: +1V8 had no decoupling at all, and the +5V bulk (C1) sits 71 mm and
 # ~100 mohm away from the module's power pins -- 60 mV of droop at 0.6 A with nothing
 # local to absorb a WiFi transmit step.  C7/C8 are local to U1's own pads.
 'C7' : ('Device','C','100nF','Capacitor_SMD:C_0402_1005Metric',(540,240)),
 'C8' : ('Device','C','10uF/16V','Capacitor_SMD:C_0805_2012Metric',(540,270)),
 'TP1': ('Connector','TestPoint','+5V','TestPoint:TestPoint_Pad_D1.5mm',(480,240)),
 'TP2': ('Connector','TestPoint','+3V3','TestPoint:TestPoint_Pad_D1.5mm',(500,240)),
 'TP3': ('Connector','TestPoint','GND','TestPoint:TestPoint_Pad_D1.5mm',(520,240)),
 'MH1': ('Mechanical','MountingHole','M2','MountingHole:MountingHole_2.2mm_M2',(560,300)),
 'MH2': ('Mechanical','MountingHole','M2','MountingHole:MountingHole_2.2mm_M2',(575,300)),
 'MH3': ('Mechanical','MountingHole','M2','MountingHole:MountingHole_2.2mm_M2',(560,320)),
 'MH4': ('Mechanical','MountingHole','M2','MountingHole:MountingHole_2.2mm_M2',(575,320)),
 'PWR1': ('power','PWR_FLAG','PWR_FLAG','',(480,200)),
 'PWR4': ('power','PWR_FLAG','PWR_FLAG','',(540,200)),
}

# ---- J3: the camera FPC pinout. This is OUR connector (the SC3336 satellite
#      board is our design), so this ordering defines it. Grounds flank each
#      differential pair for return-path integrity. ----
J3 = {1:'GND', 2:'CSI_D1_N', 3:'CSI_D1_P', 4:'GND', 5:'CSI_CLK_N', 6:'CSI_CLK_P',
      7:'GND', 8:'CSI_D0_N', 9:'CSI_D0_P',10:'GND',11:'MCLK0',      12:'GND',
     13:'CAM_SCL',14:'CAM_SDA',15:'CAM_RST',16:'CAM_PWDN',17:'GND', 18:'+3V3',
     19:'+3V3', 20:'GND',21:'+1V8',22:'NC2',23:'GND',24:'GND'}

NETS = {
 # ---------------- power ----------------
 'VBUS_IN' : [('J1','A4'),('J1','A9'),('J1','B4'),('J1','B9'),('F1','1')],
 '+5V'     : [('F1','2'),('D1','1'),('C1','1'),('C2','1'),('U2','5'),
              ('U1','79'),('U1','80'),('U1','81'),('TP1','1'),('C8','1'),
              # FIX (A-9): R7 was on +3V3, making the "VBUS detect" divider a fixed
              # 1.65 V -- below a 3V3 GPIO's V_IH, i.e. parked in the indeterminate
              # band.  Off +5V the divider gives 2.5 V, a valid logic high, and it
              # actually tracks the supply the way the comment below always claimed.
              ('R7','1')],
 '+3V3'    : [('U1','78'),('R3','2'),('C3','1'),('C4','1'),('C5','1'),('C6','1'),
              ('J2','4'),('H1','4'),('TP2','1')]
             + [('J3',str(p)) for p,n in J3.items() if n=='+3V3'],
 'GND'     : [('J1','A1'),('J1','A12'),('J1','B1'),('J1','B12'),('J1','SH'),
              ('D1','2'),('C1','2'),('C2','2'),('U2','2'),('R1','2'),('R2','2'),
              ('S1','2'),('J2','6'),('J2','SH'),('H1','1'),('D2','1'),('TP3','1'),
              ('R8','2'),('C3','2'),('C4','2'),('C5','2'),('C6','2'),
              ('C7','2'),('C8','2'),
              # FIX (A-16): J2 pins 9/10 are the DM3AT card-detect switch and were not in
              # this netlist at all -- so they carried no net, which means no connectivity
              # check could ever report them as unconnected.  Grounding both ends leaves
              # the switch harmless and stops the node floating.  For card-detect in
              # software instead, move pin 9 to a spare module GPIO with a pull-up.
              ('J2','9'),('J2','10')]
             + [('U1',str(p)) for p in U1_GND]
             + [('J3',str(p)) for p,n in J3.items() if n=='GND'],
 # ---------------- USB ----------------
 'CC1'        : [('J1','A5'),('R1','1')],
 'CC2'        : [('J1','B5'),('R2','1')],
 'USB_DP_CON' : [('J1','A6'),('J1','B6'),('U2','3')],
 'USB_DM_CON' : [('J1','A7'),('J1','B7'),('U2','1')],
 'USB_DP'     : [('U2','4'),('U1','23')],
 'USB_DM'     : [('U2','6'),('U1','22')],
 # ---------------- reset / recovery ----------------
 'NPOR_RST'   : [('U1','74'),('R3','1'),('S1','1')],
 'ADC0_RECOV' : [('U1','26'),('R9','1')],
 # ---------------- camera (MIPI CSI-2, 2 lane) ----------------
 'CSI_CLK_P'  : [('U1','10'),('J3','6')],
 'CSI_CLK_N'  : [('U1','9') ,('J3','5')],
 'CSI_D0_P'   : [('U1','12'),('J3','9')],
 'CSI_D0_N'   : [('U1','11'),('J3','8')],
 'CSI_D1_P'   : [('U1','8') ,('J3','3')],
 'CSI_D1_N'   : [('U1','7') ,('J3','2')],
 'MCLK0'      : [('U1','19'),('J3','11')],
 'CAM_SCL'    : [('U1','16'),('J3','13'),('R5','2')],   # I2C4_SCL_M2 = Luckfox 'MIPI_I2C_SCL' (A-8)
 'CAM_SDA'    : [('U1','17'),('J3','14'),('R6','2')],   # I2C4_SDA_M2 = Luckfox 'MIPI_I2C_SDA' (A-8)
 # FIX: camera bank is a 1.8 V IO domain - pull-ups must go to VCC_1V8 (pad 77),
 # never to 3V3, or the 1.8 V pins are over-driven.
 '+1V8'       : [('U1','77'),('R5','1'),('R6','1'),('J3','21'),('C7','1')],
 # FIX: USB_VBUSDET (pad 24) was floating. Divide VBUS 2:1 into the detect input.
 'VBUS_DET'   : [('U1','24'),('R7','2'),('R8','1')],
 # FIX: series resistor protects the 1.8 V SARADC input brought out on the header.
 'RECOV_HDR'  : [('R9','2'),('H1','5')],
 'CAM_RST'    : [('U1','18'),('J3','15')],
 'CAM_PWDN'   : [('U1','13'),('J3','16')],
 # ---------------- microSD (SDMMC) ----------------
 'SD_D0'  : [('U1','49'),('J2','7')],
 'SD_D1'  : [('U1','50'),('J2','8')],
 'SD_D2'  : [('U1','51'),('J2','1')],
 'SD_D3'  : [('U1','52'),('J2','2')],
 'SD_CMD' : [('U1','53'),('J2','3')],
 'SD_CLK' : [('U1','54'),('J2','5')],
 # ---------------- debug UART (UART2 M1 - clear of the SD pins) ----------------
 'UART2_TX' : [('U1','72'),('H1','3')],
 'UART2_RX' : [('U1','73'),('H1','2')],
 # ---------------- status LED ----------------
 'LED_STAT' : [('U1','58'),('R4','1')],
 'LED_A'    : [('R4','2'),('D2','2')],
}

# NOTE pad 76 VCC3V3_RTC is deliberately NC: on the module it is VCC_3V3 -> D1 (RB521S-30) -> pad76 -> 100R -> RTC_AVDD3V3.
#      It is the RTC backup-battery/supercap tap, not a supply. Tying it to +3V3 would short across D1. (Core1106 sch, PART A)

# --- PWR_FLAG on the two rails no symbol sources: +5V (USB-C VBUS pins are passive) and GND.
#     +3V3/+1V8 are sourced by U1 pins 78/77, typed power_out in lib/Core1106.kicad_sym (see patch_core1106.py) ---
NETS['+5V'].append(('PWR1','1'))
NETS['GND'].append(('PWR4','1'))
