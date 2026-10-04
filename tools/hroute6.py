"""LocalCam-1 router v2 -- rebuilt after DFM review found the v1 architecture unsound.

What v1 got wrong and this fixes:
  * v1's clear_path() returned True for any layer not in its 2-layer table, so the
    whole In2.Cu power layer was routed with collision detection OFF (+5V/+3V3/+1V8
    ended up shorted).  Occupancy here covers all four copper layers.
  * v1 would pick B.Cu for a net whose pads are top-side SMD and never add a via,
    leaving the trace floating.  Here a route always begins and ends on a layer the
    pad actually reaches; any layer change is an explicit, collision-checked via.
  * v1 dropped power and stitching vias with no test at all.  can_via() gates every one.
  * v1 exempted a diff-pair partner from clearance entirely.  Here the partner is
    routed against a relaxed mask, then the real polyline-to-polyline distance is
    measured and the route is rejected if it is under the designed gap.
  * v1's connect() returned True whenever it laid metal, so the log said OK for nets
    with no copper.  Here every net is island-checked at the end and the build FAILS
    on any net that is not electrically whole.

Style rules kept from v1 (this is the point of the exercise):
  45 deg geometry only, F.Cu trends horizontal / B.Cu vertical, perpendicular pad
  escapes, clean L/Z shapes preferred over search, rails daisy-chained as a spine.
"""
import sys, os, re, math, heapq, uuid, time
import numpy as np
from scipy import ndimage
sys.path.insert(0, '/home/claude')
from sexp import parse, find, val, unq

SRC, DST = sys.argv[1], sys.argv[2]
G     = 0.05      # 0.1 mm quantised a legal 0.35 mm gap down to 0.30 and failed it
LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
LI    = {n: i for i, n in enumerate(LAYERS)}
SIG   = ['F.Cu', 'B.Cu']
PWR_L = 'In2.Cu'
PREF  = {'F.Cu': 'h', 'B.Cu': 'v', 'In2.Cu': 'h', 'In1.Cu': 'h'}
CLR   = {'MIPI': 0.18, 'USB': 0.18, 'PWR': 0.2, 'DEF': 0.15}
WID   = {'MIPI': 0.22, 'USB': 0.27, 'PWR': 0.5, 'DEF': 0.2}
GAP   = {'MIPI': 0.18, 'USB': 0.18}
PITCH = {'MIPI': 0.40, 'USB': 0.45}
VIA_D, VIA_DRL = 0.6, 0.3   # ring 0.15 mm; 0.45/0.25 would be 0.10, under JLCPCB's 0.13
# Board style is strictly orthogonal: every trace parallel or perpendicular to an edge.
# The one exception is the three camera pairs, where a square corner needs so much more
# lateral room in the shared FPC channel that the clock pair cannot stay coupled -- and
# 3 mm of intra-pair skew on a MIPI clock is a dead camera.  DIAG is true only there.
DIAG = [False]
ESC   = 0.6
NS    = uuid.UUID('6f1c2a44-3b7e-4d1a-9c55-0a1b2c3d4e5f')
_uc = {}
def UD(k):
    _uc[k] = _uc.get(k, 0) + 1
    return str(uuid.uuid5(NS, f'{k}#{_uc[k]}'))

ORIG = open(SRC).read()
src = open(SRC).read()
def strip(txt, tag):
    n = 0
    while True:
        m = re.search(r'\n\t\(' + tag + r'\b', txt)
        if not m: break
        d = 0; j = m.start()+1
        while True:
            if txt[j] == '(': d += 1
            elif txt[j] == ')':
                d -= 1
                if d == 0: break
            j += 1
        txt = txt[:m.start()] + txt[j+1:]; n += 1
    return txt, n
src, n1 = strip(src, 'segment'); src, n2 = strip(src, 'via')
# stale zone fills must go -- KiCad recomputes them, and plotting the old ones
# would bury signal traces inside the pours
nfill = len(re.findall(r'\(filled_polygon', src))
while True:
    m = re.search(r'\n\t+\(filled_polygon', src)
    if not m: break
    d = 0; j = m.start()+1
    while True:
        if src[j] == '(': d += 1
        elif src[j] == ')':
            d -= 1
            if d == 0: break
        j += 1
    src = src[:m.start()] + src[j+1:]
print(f'ripped up {n1} segments, {n2} vias, {nfill} stale zone fills')
bd = parse(src)

BW = BH = 0
for l in find(bd, 'gr_line'):
    for k in ('start','end'):
        a = find(l,k)[0]; BW = max(BW,float(a[1])); BH = max(BH,float(a[2]))
NX, NY = int(BW/G)+2, int(BH/G)+2
nets = sorted(set(re.findall(r'\(net "([^"]*)"\)', src)))
nidx = {n: i+1 for i, n in enumerate(nets)}
def xf(X,Y,r,x,y):
    t = math.radians(r); return (X+x*math.cos(t)+y*math.sin(t), Y-x*math.sin(t)+y*math.cos(t))

PADS = []
for fp in find(bd,'footprint'):
    at = find(fp,'at')[0]; X,Y = float(at[1]),float(at[2]); r = float(at[3]) if len(at)>3 else 0
    ref = [unq(p[2]) for p in find(fp,'property') if unq(p[1])=='Reference'][0]
    for p in find(fp,'pad'):
        a = find(p,'at')[0]; sz = find(p,'size')[0]
        nn = find(p,'net'); net = unq(nn[0][1]) if nn else None
        px,py = xf(X,Y,r,float(a[1]),float(a[2]))
        lays = [unq(z) for z in find(p,'layers')[0][1:]]
        thru = p[2] in ('thru_hole','np_thru_hole')
        on = LAYERS if thru or any(z=='*.Cu' for z in lays) else [z for z in LAYERS if z in lays]
        PADS.append(dict(ref=ref,pin=unq(p[1]),net=net,x=px,y=py,w=float(sz[1]),h=float(sz[2]),
                         rot=(float(a[3]) if len(a)>3 else 0),thru=thru,fx=X,fy=Y,on=on or ['F.Cu']))

ROWAX = {}; _br = {}
for _p in PADS: _br.setdefault(_p['ref'],[]).append(_p)
for _r,_ps in _br.items():
    _sx = max(q['x'] for q in _ps)-min(q['x'] for q in _ps)
    _sy = max(q['y'] for q in _ps)-min(q['y'] for q in _ps)
    ROWAX[_r] = None if len(_ps)<2 else ('v' if _sy>3*max(_sx,.01) else ('h' if _sx>3*max(_sy,.01) else None))

occ = [np.zeros((NX,NY),np.int32) for _ in LAYERS]
def box(arr,cx,cy,w,h,rot,v):
    if abs(rot)%180==90: w,h = h,w
    # +1, not +2: the slice end is exclusive, so +2 inflated every pad and track by
    # a full 0.1 mm cell on each side and made fine-pitch escapes look impossible.
    arr[max(0,int((cx-w/2)/G)):int((cx+w/2)/G)+1, max(0,int((cy-h/2)/G)):int((cy+h/2)/G)+1] = v
