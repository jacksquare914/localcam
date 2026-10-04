"""LocalCam-1 continuity + clearance test — independent of KiCad's own DRC.

  python3 continuity.py            # test LocalCam1.kicad_pcb in this folder
  python3 continuity.py board.kicad_pcb

Rasterises all copper (pads, tracks, vias, filled zones) per layer at 0.02 mm,
joins layers through vias and through-hole pads, then for each net counts how many
electrically separate islands its copper forms.

  1 island  = net is fully continuous          OK
  N islands = net is in N disconnected pieces  -> N-1 connections still missing

Also reports any two different nets closer than the clearance (a short waiting to happen).

NOTE: zones only count if KiCad has filled them — press B in the PCB editor and save
first, otherwise pours are ignored and ground will look disconnected.
"""
import sys, os, math
import numpy as np
from scipy import ndimage
sys.path.insert(0, '/home/claude')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sexp import parse, find, val, unq

G      = 0.05 if '--fine' not in sys.argv else 0.02   # mm per cell
CLEAR  = 0.15                                   # mm, min clearance to flag
LAY    = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
LI     = {n: i for i, n in enumerate(LAY)}
ARGS   = [a for a in sys.argv[1:] if not a.startswith('--')]
PATH   = ARGS[0] if ARGS else os.path.join(HERE, 'LocalCam1.kicad_pcb')
DOCLR  = '--clearance' in sys.argv

b = parse(open(PATH).read())
W = H = 0
for l in find(b, 'gr_line'):
    for k in ('start', 'end'):
        a = find(l, k)[0]; W = max(W, float(a[1])); H = max(H, float(a[2]))
for l in find(b, 'gr_arc'):
    for k in ('start', 'mid', 'end'):
        for a in find(l, k): W = max(W, float(a[1])); H = max(H, float(a[2]))
NX, NY = int(W / G) + 2, int(H / G) + 2

own  = [np.zeros((NX, NY), np.int32) for _ in LAY]     # net id per cell per layer
vmap = [np.zeros((NX, NY), bool) for _ in LAY]         # cell is joined to the layer below/above

def xf(X, Y, r, x, y):
    t = math.radians(r)
    return (X + x*math.cos(t) + y*math.sin(t), Y - x*math.sin(t) + y*math.cos(t))

def rect(arr, cx, cy, w, h, rot, v):
    if abs(rot) % 180 == 90: w, h = h, w
    arr[max(0, int((cx-w/2)/G)):int((cx+w/2)/G)+1,
        max(0, int((cy-h/2)/G)):int((cy+h/2)/G)+1] = v

def disc(arr, cx, cy, d, v):
    r = d/2; x0, x1 = max(0,int((cx-r)/G)), min(NX-1,int((cx+r)/G))
    y0, y1 = max(0,int((cy-r)/G)), min(NY-1,int((cy+r)/G))
    ys, xs = np.ogrid[y0:y1+1, x0:x1+1]
    m = ((xs*G-cx)**2 + (ys*G-cy)**2) <= r*r
    sub = arr[x0:x1+1, y0:y1+1]
    sub[m.T] = v

# ---- collect nets -------------------------------------------------------
import re as _re
_all = sorted(set(_re.findall(r'\(net "([^"]*)"\)', open(PATH).read())))
_idx = {nm: i+1 for i, nm in enumerate(_all)}
netname = {i+1: nm for i, nm in enumerate(_all)}
def nid(node):
    x = find(node, 'net')
    if not x: return 0
    t = x[0][1]
    return _idx.get(unq(t), 0) if t.startswith('"') else int(t)

