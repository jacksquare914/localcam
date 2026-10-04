"""LocalCam-1: build LocalCam1.kicad_pcb (KiCad 10 dialect) from spec.py + placement.py.
Footprints come verbatim from the workstation's KiCad 10 libraries (fplib10) and Luckfox's
Core1106-PCB.pretty; nets from spec.py; positions from placement.py.  Never hand-edit the output."""
import sys, uuid, datetime, os
sys.path.insert(0,'/home/claude'); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, find, val, unq
from spec import PARTS, NETS
from placement import BOARD_W, BOARD_H, CORNER_R, HOLES, PLACE, EXTRA, ZONES

FPLIB='/home/claude/fplib10'
NS=uuid.UUID('6f1c2a44-3b7e-4d1a-9c55-0a1b2c3d4e5f')          # same namespace as gen.py
def UD(key): return str(uuid.uuid5(NS,key))
def q(s): return '"'+str(s).replace('\\','\\\\').replace('"','\\"')+'"'
def dump(n):
    if isinstance(n,str): return q(n[1:]) if n.startswith('"') else n
    return '('+' '.join(dump(x) for x in n)+')'
def S(txt): return parse(txt)                                  # small helper for literal nodes

# ---------- nets ----------
netnames=['']+sorted(NETS)                                     # index 0 = unconnected
netidx={n:i for i,n in enumerate(netnames)}
padnet={}                                                      # (ref,pin) -> net name
for n,conns in NETS.items():
    for ref,pin in conns: padnet[(ref,str(pin))]=n

# ---------- pin names (from the generated schematic) ----------
_sch=parse(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'LocalCam1.kicad_sch')).read())
_libs={unq(x[1]):x for x in find(find(_sch,'lib_symbols')[0],'symbol')}
def _pins(sym):
    out={}
    def walk(n):
        for p in find(n,'pin'): out[unq(val(p,'number'))]=unq(val(p,'name'))
        for sub in find(n,'symbol'): walk(sub)
    walk(sym); return out
pinname={}
for ref,(lib,name,_v,_fp,_at) in PARTS.items():
    for num,nm in _pins(_libs[f'{lib}:{name}']).items(): pinname[(ref,num)]=nm

# ---------- footprint loader ----------
def fp_path(lid):
    lib,name=lid.split(':')
    d = 'Core1106-PCB.pretty' if lib=='Core1106' else f'{lib}.pretty'
    return f'{FPLIB}/{d}/{name}.kicad_mod'
def load_fp(lid):
    return parse(open(fp_path(lid)).read())

def crtyd_bbox(fp):
    pts=[]
    for l in find(fp,'fp_line')+find(fp,'fp_rect')+find(fp,'fp_poly')+find(fp,'fp_circle')+find(fp,'fp_arc'):
        if unq(val(l,'layer'))!='F.CrtYd': continue
        for k in ('start','end','mid','center'):
            for a in find(l,k): pts.append((float(a[1]),float(a[2])))
        for pp in find(l,'pts'):
            for a in find(pp,'xy'): pts.append((float(a[1]),float(a[2])))
    if not pts: return None
    return (min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts))