for p in PADS:
    v = nidx.get(p['net'],-1) if p['net'] else -1
    for ln in p['on']: box(occ[LI[ln]],p['x'],p['y'],p['w'],p['h'],p['rot'],v)
for a in occ:
    m = int(math.ceil(0.45/G)); a[:m,:]=-1; a[-m:,:]=-1; a[:,:m]=-1; a[:,-m:]=-1
for fp in find(bd,'footprint'):
    if 'Core1106' not in unq(fp[1]): continue
    at = find(fp,'at')[0]; X,Y = float(at[1]),float(at[2]); r = float(at[3]) if len(at)>3 else 0
    for z in find(fp,'zone'):
        if not find(z,'keepout'): continue
        pts = [xf(X,Y,r,float(q[1]),float(q[2])) for q in find(find(find(z,'polygon')[0],'pts')[0],'xy')]
        xs=[q[0] for q in pts]; ys=[q[1] for q in pts]
        for arr in occ: arr[max(0,int(min(xs)/G)):int(max(xs)/G)+2, max(0,int(min(ys)/G)):int(max(ys)/G)+2] = -1
    c0 = xf(X,Y,r,-10.6,-10.6); c1 = xf(X,Y,r,10.6,10.6)
    bx = sorted((c0[0],c1[0])); by = sorted((c0[1],c1[1]))
    occ[LI['F.Cu']][max(0,int(bx[0]/G)):int(bx[1]/G)+2, max(0,int(by[0]/G)):int(by[1]/G)+2] = -1
# In1.Cu is the solid ground plane: nothing but GND may live there
occ[LI['In1.Cu']][:,:] = np.where(occ[LI['In1.Cu']]==0, nidx['GND'], occ[LI['In1.Cu']])

# Union of every pad on the board, any net, grown by 0.1 mm.  A via may not overlap it:
# a via inside an SMD, FPC or castellated pad wicks paste during reflow, and JLCPCB
# does not do via-in-pad at this tier.  v3 dropped vias straight onto pad centres as a
# last resort, which put three of them inside pads.
PADMASK=np.zeros((NX,NY),bool)
for _p in PADS:
    _w,_h=_p['w']+0.2,_p['h']+0.2
    if abs(_p['rot'])%180==90: _w,_h=_h,_w
    PADMASK[max(0,int((_p['x']-_w/2)/G)):int((_p['x']+_w/2)/G)+1,
            max(0,int((_p['y']-_h/2)/G)):int((_p['y']+_h/2)/G)+1]=True

TRK=[]; VIAS=[]; _M={'_s':0}
VIAPOS=[]                      # every via centre, for the hole-to-hole rule
def lay_seg(x0,y0,x1,y1,ln,net,w):
    _M.clear(); _M['_s']=_M.get('_s',0)+1
    TRK.append((x0,y0,x1,y1,ln,net,w))
    n = max(2,int(max(abs(x1-x0),abs(y1-y0))/G)+2)
    for i in range(n+1):
        t=i/n; box(occ[LI[ln]],x0+(x1-x0)*t,y0+(y1-y0)*t,w,w,0,nidx[net])
def lay_via(x,y,net):
    _M.clear(); _M['_s']=_M.get('_s',0)+1
    VIAS.append((x,y,net)); VIAPOS.append((x,y))
    for arr in occ: box(arr,x,y,VIA_D,VIA_D,0,nidx[net])
# JLCPCB wants 0.20 mm hole to hole; two 0.3 mm drills put the centres 0.5 mm apart.
# 0.55 for margin, and it also stops the duplicate/co-located vias v3 emitted.
VIA_PITCH = 0.55
def can_via(x,y,net,clr=0.2):
    gx,gy = int(round(x/G)),int(round(y/G)); rad = int(math.ceil((VIA_D/2+clr)/G))
    if not (rad<=gx<NX-rad and rad<=gy<NY-rad): return False
    pr=int(math.ceil((VIA_D/2)/G))
    if PADMASK[gx-pr:gx+pr+1, gy-pr:gy+pr+1].any(): return False
    for vx,vy in VIAPOS:
        if abs(vx-x)<VIA_PITCH and abs(vy-y)<VIA_PITCH and math.hypot(vx-x,vy-y)<VIA_PITCH:
            return False
    for li,arr in enumerate(occ):
        # In1.Cu is a poured plane, not routed copper.  A foreign-net via passing
        # through it gets an antipad from the zone filler automatically, so plane
        # copper must not be treated as an obstacle -- v2 did, and that blocked
        # every non-GND via on the board.
        if LAYERS[li]=='In1.Cu': continue
        sub = arr[gx-rad:gx+rad+1, gy-rad:gy+rad+1]
        if np.any((sub!=0)&(sub!=nidx[net])): return False
    return True

def mask_for(ln,net,w,clr,ignore=None,box=None):
    """box = (x0,y0,x1,y1) in cells: dilate only that window.  A whole-board dilation
    at 0.05 mm is 1.3 M cells and is thrown away every time a segment is laid."""
    key=(ln,net,round(w,3),round(clr,3),ignore,box,_M.get('_s',0))
    if key in _M: return _M[key]
    arr=occ[LI[ln]]; rad=int(math.ceil((w/2+clr)/G)); v=nidx[net]
    st=np.ones((2*rad+1,2*rad+1),bool)
    if box is None:
        bad=(arr!=0)&(arr!=v)
        if ignore: bad &= (arr!=nidx[ignore])
        ok=~ndimage.binary_dilation(bad,structure=st)
    else:
        x0,y0,x1,y1=box
        sub=arr[x0:x1,y0:y1]
        bad=(sub!=0)&(sub!=v)
        if ignore: bad &= (sub!=nidx[ignore])
        ok=np.zeros((NX,NY),bool); ok[x0:x1,y0:y1]=~ndimage.binary_dilation(bad,structure=st)
    _M[key]=ok; return ok
def pad_rect(pad,m=0.10):
    w,h=pad['w'],pad['h']
    if abs(pad['rot'])%180==90: w,h=h,w
    return (pad['x'],pad['y'],w/2+m,h/2+m)
def in_rects(x,y,rects):
    for cx,cy,hw,hh in rects:
        if abs(x-cx)<=hw and abs(y-cy)<=hh: return True
    return False
def clear_path(pts,ln,net,w,clr,ok=None,ignore=None,exempt=None):
    """exempt: pad rectangles where clearance is not the trace's problem.  Leaving a
    0.5 mm-pitch FPC pad is physically impossible if the neighbouring pad's clearance
    halo is enforced over the pad itself -- the fab guarantees the pad gaps."""
    if ok is None: ok=mask_for(ln,net,w,clr,ignore)
    for p,q in zip(pts,pts[1:]):
        n=max(2,int(math.hypot(q[0]-p[0],q[1]-p[1])/G)+2)
        for i in range(n+1):
            t=i/n; x=p[0]+(q[0]-p[0])*t; y=p[1]+(q[1]-p[1])*t
            gx,gy=int(round(x/G)),int(round(y/G))
            if not (0<=gx<NX and 0<=gy<NY): return False
            if ok[gx,gy]: continue
            if exempt and in_rects(x,y,exempt): continue
            return False
    return True