# ---- pads ---------------------------------------------------------------
npad = 0; padlist = []
for fp in find(b, 'footprint'):
    at = find(fp, 'at')[0]; X, Y = float(at[1]), float(at[2])
    r = float(at[3]) if len(at) > 3 else 0.0
    ref = [unq(p[2]) for p in find(fp, 'property') if unq(p[1]) == 'Reference'][0]
    for p in find(fp, 'pad'):
        a = find(p, 'at')[0]; s = find(p, 'size')[0]
        pr = float(a[3]) if len(a) > 3 else 0.0
        px, py = xf(X, Y, r, float(a[1]), float(a[2]))
        v = nid(p)
        if v == 0: continue
        thru = p[2] in ('thru_hole', 'np_thru_hole')
        lays = [unq(z) for z in find(p, 'layers')[0][1:]]
        tgt = LAY if thru else [z for z in LAY if z in lays or '*.Cu' in lays]
        for ln in tgt:
            rect(own[LI[ln]], px, py, float(s[1]), float(s[2]), pr, v)
            if thru: vmap[LI[ln]][max(0,int((px-0.1)/G)):int((px+0.1)/G)+1,
                                  max(0,int((py-0.1)/G)):int((py+0.1)/G)+1] = True
        padlist.append((ref, unq(p[1]), v)); npad += 1

# ---- tracks -------------------------------------------------------------
nseg = 0
for s in find(b, 'segment'):
    ln = unq(val(s, 'layer'))
    if ln not in LI: continue
    a = find(s, 'start')[0]; c = find(s, 'end')[0]; w = float(val(s, 'width')); v = nid(s)
    x0, y0, x1, y1 = float(a[1]), float(a[2]), float(c[1]), float(c[2])
    n = int(max(abs(x1-x0), abs(y1-y0))/G) + 2
    for i in range(n+1):
        t = i/n; disc(own[LI[ln]], x0+(x1-x0)*t, y0+(y1-y0)*t, w, v)
    nseg += 1

# ---- vias ---------------------------------------------------------------
nvia = 0
for vn in find(b, 'via'):
    a = find(vn, 'at')[0]; d = float(val(vn, 'size')); v = nid(vn)
    x, y = float(a[1]), float(a[2])
    lays = [unq(z) for z in find(vn, 'layers')[0][1:]] if find(vn, 'layers') else LAY
    span = LAY if len(lays) < 2 else LAY[LI[lays[0]]:LI[lays[-1]]+1] if lays[0] in LI and lays[-1] in LI else LAY
    for ln in span:
        disc(own[LI[ln]], x, y, d, v)
        vmap[LI[ln]][max(0,int((x-d/4)/G)):int((x+d/4)/G)+1,
                     max(0,int((y-d/4)/G)):int((y+d/4)/G)+1] = True
    nvia += 1

# ---- filled zones -------------------------------------------------------
nzone = 0; unfilled = []
from matplotlib.path import Path as MPath
for z in find(b, 'zone'):
    v = nid(z); zl = unq(val(z, 'layer') or '')
    fills = find(z, 'filled_polygon')
    if not fills:
        unfilled.append((netname.get(v, '?'), zl or 'multi')); continue
    for f in fills:
        ln = unq(val(f, 'layer') or zl)
        if ln not in LI: continue
        pts = [(float(a[1]), float(a[2])) for a in find(find(f, 'pts')[0], 'xy')]
        if len(pts) < 3: continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        x0, x1 = max(0,int(min(xs)/G)), min(NX-1,int(max(xs)/G))
        y0, y1 = max(0,int(min(ys)/G)), min(NY-1,int(max(ys)/G))
        if x1 <= x0 or y1 <= y0: continue
        gx, gy = np.meshgrid(np.arange(x0,x1+1)*G, np.arange(y0,y1+1)*G, indexing='ij')
        inside = MPath(pts).contains_points(np.column_stack([gx.ravel(), gy.ravel()]))
        sub = own[LI[ln]][x0:x1+1, y0:y1+1]
        sub[inside.reshape(sub.shape) & (sub == 0)] = v
        nzone += 1

# ---- continuity: label islands per net, joined across layers by vias ----
print(f'board {W:.0f} x {H:.0f} mm   pads {npad}  tracks {nseg}  vias {nvia}  filled zone polys {nzone}')
if unfilled:
    print(f'!! {len(unfilled)} zone(s) NOT FILLED - press B in KiCad and save, or pours are ignored:')
    for n, l in unfilled[:8]: print(f'     {n} on {l}')