def place_fp(lid, ref, value, xyr, sympath=None):
    fp=[x for x in load_fp(lid)]
    x,y,r=xyr
    # strip file-level tokens the board doesn't take, and any existing at/layer/path
    drop={'version','generator','generator_version','at','layer','path','sheetname','sheetfile','embedded_fonts'}
    body=[n for n in fp[2:] if not (isinstance(n,list) and n and n[0] in drop)]
    out=['footprint','"'+lid, ['layer','"F.Cu'],
         ['uuid','"'+UD('fp:'+ref)], ['at',f'{x:g}',f'{y:g}',f'{r:g}']]
    for n in body:
        if isinstance(n,list) and n and n[0]=='property':
            key=unq(n[1])
            if key=='Reference': n=[*n]; n[2]='"'+ref
            elif key=='Value':
                n=[*n]; n[2]='"'+value
                n=[z for z in n if not (isinstance(z,list) and z and z[0]=='hide')]
                k2=next(i for i,z in enumerate(n) if isinstance(z,list) and z and z[0]=='at')
                n.insert(k2+1,['layer','"F.Fab']); n.insert(k2+2,['hide','yes'])
        if isinstance(n,list) and n and n[0]=='property' and unq(n[1])=='Reference':
            # park the reference label just outside the courtyard, upright, on the side away from the board edge
            n=[*n]; k=next(i for i,z in enumerate(n) if isinstance(z,list) and z and z[0]=='at')
            import math; t=math.radians(r)
            cy=crtyd_bbox(fp) or (-1,-1,1,1)
            # courtyard corners into the board frame, take the vertical extent there
            cs=[(cx*math.cos(t)+cy_*math.sin(t), -cx*math.sin(t)+cy_*math.cos(t)) for cx in (cy[0],cy[2]) for cy_ in (cy[1],cy[3])]
            top=min(b for a,b in cs); bot=max(b for a,b in cs)
            dy = (bot+0.9) if y < 6.0 else (top-0.9)          # board-frame offset from the footprint origin
            lx,lyy = (-dy*math.sin(t), dy*math.cos(t))        # back to the footprint's local frame
            n[k]=['at',f'{lx:.3f}',f'{lyy:.3f}',f'{(-r)%360:g}']
            n=[z for z in n if not (isinstance(z,list) and z and z[0]=='hide')]
        if isinstance(n,list) and n and n[0] in ('property','fp_text','pad'):
            # KiCad stores pad/text angles ABSOLUTE (footprint rotation folded in); libraries store 0.
            n=[*n]; k=next((i for i,z in enumerate(n) if isinstance(z,list) and z and z[0]=='at'),None)
            if k is not None:
                a=[*n[k]]; ang=float(a[3]) if len(a)>3 else 0.0
                a=a[:3]+[f'{(ang+r)%360:g}']; n[k]=a
        if isinstance(n,list) and n and n[0]=='pad':
            pin=unq(n[1]); net=padnet.get((ref,pin))
            if not net and (ref,pin) in pinname:           # schematic pin with no net -> KiCad's unconnected-net name
                net=f'unconnected-({ref}-{pinname[(ref,pin)].replace("/","{slash}")}-Pad{pin})'
                if net not in netidx: netidx[net]=len(netnames); netnames.append(net)
            if net:
                k=next(i for i,z in enumerate(n) if isinstance(z,list) and z and z[0]=='layers')
                n.insert(k+1,['net',str(netidx[net]),'"'+net])
        out.append(n)
    if sympath:
        out.insert(5,['path','"/'+sympath]); out.insert(6,['sheetname','"/']); out.insert(7,['sheetfile','"LocalCam1.kicad_sch'])
    return out

# ---------- board ----------
L=[]
L.append('(kicad_pcb (version 20260206) (generator "pcbnew") (generator_version "10.0")')
L.append('  (general (thickness 1.6) (legacy_teardrops no))')
L.append('  (paper "A4")')
L.append(f'  (title_block (title "LocalCam-1 Rev A carrier") (date {q(datetime.date.today().isoformat())}) (rev "A") '
         '(comment 1 "Generated from spec.py + placement.py - do not hand-place") '
         '(comment 2 "Stack: JLCPCB JLC04161H-7628, L2 solid GND, MIPI 100R 0.22/0.18, USB 90R 0.27/0.18"))')
L.append('''  (layers
    (0 "F.Cu" signal) (4 "In1.Cu" signal "GND") (6 "In2.Cu" signal "PWR") (2 "B.Cu" signal)
    (9 "F.Adhes" user "F.Adhesive") (11 "B.Adhes" user "B.Adhesive") (13 "F.Paste" user) (15 "B.Paste" user)
    (5 "F.SilkS" user "F.Silkscreen") (7 "B.SilkS" user "B.Silkscreen") (1 "F.Mask" user) (3 "B.Mask" user)
    (17 "Dwgs.User" user "User.Drawings") (19 "Cmts.User" user "User.Comments") (21 "Eco1.User" user "User.Eco1")
    (23 "Eco2.User" user "User.Eco2") (25 "Edge.Cuts" user) (27 "Margin" user)
    (31 "F.CrtYd" user "F.Courtyard") (29 "B.CrtYd" user "B.Courtyard") (35 "F.Fab" user) (33 "B.Fab" user)
  )''')
L.append('''  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (color "Green") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "FR4 7628") (epsilon_r 4.4) (loss_tangent 0.02))
      (layer "In1.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
      (layer "In2.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "FR4 7628") (epsilon_r 4.4) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (color "Green") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
      (copper_finish "ENIG") (dielectric_constraints yes)
    )
    (pad_to_mask_clearance 0) (allow_soldermask_bridges_in_footprints no)
    (tenting (front yes) (back yes)) (covering (front no) (back no)) (plugging (front no) (back no)) (capping no) (filling no)
    (pcbplotparams (layerselection 0x00000000_00000000_00000030_80000001) (plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)
      (disableapertmacros no) (usegerberextensions no) (usegerberattributes yes) (usegerberadvancedattributes yes) (creategerberjobfile yes)
      (dashed_line_dash_ratio 12) (dashed_line_gap_ratio 3) (svgprecision 6) (plotframeref no) (mode 1) (useauxorigin no)
      (pdf_front_fp_property_popups yes) (pdf_back_fp_property_popups yes) (pdf_metadata yes) (pdf_single_document no)
      (dxfpolygonmode yes) (dxfimperialunits yes) (dxfusepcbnewfont yes) (psnegative no) (psa4output no) (plot_black_and_white yes)
      (sketchpadsonfab no) (plotpadnumbers no) (hidednponfab no) (sketchdnponfab yes) (crossoutdnponfab yes) (subtractmaskfromsilk no)
      (outputformat 1) (mirror no) (drillshape 1) (scaleselection 1) (outputdirectory "fab/"))
  )''')