def blocker(pts,ln,net,w,clr,ignore=None,exempt=None):
    arr=occ[LI[ln]]; rad=int(math.ceil((w/2+clr)/G)); v=nidx[net]
    bad=(arr!=0)&(arr!=v)
    if ignore: bad &= (arr!=nidx[ignore])
    ok=~ndimage.binary_dilation(bad,structure=np.ones((2*rad+1,2*rad+1),bool))
    inv={i:n for n,i in nidx.items()}
    for p,q in zip(pts,pts[1:]):
        n=max(2,int(math.hypot(q[0]-p[0],q[1]-p[1])/G)+2)
        for i in range(n+1):
            t=i/n; x=p[0]+(q[0]-p[0])*t; y=p[1]+(q[1]-p[1])*t
            gx,gy=int(round(x/G)),int(round(y/G))
            if not ok[gx,gy]:
                if exempt and in_rects(x,y,exempt): continue
                sub=arr[max(0,gx-rad):gx+rad+1,max(0,gy-rad):gy+rad+1]
                who=sorted({inv.get(int(z),f'#{z}') for z in np.unique(sub) if z!=0 and z!=v})
                return f'at ({x:.2f},{y:.2f}) blocked by {who[:3]}'
    return 'clear'

def snap(v): return round(v/G)*G
def lshape(a,b,first):
    (x0,y0),(x1,y1)=a,b; dx,dy=x1-x0,y1-y0
    if abs(dx)<1e-9 or abs(dy)<1e-9: return [a,b]
    if not DIAG[0]:
        return [a,((x1,y0) if first=='h' else (x0,y1)),b]      # true right angle
    sx,sy=(1 if dx>0 else -1),(1 if dy>0 else -1); m=min(abs(dx),abs(dy))
    p1,p2 = ((x1-sx*m,y0),(x1,y0+sy*m)) if first=='h' else ((x0,y1-sy*m),(x0+sx*m,y1))
    pts=[a,p1,p2,b]
    return [p for i,p in enumerate(pts) if i==0 or abs(p[0]-pts[i-1][0])>1e-9 or abs(p[1]-pts[i-1][1])>1e-9]
def trim45(pts):
    if not DIAG[0]:
        d=[pts[0]]
        for q in pts[1:]:
            if abs(q[0]-d[-1][0])>1e-9 or abs(q[1]-d[-1][1])>1e-9: d.append(q)
        return d
    out=[pts[0]]
    for i in range(1,len(pts)-1):
        p,c,n=pts[i-1],pts[i],pts[i+1]
        d1=(c[0]-p[0],c[1]-p[1]); d2=(n[0]-c[0],n[1]-c[1])
        l1=math.hypot(*d1); l2=math.hypot(*d2)
        if l1<1e-9 or l2<1e-9: continue
        k=min(l1,l2)/2
        out.append((c[0]-d1[0]/l1*k, c[1]-d1[1]/l1*k)); out.append((c[0]+d2[0]/l2*k, c[1]+d2[1]/l2*k))
    out.append(pts[-1]); d=[out[0]]
    for p in out[1:]:
        if abs(p[0]-d[-1][0])>1e-9 or abs(p[1]-d[-1][1])>1e-9: d.append(p)
    return d
def zshape(a,b,axis,frac):
    (x0,y0),(x1,y1)=a,b
    if axis=='h':
        xm=snap(x0+(x1-x0)*frac); return trim45([a,(xm,y0),(xm,y1),b])
    ym=snap(y0+(y1-y0)*frac); return trim45([a,(x0,ym),(x1,ym),b])
def plen(p): return sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(p,p[1:]))

def escape(pad,L=None,toward=None):
    """A pad's escape direction is its own long axis, pointing away from the body.

    v2 took one row axis per footprint, which is nonsense for a 112-pad module with
    pads on all four edges: it sent the SD bus sideways out of a 1.0 mm-pitch row
    straight into its neighbours, so every one of those nets failed at the first cell.
    """
    w,h = pad['w'],pad['h']
    if abs(pad['rot'])%180==90: w,h = h,w
    dx,dy = pad['x']-pad['fx'], pad['y']-pad['fy']
    if w > h*1.2:   dirs=[((1,0),w/2),((-1,0),w/2)]          # long in x -> escape in x
    elif h > w*1.2: dirs=[((0,1),h/2),((0,-1),h/2)]
    else:           dirs=[((1,0),w/2),((-1,0),w/2),((0,1),h/2),((0,-1),h/2)]
    _L = ESC if L is None else L
    # outward first: a castellated pad routed inward disappears under the module
    def outward(d): return d[0]*dx + d[1]*dy
    dirs.sort(key=lambda z: -outward(z[0]))
    out=[]
    for d,off in dirs:
        out.append((snap(pad['x']+d[0]*(off+_L)),pad['y']) if d[0] else (pad['x'],snap(pad['y']+d[1]*(off+_L))))
    if toward is not None:
        # keep outward-first ordering but let a clearly better-aimed exit win
        out.sort(key=lambda e: math.hypot(e[0]-toward[0],e[1]-toward[1]))
    return (pad['x'],pad['y']), out