print()

nets = sorted({v for v in netname if v > 0 and not netname[v].startswith('unconnected-')},
              key=lambda v: netname[v])
struct = np.ones((3,3), bool)
bad = []
print(f'{"net":14} {"pads":>5} {"islands":>8}   status')
print('-'*52)
for v in nets:
    pads_here = [p for p in padlist if p[2] == v]
    if not pads_here: continue
    # label each layer, then merge labels that share a via cell
    labs = []; offset = 0
    for li in range(len(LAY)):
        lab, n = ndimage.label(own[li] == v, structure=struct)
        lab[lab > 0] += offset; offset += n; labs.append(lab)
    parent = list(range(offset+1))
    def fr(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def un(a, b):
        a, b = fr(a), fr(b)
        if a != b: parent[max(a,b)] = min(a,b)
    for li in range(len(LAY)-1):
        for lj in range(li+1, len(LAY)):
            both = (labs[li] > 0) & (labs[lj] > 0) & vmap[li] & vmap[lj]
            if both.any():
                for a, c in set(zip(labs[li][both].tolist(), labs[lj][both].tolist())): un(a, c)
    groups = set()
    for li in range(len(LAY)):
        vals = np.unique(labs[li]); groups |= {fr(int(x)) for x in vals if x > 0}
    n_isl = len(groups)
    ok = 'OK' if n_isl == 1 else f'MISSING {n_isl-1} connection(s)'
    if n_isl != 1: bad.append((netname[v], len(pads_here), n_isl))
    print(f'{netname[v]:14} {len(pads_here):5} {n_isl:8}   {ok}')

print()
print(f'CONTINUITY: {len(nets)-len(bad)}/{len(nets)} nets fully connected'
      + ('' if not bad else f'   -- {sum(n-1 for _,_,n in bad)} connections still missing'))

# ---- clearance (opt-in: --clearance) -----------------------------------
print()
if not DOCLR:
    print('CLEARANCE: skipped (run with --clearance to test, slower)')
else:
    # Euclidean distance transform, not a square dilation: a square kernel of radius
    # 0.15 mm reaches 0.21 mm diagonally, so it reported every legal 0.18 mm diff-pair
    # gap as a violation.  This measures the true centre-to-centre distance and
    # subtracts nothing, so the number printed is the real copper-to-copper gap.
    hits = []; worst = []
    for li, arr in enumerate(own):
        ids = [x for x in np.unique(arr) if x > 0]
        for v in ids:
            mine = (arr == v)
            others = (arr != 0) & ~mine
            if not others.any() or not mine.any(): continue
            d = ndimage.distance_transform_edt(~others, sampling=G)
            dm = d[mine]
            mn = float(dm.min())
            worst.append((mn, LAY[li], netname.get(v, '?')))
            if mn < CLEAR:
                j = np.argwhere(mine & (d <= mn + 1e-9))[0]
                near = sorted({netname.get(int(x), '?')
                               for x in np.unique(arr[max(0,j[0]-4):j[0]+5, max(0,j[1]-4):j[1]+5])
                               if x > 0 and x != v})
                hits.append((LAY[li], netname.get(v, '?'), near[:3],
                             (round(j[0]*G, 2), round(j[1]*G, 2)), mn))
    worst.sort()
    print('tightest gaps (copper edge to copper edge, true distance):')
    for mn, l, n in worst[:6]:
        print(f'   {mn:6.3f} mm   {l:7} {n}')
    print()
    if hits:
        print(f'CLEARANCE: {len(hits)} net(s) closer than {CLEAR} mm to foreign copper')
        for l, n, o, loc, mn in hits[:15]:
            print(f'   {mn:5.3f} mm  {l:7} {n:14} vs {",".join(o):22} at {loc}')
    else:
        print(f'CLEARANCE: nothing closer than {CLEAR} mm  -- clean')
