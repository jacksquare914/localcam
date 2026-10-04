#!/usr/bin/env bash
# =============================================================================
#  LocalCam-1 Rev A2  --  one-shot JLCPCB output generator
#
#  Run this on YOUR machine, where KiCad 10 lives.  The cloud container only has
#  kicad-cli 7, which cannot read a version-10 board file, so this has to run
#  where the real KiCad is.
#
#      chmod +x make-fab.sh
#      ./make-fab.sh
#
#  Output: fab/LocalCam1-Rev-A2-JLCPCB.zip  -- upload that file as-is.
#  Also writes fab/DRC.rpt; read it before you order.
#
#  BEFORE running: open the board in KiCad, press B to fill the zones, and save.
#  Unfilled zones plot as empty copper and the ground plane would simply not exist.
#  (kicad-cli does refill on plot in recent builds, but do not bet a board order on it.)
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

PCB=LocalCam1.kicad_pcb
SCH=LocalCam1.kicad_sch
OUT=fab
GBR=$OUT/gerbers
NAME=LocalCam1-Rev-A2-JLCPCB

command -v kicad-cli >/dev/null || { echo "kicad-cli not on PATH.
  macOS: /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
  Windows: C:\\Program Files\\KiCad\\10.0\\bin\\kicad-cli.exe"; exit 1; }
echo "kicad-cli: $(kicad-cli version)"
[ -f "$PCB" ] || { echo "$PCB not found -- run this from the folder that holds it"; exit 1; }

rm -rf "$OUT"; mkdir -p "$GBR"

# --- 1. DRC first.  If this is not clean, stop and fix it, do not order. --------
echo "== DRC =="
kicad-cli pcb drc --output "$OUT/DRC.rpt" --schematic-parity \
  --severity-error --severity-warning --exit-code-violations "$PCB" || DRC_FAIL=1
grep -E "^\*\*|violations|errors|warnings" "$OUT/DRC.rpt" | head -20 || true

# --- 2. Gerbers.  Four copper layers, both masks, both silks, both pastes, edge.
#     --subtract-soldermask keeps silk off the pads, which is what JLCPCB expects.
echo "== gerbers =="
kicad-cli pcb export gerbers --output "$GBR/" \
  --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" \
  --subtract-soldermask --no-x2 --use-drill-file-origin "$PCB"

# --- 3. Drill.  Excellon, mm, absolute origin, PTH and NPTH in separate files. --
echo "== drill =="
kicad-cli pcb export drill --output "$GBR/" --format excellon \
  --drill-origin absolute --excellon-units mm --excellon-zeros-format decimal \
  --excellon-separate-th --generate-map-file --map-format gerberx2 "$PCB"

# --- 4. Assembly data, in JLCPCB's column order. -------------------------------
echo "== BOM and placement =="
kicad-cli sch export bom --output "$OUT/$NAME-BOM.csv" \
  --fields 'Reference,Value,Footprint,${QUANTITY}' \
  --labels 'Designator,Comment,Footprint,Qty' \
  --group-by 'Value,Footprint' --ref-range-delimiter '' "$SCH"

kicad-cli pcb export pos --output "$OUT/$NAME-CPL.csv" \
  --side both --format csv --units mm --use-drill-file-origin --exclude-dnp "$PCB"

# JLCPCB wants the CPL header as Designator,Mid X,Mid Y,Layer,Rotation
python3 - "$OUT/$NAME-CPL.csv" <<'PY'
import csv,sys
p=sys.argv[1]; rows=list(csv.reader(open(p)))
if rows:
    hdr=[h.strip().lower() for h in rows[0]]
    def col(*names):
        for n in names:
            if n in hdr: return hdr.index(n)
        return None
    i=(col('ref','designator'),col('posx','x','mid x'),col('posy','y','mid y'),
       col('side','layer'),col('rot','rotation'))
    if all(x is not None for x in i):
        out=[['Designator','Mid X','Mid Y','Layer','Rotation']]
        for r in rows[1:]:
            if not r: continue
            side='top' if r[i[3]].strip().lower().startswith('t') else 'bottom'
            out.append([r[i[0]],r[i[1]],r[i[2]],side,r[i[4]]])
        csv.writer(open(p,'w',newline='')).writerows(out)
        print(f'   CPL rewritten in JLCPCB column order: {len(out)-1} parts')
PY

# --- 5. Zip.  JLCPCB takes the gerbers+drill archive; BOM/CPL upload separately.
echo "== zip =="
( cd "$GBR" && zip -q -r "../$NAME.zip" . )
echo
echo "----------------------------------------------------------------"
echo " upload to JLCPCB:   $OUT/$NAME.zip"
echo " assembly BOM:       $OUT/$NAME-BOM.csv"
echo " assembly placement: $OUT/$NAME-CPL.csv"
echo " read first:         $OUT/DRC.rpt"
echo
echo " JLCPCB order settings for this board:"
echo "   Layers 4        Thickness 1.6 mm       Impedance control: YES"
echo "   Stackup JLC04161H-7628   (this is what the 100 ohm / 90 ohm"
echo "                             geometry was calculated against -- if you"
echo "                             let them pick a different stackup the"
echo "                             camera pairs are no longer 100 ohm)"
echo "   Outer copper 1 oz        Inner copper 0.5 oz"
echo "   Min track/gap 0.15 mm    Via 0.6/0.3 mm     Surface: HASL or ENIG"
echo "   Remove order number: specify a location, or 'No' if you do not mind"
echo "----------------------------------------------------------------"
[ "${DRC_FAIL:-0}" = "1" ] && echo " !! DRC reported violations -- open $OUT/DRC.rpt before ordering."