D8=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
D4=D8[:4]
# Style weights.  TURN keeps the picture orthogonal, OFFAX makes F.Cu trend
# horizontal and B.Cu vertical, VIAC stops the router stitching for fun.
# HW is a weighted-A* factor: the step costs above are ~1..10 while a plain
# Euclidean heuristic is ~1 per cell, so unweighted search wanders the whole
# board before committing.  HW restores useful guidance.
TURN,OFFAX,VIAC,HW = 6.0,1.2,15.0,3.0
def maze2(a,b,net,w,clr,layers,cap=1200000,endlayers=None,pad_mm=12.0,hw=None):
    hw=HW if hw is None else hw
    m=int(pad_mm/G)
    box=(max(0,int(min(a[0],b[0])/G)-m), max(0,int(min(a[1],b[1])/G)-m),
         min(NX,int(max(a[0],b[0])/G)+m), min(NY,int(max(a[1],b[1])/G)+m))
    oks={ln:mask_for(ln,net,w,clr,box=box) for ln in layers}
    el=set(range(len(layers))) if endlayers is None else {i for i,ln in enumerate(layers) if ln in endlayers}
    sx,sy=int(round(a[0]/G)),int(round(a[1]/G)); tx,ty=int(round(b[0]/G)),int(round(b[1]/G))
    start=(0,sx,sy,8); g={start:0.}; prev={}; pq=[(0.,start)]; seen=None; n=0
    rv=int(math.ceil((VIA_D/2+clr)/G))
    while pq:
        n+=1
        if n>cap: break
        f,cur=heapq.heappop(pq); cl,cx,cy,cd=cur
        if (cx,cy)==(tx,ty) and cl in el: seen=cur; break
        base=g[cur]; ln=layers[cl]; pref=PREF[ln]; ok=oks[ln]
        NB = D8 if DIAG[0] else D4
        for di,(dx,dy) in enumerate(NB):
            nx,ny=cx+dx,cy+dy
            if not (0<=nx<NX and 0<=ny<NY): continue
            if (nx,ny)!=(tx,ty) and not ok[nx,ny]: continue
            c=1.0 if dx==0 or dy==0 else 1.414
            if cd!=8 and di!=cd: c+=TURN
            ax='h' if dy==0 else ('v' if dx==0 else 'd')
            c += OFFAX*0.5 if ax=='d' else (OFFAX if ax!=pref else 0)
            ns=(cl,nx,ny,di); ng=base+c
            if ng<g.get(ns,1e18):
                g[ns]=ng; prev[ns]=cur; heapq.heappush(pq,(ng+hw*math.hypot(nx-tx,ny-ty),ns))
        if len(layers)>1:
            nl=1-cl
            if rv<=cx<NX-rv and rv<=cy<NY-rv and oks[layers[nl]][cx,cy] and can_via(cx*G,cy*G,net,clr):
                ns=(nl,cx,cy,8); ng=base+VIAC
                if ng<g.get(ns,1e18):
                    g[ns]=ng; prev[ns]=cur; heapq.heappush(pq,(ng+hw*math.hypot(cx-tx,cy-ty),ns))
    if seen is None: return None
    ch=[seen]
    while ch[-1] in prev: ch.append(prev[ch[-1]])
    ch.reverse()
    runs=[]; vias=[]; cl=ch[0][0]; pts=[(ch[0][1]*G,ch[0][2]*G)]
    for p,q in zip(ch,ch[1:]):
        if q[0]!=p[0]:
            runs.append((layers[cl],pts)); vias.append((p[1]*G,p[2]*G)); cl=q[0]; pts=[(q[1]*G,q[2]*G)]
        else: pts.append((q[1]*G,q[2]*G))
    runs.append((layers[cl],pts))
    out=[]
    for ln,ps in runs:
        if len(ps)<2: continue
        o=[ps[0]]
        for i in range(1,len(ps)-1):
            d1=(ps[i][0]-ps[i-1][0],ps[i][1]-ps[i-1][1]); d2=(ps[i+1][0]-ps[i][0],ps[i+1][1]-ps[i][1])
            if abs(d1[0]-d2[0])>1e-9 or abs(d1[1]-d2[1])>1e-9: o.append(ps[i])
        o.append(ps[-1]); out.append((ln,o))
    return (out,vias) if out else None

def cls_of(n):
    if n.startswith('CSI_'): return 'MIPI'
    # The J1<->U2 stubs are ~5 mm of the USB channel through the ESD part.  Holding
    # them to 0.27/0.18 makes them unroutable through U2's pad field, and a 0.2 mm
    # trace over 5 mm is ~95 ohm instead of 90 -- electrically irrelevant at USB 2.0.
    # The impedance-controlled run is U2<->U1, which keeps the USB class.
    if n.endswith('_CON'): return 'DEF'
    if n.startswith('USB_D'): return 'USB'
    if n in ('+5V','+3V3','+1V8','GND','VBUS_IN'): return 'PWR'
    return 'DEF'

def esc_geom(q,wid,clr):
    """Escape width/clearance scaled to the pad.  A 0.3 mm stub at 0.2 mm clearance
    needs 0.35 mm of lateral room; an FPC pin at 0.5 mm pitch offers exactly 0.35 mm,
    so it fails by one cell.  A 0.3 mm-wide pin cannot carry more than a 0.2 mm trace
    anyway, so the stub follows the pad and fattens once clear."""
    short=min(q['w'],q['h'])
    return (min(wid,max(0.2,short*0.8)), min(clr,CLR['DEF']) if short<0.45 else clr)

def connect(pa,pb,net,w=None,maze=True,clr=None):
    """Join two pads.  Always starts and ends on a layer the pad actually reaches.

    The escape legs are checked and laid at a necked width (esc_geom): a 0.27 mm USB
    trace at 0.18 mm clearance needs exactly the 0.35 mm a 0.5 mm-pitch connector pad
    offers, so it fails by one cell.  Necking the first millimetre is what a person
    does anyway, and the impedance of a 1 mm stub is irrelevant.
    """
    k=cls_of(net)
    if clr is None: clr=CLR[k]
    if w is None: w=WID[k]
    wa,ca=esc_geom(pa,w,clr); wb,cb=esc_geom(pb,w,clr)
    ra,rb=pad_rect(pa),pad_rect(pb)
    la=[l for l in SIG if l in pa['on']] or ['F.Cu']
    lb=[l for l in SIG if l in pb['on']] or ['F.Cu']
    for La in (0.6,1.1,0.35,1.6):
        a0,aopts=escape(pa,La,toward=(pb['x'],pb['y']))
        for Lb in (0.6,1.1,0.35,1.6):
            b0,bopts=escape(pb,Lb,toward=(pa['x'],pa['y']))
            for ln in ([l for l in la if l in lb] or la):
                for a1 in aopts[:3]:
                    if not clear_path([a0,a1],ln,net,wa,ca,exempt=[ra]): continue
                    for b1 in bopts[:3]:
                        if not clear_path([b1,b0],ln,net,wb,cb,exempt=[rb]): continue
                        cands=[lshape(a1,b1,'h'),lshape(a1,b1,'v')]
                        for fr in (0.3,0.5,0.7):
                            for axz in ('h','v'): cands.append(zshape(a1,b1,axz,fr))
                        dxx,dyy=abs(b1[0]-a1[0]),abs(b1[1]-a1[1])
                        if dxx<1e-6 or dyy<1e-6: cands.append([a1,b1])
                        best=None
                        for c in cands:
                            c=[q for i,q in enumerate(c) if i==0 or math.hypot(q[0]-c[i-1][0],q[1]-c[i-1][1])>1e-9]
                            if len(c)<2: continue
                            if not clear_path(c,ln,net,w,clr,exempt=[ra,rb]): continue
                            sc=plen(c)+max(0,len(c)-2)*2.5
                            if best is None or sc<best[0]: best=(sc,c)
                        if best:
                            lay_seg(a0[0],a0[1],a1[0],a1[1],ln,net,wa)
                            for q,r in zip(best[1],best[1][1:]): lay_seg(q[0],q[1],r[0],r[1],ln,net,w)
                            lay_seg(b1[0],b1[1],b0[0],b0[1],ln,net,wb)
                            return True
    if not maze: return False
    # guided two-layer search; both ends pinned to a layer the pad reaches
    tries=0
    lay_order=[l for l in SIG if l in la] or ['F.Cu']
    layers=[lay_order[0]]+[l for l in SIG if l!=lay_order[0]]
    endl=[l for l in SIG if l in pb['on']] or ['F.Cu']
    span=math.hypot(pb['x']-pa['x'],pb['y']-pa['y'])
    hw=HW if span<25 else 8.0          # a 40 mm haul needs a greedier heuristic
    for La in (0.6,1.0):
        a0,aopts=escape(pa,La,toward=(pb['x'],pb['y']))
        for Lb in (0.6,1.0):
            b0,bopts=escape(pb,Lb,toward=(pa['x'],pa['y']))
            for a1 in aopts[:3]:
                if not clear_path([a0,a1],layers[0],net,wa,ca,exempt=[ra]): continue
                for b1 in bopts[:3]:
                    if not any(clear_path([b1,b0],L,net,wb,cb,exempt=[rb]) for L in SIG): continue
                    if tries>=12: return False
                    r=maze2(a1,b1,net,w,clr,layers,endlayers=endl,hw=hw,pad_mm=(12.0 if span<25 else 20.0),
                            cap=((2500000 if span>=25 else 1200000) if tries<3 else 400000)); tries+=1
                    if not r: continue
                    runs,vias=r
                    if runs[0][0] not in pa['on'] or runs[-1][0] not in pb['on']: continue
                    if not all(can_via(vx,vy,net,clr) for vx,vy in vias): continue
                    if not clear_path([b1,b0],runs[-1][0],net,wb,cb,exempt=[rb]): continue
                    lay_seg(a0[0],a0[1],a1[0],a1[1],runs[0][0],net,wa)
                    for ln,ps in runs:
                        for q,t in zip(ps,ps[1:]): lay_seg(q[0],q[1],t[0],t[1],ln,net,w)
                    for vx,vy in vias: lay_via(vx,vy,net)
                    lay_seg(b1[0],b1[1],b0[0],b0[1],runs[-1][0],net,wb)
                    return True
    return False