NET_MARK=len(L)

# footprints from the schematic
nfp=0
for ref,(lib,name,value,fp,_at) in PARTS.items():
    if not fp: continue                                   # PWR_FLAGs have no footprint
    if ref not in PLACE: raise SystemExit(f'!! no placement for {ref}')
    L.append('  '+dump(place_fp(fp,ref,value,PLACE[ref],sympath=UD('sym:'+ref)))); nfp+=1
for ref,(fp,xyr) in EXTRA.items():
    L.append('  '+dump(place_fp(fp,ref,'M2',xyr))); nfp+=1

L[NET_MARK:NET_MARK]=[f'  (net {i} {q(n)})' for i,n in enumerate(netnames)]

# outline: rounded rectangle
W,H,R=BOARD_W,BOARD_H,CORNER_R
def gl(a,b): return f'  (gr_line (start {a[0]:g} {a[1]:g}) (end {b[0]:g} {b[1]:g}) (stroke (width 0.1) (type solid)) (layer "Edge.Cuts") (uuid {q(UD("edge:"+str(a)+str(b)))}))'
def ga(s,m,e): return f'  (gr_arc (start {s[0]:g} {s[1]:g}) (mid {m[0]:.4f} {m[1]:.4f}) (end {e[0]:g} {e[1]:g}) (stroke (width 0.1) (type solid)) (layer "Edge.Cuts") (uuid {q(UD("arc:"+str(s)+str(e)))}))'
c=0.70710678*R
L+= [gl((R,0),(W-R,0)), gl((W,R),(W,H-R)), gl((W-R,H),(R,H)), gl((0,H-R),(0,R)),
     ga((W-R,0),(W-R+c,R-c),(W,R)), ga((W,H-R),(W-R+c,H-R+c),(W-R,H)),
     ga((R,H),(R-c,H-R+c),(0,H-R)), ga((0,R),(R-c,R-c),(R,0))]
# silk title
L.append(f'  (gr_text "LocalCam-1  Rev A" (at 36 41.5 0) (layer "F.SilkS") (uuid {q(UD("txt:title"))}) (effects (font (size 1 1) (thickness 0.15))))')
# Zone outline: the board edge inset by EDGE_INSET, following the corner radius.
# A raw 0..W x 0..H rectangle would pour copper flush to the cut line and over the
# corner fillets -- JLCPCB wants 0.20 mm of copper-to-edge, so 0.25 mm it is.
EDGE_INSET = 0.25
def zone_pts(inset):
    w,h,r = W-inset, H-inset, max(0.0, R-inset)
    x0=y0=inset; x1,y1=w,h
    pts=[]
    import math as _m
    for cx,cy,a0 in ((x1-r,y1-r,0.0),(x0+r,y1-r,90.0),(x0+r,y0+r,180.0),(x1-r,y0+r,270.0)):
        for k in range(5):
            a=_m.radians(a0+k*22.5)
            pts.append((cx+r*_m.cos(a), cy+r*_m.sin(a)))
    return ' '.join(f'(xy {x:.4f} {y:.4f})' for x,y in pts)
ZPTS = zone_pts(EDGE_INSET)

for net,layer,prio in ZONES:
    L.append(f'''  (zone (net {netidx[net]}) (net_name {q(net)}) (layer {q(layer)}) (uuid {q(UD("zone:"+net+layer))}) (name {q(net+"_"+layer)})
    (hatch edge 0.5) (priority {prio}) (connect_pads (clearance 0.2)) (min_thickness 0.25) (filled_areas_thickness no)
    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.4))
    (polygon (pts {ZPTS})))''')
L.append('  (embedded_fonts no)')
L.append(')')
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'LocalCam1.kicad_pcb'),'w').write('\n'.join(L)+'\n')
print(f'wrote LocalCam1.kicad_pcb  footprints={nfp} nets={len(netnames)-1} board={W}x{H}')