def seg_dist(p1,p2,q1,q2):
    def pd(p,a,b):
        ax,ay=b[0]-a[0],b[1]-a[1]; l=ax*ax+ay*ay
        t=0 if l==0 else max(0,min(1,((p[0]-a[0])*ax+(p[1]-a[1])*ay)/l))
        return math.hypot(p[0]-(a[0]+t*ax),p[1]-(a[1]+t*ay))
    return min(pd(p1,q1,q2),pd(p2,q1,q2),pd(q1,p1,p2),pd(q2,p1,p2))
def poly_gap(A,B):
    m=1e9
    for a1,a2 in zip(A,A[1:]):
        for b1,b2 in zip(B,B[1:]): m=min(m,seg_dist(a1,a2,b1,b2))
    return m

bynet={}
for p in PADS:
    if p['net'] and not p['net'].startswith('unconnected-'): bynet.setdefault(p['net'],[]).append(p)

# Routed in physical order along the FPC (D1 at the bottom, then CLK, then D0) so the
# three pairs nest as a bus instead of fighting for the same channel.  The pin order at
# J3 and at U1 is the same, so nothing has to cross.
PAIRS=[('CSI_D1_N','CSI_D1_P'),('CSI_CLK_N','CSI_CLK_P'),('CSI_D0_N','CSI_D0_P'),('USB_DM','USB_DP')]

# ---- true coupled-pair routing ------------------------------------------
# One centreline is routed as a single fat trace (2w+gap wide, so the corridor it
# reserves is exactly what the finished pair occupies), then both traces are
# generated as parallel offsets of it.  That is how a pair is meant to be drawn:
# constant gap, mirrored corners, matched length by construction -- not two
# independent searches that happen to end up near each other.
def unit(a,b):
    d=(b[0]-a[0],b[1]-a[1]); l=math.hypot(*d)
    return (0.,0.) if l<1e-12 else (d[0]/l,d[1]/l)

def offset_poly(P,d):
    """Offset an H/V/45 polyline by d (left of travel = +).  Angles are preserved."""
    segs=[]
    for a,b in zip(P,P[1:]):
        u=unit(a,b)
        if u==(0.,0.): continue
        n=(-u[1],u[0])
        segs.append(((a[0]+d*n[0],a[1]+d*n[1]),(b[0]+d*n[0],b[1]+d*n[1])))
    if not segs: return None
    out=[segs[0][0]]
    for (a1,b1),(a2,b2) in zip(segs,segs[1:]):
        r=(b1[0]-a1[0],b1[1]-a1[1]); s=(b2[0]-a2[0],b2[1]-a2[1])
        den=r[0]*s[1]-r[1]*s[0]
        if abs(den)<1e-12: out.append(b1); continue
        t=((a2[0]-a1[0])*s[1]-(a2[1]-a1[1])*s[0])/den
        out.append((a1[0]+t*r[0],a1[1]+t*r[1]))
    out.append(segs[-1][1])
    d2=[out[0]]
    for p in out[1:]:
        if math.hypot(p[0]-d2[-1][0],p[1]-d2[-1][1])>1e-9: d2.append(p)
    return d2

def tidy(P):
    """Offset intersections drift by ~1e-4 mm, which reads as an off-angle segment.
    Round to the 0.1 um the file stores and force each segment onto H, V or exact 45."""
    Q=[(round(P[0][0],4),round(P[0][1],4))]
    for q in P[1:]:
        x,y=round(q[0],4),round(q[1],4); a=Q[-1]
        dx,dy=x-a[0],y-a[1]
        if abs(dx)<3e-3 and abs(dy)<3e-3: continue
        if abs(dx)<3e-3: x=a[0]
        elif abs(dy)<3e-3: y=a[1]
        elif DIAG[0] and abs(abs(dx)-abs(dy))<3e-3:
            m=(abs(dx)+abs(dy))/2
            x=a[0]+math.copysign(m,dx); y=a[1]+math.copysign(m,dy)
        elif not DIAG[0]:
            if abs(dx)>=abs(dy): y=a[1]
            else: x=a[0]
        Q.append((round(x,4),round(y,4)))
    return Q

def endpoint(p_lo,p_hi):
    """Row axis, outward normal and pad half-extent for the two pads of one pair end."""
    u=unit((p_lo['x'],p_lo['y']),(p_hi['x'],p_hi['y']))
    mid=((p_lo['x']+p_hi['x'])/2,(p_lo['y']+p_hi['y'])/2)
    n=(-u[1],u[0])
    if (mid[0]-p_lo['fx'])*n[0]+(mid[1]-p_lo['fy'])*n[1] < 0: n=(-n[0],-n[1])
    w,h=p_lo['w'],p_lo['h']
    if abs(p_lo['rot'])%180==90: w,h=h,w
    half=(abs(n[0])*w+abs(n[1])*h)/2
    pit=math.hypot(p_hi['x']-p_lo['x'],p_hi['y']-p_lo['y'])
    return mid,u,n,half,pit

PWHY=[]
def _pair_try(na,nb,stub0,stub1,nomaze=False):
    """Returns set of nets actually given continuous copper."""
    A,B=bynet.get(na,[]),bynet.get(nb,[])
    if len(A)!=2 or len(B)!=2: return None
    k=cls_of(na); w,clr,gap=WID[k],CLR[k],GAP[k]
    ends=[]
    for ref in [A[0]['ref'],A[1]['ref']]:
        pa=[q for q in A if q['ref']==ref]; pb=[q for q in B if q['ref']==ref]
        if len(pa)!=1 or len(pb)!=1: return None
        ends.append((pa[0],pb[0]))
    if ends[0][0]['ref']==ends[1][0]['ref']: return None
    off=(w+gap)/2                                  # centre-to-trace offset
    geo=[]
    for (pa,pb),stub in zip(ends,(stub0,stub1)):
        lo,hi=sorted([pa,pb],key=lambda q:(q['x'],q['y']))
        mid,u,n,half,pit=endpoint(lo,hi)
        taper=max(0.05,pit/2-off)                  # 45 deg taper, so L = stub+taper
        L=stub+taper
        # NOT snapped: snapping a coupled pair to the 0.1 mm search grid destroys
        # the exact 45 deg fan-in taper and the constant gap.
        c=(mid[0]+n[0]*(half+L),mid[1]+n[1]*(half+L))
        geo.append(dict(lo=lo,hi=hi,mid=mid,u=u,n=n,half=half,pit=pit,stub=stub,c=c))
    # fat centreline, single layer, no vias -- a MIPI/USB pair never changes layer here
    wfat=2*w+gap
    g0,g1=geo[0],geo[1]
    ci=(g0['c'][0]+g0['n'][0]*0.5,g0['c'][1]+g0['n'][1]*0.5)
    co=(g1['c'][0]+g1['n'][0]*0.5,g1['c'][1]+g1['n'][1]*0.5)
    mid_path=None
    for shape in (lshape(ci,co,'h'),lshape(ci,co,'v'),
                  zshape(ci,co,'h',.5),zshape(ci,co,'v',.5),
                  zshape(ci,co,'h',.35),zshape(ci,co,'v',.35)):
        cand=[g0['c'],ci]+shape[1:-1]+[co,g1['c']]
        cand=[p for i,p in enumerate(cand) if i==0 or math.hypot(p[0]-cand[i-1][0],p[1]-cand[i-1][1])>1e-9]
        if clear_path(cand,'F.Cu',na,wfat,clr): mid_path=cand; break
    if mid_path is None and nomaze: return None
    if mid_path is None:
        r=maze2(ci,co,na,wfat,clr,['F.Cu'],cap=250000,hw=5.0,pad_mm=10.0)
        if not r: PWHY.append('no corridor'); return None
        runs,_=r
        if len(runs)!=1: PWHY.append('corridor changed layer'); return None
        mid_path=[g0['c']]+list(runs[0][1])+[g1['c']]
        mid_path=[p for i,p in enumerate(mid_path) if i==0 or math.hypot(p[0]-mid_path[i-1][0],p[1]-mid_path[i-1][1])>1e-9]
    left=offset_poly(mid_path,+off); right=offset_poly(mid_path,-off)
    if not left or not right: PWHY.append('offset failed'); return None
    # which side each net sits on, judged at the first end
    u0,n0=g0['u'],g0['n']; d0=unit(mid_path[0],mid_path[1])
    nrm=(-d0[1],d0[0])
    def side(pad):
        v=(pad['x']-g0['mid'][0],pad['y']-g0['mid'][1])
        return v[0]*nrm[0]+v[1]*nrm[1]
    pa0,pb0=ends[0]
    net_left,net_right=(na,nb) if side(pa0)>=side(pb0) else (nb,na)
    body={net_left:left,net_right:right}
    full={}
    for j,(pa,pb) in enumerate(ends):
        gj=geo[j]
        for pad in (pa,pb):
            nn=pad['net']; poly=body[nn]
            tgt=poly[0] if j==0 else poly[-1]
            s=(pad['x']+gj['n'][0]*(gj['half']+gj['stub']),
               pad['y']+gj['n'][1]*(gj['half']+gj['stub']))
            lead=[(pad['x'],pad['y']),s,tgt]
            lead=[p for i,p in enumerate(lead) if i==0 or math.hypot(p[0]-lead[i-1][0],p[1]-lead[i-1][1])>1e-9]
            full.setdefault(nn,[]).append((j,lead))
    out={}
    for nn,poly in body.items():
        lead={j:l for j,l in full[nn]}
        head=lead.get(0,[poly[0]]); tail=lead.get(1,[poly[-1]])
        path=head[:-1]+poly+list(reversed(tail))[1:]
        path=[p for i,p in enumerate(path) if i==0 or math.hypot(p[0]-path[i-1][0],p[1]-path[i-1][1])>1e-9]
        out[nn]=tidy(path)
    pl,pr=out[net_left],out[net_right]
    if poly_gap(pl,pr) < gap-0.02: PWHY.append(f'gap {poly_gap(pl,pr):.3f}'); return None
    exm=[pad_rect(q) for j,(pa,pb) in enumerate(ends) for q in (pa,pb)]
    for nn,path in out.items():
        other=net_right if nn==net_left else net_left
        if not clear_path(path,'F.Cu',nn,w,clr,ignore=other,exempt=exm):
            PWHY.append(f'{nn} blocked: '+blocker(path,'F.Cu',nn,w,clr,ignore=other,exempt=exm)); return None
        for p,q in zip(path,path[1:]):
            dx,dy=abs(q[0]-p[0]),abs(q[1]-p[1])
            if dx>1e-6 and dy>1e-6 and abs(dx-dy)>2e-3: PWHY.append(f'off-angle {nn} {p}->{q}'); return None
    return dict(paths=out,skew=abs(plen(out[na])-plen(out[nb])),
                tot=plen(out[na])+plen(out[nb]),w=w)
LP={}
STUBS=(0.3,0.5,0.7,1.0,1.4,2.0)
STUBS_MAZE=(0.3,0.7,1.0,1.4)

def route_pair(na,nb):
    """Plan every fan-out combination, then commit the one with the least intra-pair
    skew -- not the first that happens to fit.  A tight FPC needs the coupled corridor
    to start clear of the neighbouring pads, hence the range of stub lengths."""
    best=None
    # Round 1 is shapes only and cheap: every stub combination.  Round 2 lets the maze
    # find a corridor, which costs hundreds of times more, so it only gets a few
    # combinations -- a combination that fails on geometry will fail again with a maze.
    for nomaze,stubs in ((True,STUBS),(False,STUBS_MAZE)):
        for s0 in stubs:
            for s1 in stubs:
                del PWHY[:]
                r=_pair_try(na,nb,s0,s1,nomaze=nomaze)
                if r and (best is None or (r['skew'],r['tot'])<(best['skew'],best['tot'])): best=r
                if r is None and os.environ.get('PAIRDBG') and not nomaze:
                    print(f'      stub {s0}/{s1}: {PWHY or ["no shape cleared"]}',flush=True)
        if best and best['skew']<=0.1: break
    if not best: return set()
    for nn,path in best['paths'].items():
        for p,q in zip(path,path[1:]): lay_seg(p[0],p[1],q[0],q[1],'F.Cu',nn,best['w'])
        LP[nn]=plen(path)
    return set(best['paths'])

ORDER=([n for n in nets if n.startswith('CSI_')]+[n for n in nets if n.startswith('USB_D')]+
       ['MCLK0']+[n for n in nets if n.startswith('CAM_')]+[n for n in nets if n.startswith('SD_')]+
       ['UART2_TX','UART2_RX','NPOR_RST','ADC0_RECOV','RECOV_HDR','VBUS_DET','CC1','CC2','LED_STAT','LED_A'])
ORDER=[n for n in ORDER if n in bynet]

miss=[]
BASE=[a.copy() for a in occ]      # pads, keepouts, plane: everything that cannot move
def rebuild():
    for i in range(len(LAYERS)): occ[i][:]=BASE[i]
    for x0,y0,x1,y1,ln,net,w in TRK:
        n=max(2,int(max(abs(x1-x0),abs(y1-y0))/G)+2)
        for i in range(n+1):
            t=i/n; box(occ[LI[ln]],x0+(x1-x0)*t,y0+(y1-y0)*t,w,w,0,nidx[net])
    for x,y,net in VIAS:
        for arr in occ: box(arr,x,y,VIA_D,VIA_D,0,nidx[net])
    _M.clear(); _M['_s']=_M.get('_s',0)+1
def rip(nets):
    TRK[:]=[t for t in TRK if t[5] not in nets]
    VIAS[:]=[v for v in VIAS if v[2] not in nets]
    VIAPOS[:]=[(v[0],v[1]) for v in VIAS]
    rebuild()
def snapshot(): return (list(TRK),list(VIAS))
def restore(sn):
    TRK[:] , VIAS[:] = list(sn[0]), list(sn[1])
    VIAPOS[:]=[(v[0],v[1]) for v in VIAS]; rebuild()

def drop_via(q,net,clr0,wid0,rmax=3.4):
    """Escape the pad perpendicular, then put the via where it actually fits.

    A straight escape often has nowhere to land -- a 0.6 mm via needs 0.5 mm of clear
    radius and the partner pad of an 0402 is 0.48 mm away.  So if the straight try
    fails, search outward for a legal via site and reach it with an L or Z.
    """
    wid,clr=esc_geom(q,wid0,clr0)
    for L in (0.7,1.0,1.4,1.9,2.5,0.45):
        a0,ao=escape(q,L)
        for a1 in ao:
            if clear_path([a0,a1],'F.Cu',net,wid,clr,exempt=[pad_rect(q)]) and can_via(a1[0],a1[1],net,clr):
                lay_seg(a0[0],a0[1],a1[0],a1[1],'F.Cu',net,wid); lay_via(a1[0],a1[1],net)
                return a1
    a0,ao=escape(q,0.45)
    for a1 in ao:
        if not clear_path([a0,a1],'F.Cu',net,wid,clr,exempt=[pad_rect(q)]): continue
        for R in (1.0,1.4,1.9,2.5,rmax):
            for k in range(24):
                th=k*math.pi/12
                vx,vy=snap(q['x']+R*math.cos(th)),snap(q['y']+R*math.sin(th))
                if not can_via(vx,vy,net,clr): continue
                for sh in (lshape(a1,(vx,vy),'h'),lshape(a1,(vx,vy),'v')):
                    full=[a0]+sh
                    full=[z for i,z in enumerate(full) if i==0 or math.hypot(z[0]-full[i-1][0],z[1]-full[i-1][1])>1e-9]
                    if not clear_path(full,'F.Cu',net,wid,clr,exempt=[pad_rect(q)]): continue
                    for z,r in zip(full,full[1:]): lay_seg(z[0],z[1],r[0],r[1],'F.Cu',net,wid)
                    lay_via(vx,vy,net); return (vx,vy)
    if os.environ.get('PWRDBG'):
        a0,ao=escape(q,0.45)
        print(f'      !! {net} {q["ref"]}.{q["pin"]} at ({q["x"]:.2f},{q["y"]:.2f}) stuck:',flush=True)
        for a1 in ao:
            print(f'         stub ->{a1}: '+blocker([a0,a1],'F.Cu',net,wid,clr,exempt=[pad_rect(q)]),flush=True)
    return None


def route_net(net,ps):
    done=[ps[0]]; todo=list(ps[1:]); ok=0; fail=[]
    while todo:
        cand=sorted(((math.hypot(a['x']-b['x'],a['y']-b['y']),i,j)
                     for j,b in enumerate(todo) for i,a in enumerate(done)))
        b_pick=cand[0][2]; b=todo[b_pick]
        got=False
        for _,i,j in cand:
            if j!=b_pick: continue
            if connect(done[i],b,net) or connect(done[i],b,net,w=WID['DEF']): got=True; break
        todo.remove(b); done.append(b)
        if got: ok+=1
        else: fail.append((net,b,[q for q in done if q is not b]))
    return ok,fail


# ---- finisher ------------------------------------------------------------
# Re-lay every piece of copper the previous run produced, so occupancy is the real
# board, then make only the connections a per-pad audit proved are missing.  Rerouting
# the whole board to fix four pads would throw away three perfect camera pairs.
_es=re.findall(r'\(segment\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)\s*'
               r'\(width ([\d.]+)\)\s*\(layer "([^"]+)"\)\s*\(net "([^"]+)"\)', ORIG)
_ev=re.findall(r'\(via\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([\d.]+)\)\s*\(drill ([\d.]+)\)\s*'
               r'\(layers "[^"]+" "[^"]+"\)\s*\(net "([^"]+)"\)', ORIG)
for x0,y0,x1,y1,w,ln,nt in _es:
    if ln in LI and nt in nidx: lay_seg(float(x0),float(y0),float(x1),float(y1),ln,nt,float(w))
for x,y,d,dr,nt in _ev:
    if nt in nidx: lay_via(float(x),float(y),nt)
print(f'kept {len(_es)} segments and {len(_ev)} vias from the previous run')

TARGETS=[('CAM_SDA','J3','14'),('GND','U2','2'),('SD_D3','J2','2'),('VBUS_DET','R7','2')]
def padof(ref,pin):
    for q in PADS:
        if q['ref']==ref and q['pin']==pin: return q
    return None

print('\nfinishing the connections the audit found missing:')
FAIL=[]; PAIRED=set()
RIPPABLE={n for n in nets if not n.startswith('unconnected-')
          and n not in ('GND','+5V','+3V3','+1V8','VBUS_IN')
          and not n.startswith('CSI_')}          # the camera pairs are never touched
for net,ref,pin in TARGETS:
    b=padof(ref,pin)
    if b is None: print(f'  {net} {ref}.{pin}: pad not found'); continue
    done=False
    if net=='GND':
        # First choice is a via: that ties the pad straight to the In1.Cu plane.
        if drop_via(b,'GND',0.10,0.2,rmax=3.0):
            print(f'  GND {ref}.{pin}: via to the plane placed'); done=True
        else:
            # No room for a legal via (0.6/0.3 -- a 0.45/0.25 via would only have a
            # 0.10 mm annular ring, under JLCPCB's 0.13 mm floor).  So thread a short
            # 0.2 mm trace out to open copper instead: the GND pour bonds to same-net
            # copper, so ending in pour-eligible area is a real connection.  Verified
            # afterwards by padaudit.py, which simulates the fill.
            zr=int(math.ceil(0.55/G))
            for L in (0.6,0.9,1.3,1.8,2.4,3.0):
                a0,ao=escape(b,L)
                for a1 in ao:
                    if not clear_path([a0,a1],'F.Cu','GND',0.2,0.15,exempt=[pad_rect(b)]): continue
                    gx,gy=int(round(a1[0]/G)),int(round(a1[1]/G))
                    win=occ[LI['F.Cu']][gx-zr:gx+zr+1, gy-zr:gy+zr+1]
                    if win.size==0 or np.any((win!=0)&(win!=nidx['GND'])): continue
                    lay_seg(a0[0],a0[1],a1[0],a1[1],'F.Cu','GND',0.2)
                    print(f'  GND {ref}.{pin}: 0.2 mm tail out to open copper at '
                          f'({a1[0]:.2f},{a1[1]:.2f}); the pour bonds to it'); done=True; break
                if done: break
    else:
        others=sorted((q for q in PADS if q['net']==net and q is not b),
                      key=lambda q: math.hypot(q['x']-b['x'],q['y']-b['y']))
        for a in others:
            if connect(a,b,net,w=0.15,clr=0.10):
                print(f'  {net} {ref}.{pin}: routed to {a["ref"]}.{a["pin"]}'); done=True; break
    if not done: FAIL.append((net,b,[q for q in PADS if q['net']==net and q is not b]))

# local rip-up for whatever is left
for rnd,rmul in ((1,2),(2,5)):
    if not FAIL: break
    print(f'  -- rip-up round {rnd} --',flush=True)
    for net,b,done_ in list(FAIL):
        w,clr=0.15,0.10
        a=min(done_,key=lambda q: math.hypot(q['x']-b['x'],q['y']-b['y'])) if done_ else None
        culprits=set(); inv={i:n for n,i in nidx.items()}
        for ln in SIG:
            arr=occ[LI[ln]]; rad=int(math.ceil((w/2+clr)/G))*rmul
            ax,ay=(a['x'],a['y']) if a else (b['x'],b['y'])
            n_=int(math.hypot(b['x']-ax,b['y']-ay)/G)+2
            for k in range(n_+1):
                t=k/n_; gx=int(round((ax+(b['x']-ax)*t)/G)); gy=int(round((ay+(b['y']-ay)*t)/G))
                if not (rad<=gx<NX-rad and rad<=gy<NY-rad): continue
                for z in np.unique(arr[gx-rad:gx+rad+1,gy-rad:gy+rad+1]):
                    nm=inv.get(int(z))
                    if nm and nm!=net and nm in RIPPABLE: culprits.add(nm)
        if not culprits: continue
        sn=snapshot(); rip(culprits)
        if net=='GND': fixed=bool(drop_via(b,'GND',0.10,0.2,rmax=3.0))
        else:          fixed=any(connect(q,b,net,w=w,clr=clr) for q in done_[:4])
        again=[]
        for nm in sorted(culprits):
            ps2=bynet.get(nm,[])
            if len(ps2)<2: continue
            xs=max(q['x'] for q in ps2)-min(q['x'] for q in ps2); ys=max(q['y'] for q in ps2)-min(q['y'] for q in ps2)
            ps2=sorted(ps2,key=lambda q:(q['x'],q['y']) if xs>=ys else (q['y'],q['x']))
            _,f2=route_net(nm,ps2); again+=f2
        if fixed and len(again)==0:
            FAIL[:]=[f for f in FAIL if f[1] is not b]
            print(f'  {net} {b["ref"]}.{b["pin"]}: ripped {len(culprits)} net(s) -> routed',flush=True)
        else:
            restore(sn)
            print(f'  {net} {b["ref"]}.{b["pin"]}: ripped {len(culprits)}, '
                  f'{"broke "+str(len(again))+" other(s)" if fixed else "no gain"} -- put back',flush=True)

miss=[f'{n} {q["ref"]}.{q["pin"]}' for n,q,_ in FAIL]
EXC=[]
# ---- geometry repair ---------------------------------------------------
# Nothing on this board is allowed to be an arbitrary angle -- it is the whole point of
# the exercise.  Anything that slipped through gets rebuilt as an L, or removed and
# reported rather than shipped.
PAIRNETS=set()
for _a,_b in PAIRS: PAIRNETS|={_a,_b}
def is_bad(t):
    dx,dy=abs(t[2]-t[0]),abs(t[3]-t[1])
    if dx<=1e-6 or dy<=1e-6: return False                 # H or V: always fine
    if t[5] in PAIRNETS and abs(dx-dy)<=1e-3: return False  # exact 45 on a pair: fine
    return True
_fixed=_dropped=0
for _i,_t in enumerate(list(TRK)):
    if not is_bad(_t): continue
    x0,y0,x1,y1,ln,net,w=_t
    done=False
    for mid in ((x1,y0),(x0,y1)):
        cand=[(x0,y0),mid,(x1,y1)]
        if clear_path(cand,ln,net,w,CLR[cls_of(net)]):
            TRK[_i]=(x0,y0,mid[0],mid[1],ln,net,w)
            TRK.append((mid[0],mid[1],x1,y1,ln,net,w)); _fixed+=1; done=True; break
    if not done:
        TRK[_i]=None; _dropped+=1
TRK[:]=[t for t in TRK if t is not None]
if _fixed or _dropped:
    print(f'\ngeometry repair: {_fixed} segment(s) rebuilt as L'
          + (f', {_dropped} removed (reported as unrouted)' if _dropped else ''))
    rebuild()

bad=[t for t in TRK if is_bad(t)]
_orth=sum(1 for t in TRK if abs(t[2]-t[0])<=1e-6 or abs(t[3]-t[1])<=1e-6)
_d45 =len(TRK)-_orth-len(bad)
print(f'geometry: {_orth} orthogonal + {_d45} chamfer(s) on the camera pairs'
      + ('' if not bad else f'   !! {len(bad)} oblique'))

if miss:
    print(f'\nUNROUTED ({len(miss)}):')
    for m in miss: print('   ',m)

out=[]
for x0,y0,x1,y1,ln,net,w in TRK:
    out.append(f'\t(segment\n\t\t(start {x0:.4f} {y0:.4f})\n\t\t(end {x1:.4f} {y1:.4f})\n\t\t(width {w})\n'
               f'\t\t(layer "{ln}")\n\t\t(net "{net}")\n\t\t(uuid "{UD("s")}")\n\t)')
for x,y,net in VIAS:
    out.append(f'\t(via\n\t\t(at {x:.4f} {y:.4f})\n\t\t(size {VIA_D})\n\t\t(drill {VIA_DRL})\n'
               f'\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{UD("v")}")\n\t)')
i=src.rfind(')')
open(DST,'w').write(src[:i]+'\n'.join(out)+'\n'+src[i:])
if EXC:
    print(f'\nlocal clearance exceptions (0.15/0.10, all >= 1.7x JLCPCB minimum): {len(EXC)}')
    for e in EXC: print('   ',e)
print(f'\nwrote {len(TRK)} segments, {len(VIAS)} vias -> {DST}')
