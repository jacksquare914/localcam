"""Per-pad connectivity audit, with the ground pour simulated.

  python3 padaudit.py routed.kicad_pcb

continuity.py counts islands per net, which tells you a net is broken but not WHICH pad
is orphaned.  This walks every pad that carries a real net and answers one question:
is this pad in the same electrical island as the rest of its net?

It also simulates the zone fill, because the delivered file deliberately ships with
unfilled pours (KiCad recomputes them).  Without that simulation every GND pad looks
disconnected and the answer is useless.  The pour is grown from existing GND copper
across all cells that are at least `clearance` away from any foreign net, which is what
the zone filler does, minus thermal reliefs and min-width pruning.
"""
import sys, os, math
import numpy as np
from scipy import ndimage
sys.path.insert(0, '/home/claude')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sexp import parse, find, val, unq

G     = 0.05
LAY   = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
LI    = {n: i for i, n in enumerate(LAY)}
POUR  = {'F.Cu', 'In1.Cu', 'B.Cu'}      # layers carrying a GND pour (placement.ZONES)
ZCLR  = 0.2                              # zone clearance to foreign copper
PATH  = sys.argv[1] if len(sys.argv) > 1 else 'LocalCam1.kicad_pcb'

txt = open(PATH).read(); b = parse(txt)
W = H = 0
for l in find(b, 'gr_line'):
    for k in ('start', 'end'):
        a = find(l, k)[0]; W = max(W, float(a[1])); H = max(H, float(a[2]))
for l in find(b, 'gr_arc'):
    for k in ('start', 'mid', 'end'):
        for a in find(l, k): W = max(W, float(a[1])); H = max(H, float(a[2]))
NX, NY = int(W/G)+2, int(H/G)+2

import re
names = sorted(set(re.findall(r'\(net "([^"]*)"\)', txt)))
nidx  = {n: i+1 for i, n in enumerate(names)}
nname = {i+1: n for i, n in enumerate(names)}

own  = [np.zeros((NX, NY), np.int32) for _ in LAY]
vmap = [np.zeros((NX, NY), bool) for _ in LAY]

def xf(X, Y, r, x, y):
    t = math.radians(r)
    return (X + x*math.cos(t) + y*math.sin(t), Y - x*math.sin(t) + y*math.cos(t))
def box(arr, cx, cy, w, h, rot, v):
    if abs(rot) % 180 == 90: w, h = h, w
    arr[max(0,int((cx-w/2)/G)):int((cx+w/2)/G)+1, max(0,int((cy-h/2)/G)):int((cy+h/2)/G)+1] = v
def disc(arr, cx, cy, d, v):
    r = d/2
    x0, x1 = max(0,int((cx-r)/G)), min(NX-1,int((cx+r)/G))
    y0, y1 = max(0,int((cy-r)/G)), min(NY-1,int((cy+r)/G))
    if x1 < x0 or y1 < y0: return
    ys, xs = np.ogrid[y0:y1+1, x0:x1+1]
    m = ((xs*G-cx)**2 + (ys*G-cy)**2) <= r*r
    sub = arr[x0:x1+1, y0:y1+1]; sub[m.T] = v

def nid(node):
    x = find(node, 'net')
    if not x: return 0
    t = x[0][1]
    return nidx.get(unq(t), 0) if t.startswith('"') else int(t)

# ---- pads ---------------------------------------------------------------
PADS = []
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
        on = LAY if thru or '*.Cu' in lays else [z for z in LAY if z in lays]
        for ln in on or ['F.Cu']:
            box(own[LI[ln]], px, py, float(s[1]), float(s[2]), pr, v)
            if thru:
                vmap[LI[ln]][max(0,int((px-0.1)/G)):int((px+0.1)/G)+1,
                             max(0,int((py-0.1)/G)):int((py+0.1)/G)+1] = True
        PADS.append(dict(ref=ref, pin=unq(p[1]), v=v, x=px, y=py, on=on or ['F.Cu']))

# ---- tracks and vias ----------------------------------------------------
nseg = nvia = 0
for s in find(b, 'segment'):
    ln = unq(val(s, 'layer'))
    if ln not in LI: continue
    a = find(s, 'start')[0]; c = find(s, 'end')[0]
    w = float(val(s, 'width')); v = nid(s)
    x0, y0, x1, y1 = float(a[1]), float(a[2]), float(c[1]), float(c[2])
    n = int(max(abs(x1-x0), abs(y1-y0))/G) + 2
    for i in range(n+1):
        t = i/n; disc(own[LI[ln]], x0+(x1-x0)*t, y0+(y1-y0)*t, w, v)
    nseg += 1
for vn in find(b, 'via'):
    a = find(vn, 'at')[0]; d = float(val(vn, 'size')); v = nid(vn)
    x, y = float(a[1]), float(a[2])
    for ln in LAY:
        disc(own[LI[ln]], x, y, d, v)
        vmap[LI[ln]][max(0,int((x-d/4)/G)):int((x+d/4)/G)+1,
                     max(0,int((y-d/4)/G)):int((y+d/4)/G)+1] = True
    nvia += 1

# ---- simulate the GND pour ---------------------------------------------
# Outline mask: inside the board, inset by the zone's own edge clearance.
board = np.zeros((NX, NY), bool)
inset = int(0.3/G)
board[inset:NX-inset, inset:NY-inset] = True
GV = nidx.get('GND')
rad = int(math.ceil(ZCLR/G))
st = np.ones((2*rad+1, 2*rad+1), bool)
filled = 0
for ln in POUR:
    li = LI[ln]; arr = own[li]
    foreign = (arr != 0) & (arr != GV)
    allowed = board & ~ndimage.binary_dilation(foreign, structure=st)
    # the pour is whatever region of `allowed` touches copper already on GND
    seed = (arr == GV)
    lab, n = ndimage.label(allowed | seed)
    keep = set(np.unique(lab[seed & (lab > 0)]).tolist())
    grown = np.isin(lab, list(keep)) & (allowed | seed)
    newly = grown & (arr == 0)
    arr[newly] = GV
    filled += int(newly.sum())

print(f'{PATH}')
print(f'board {W:.0f} x {H:.0f} mm   pads(netted) {len(PADS)}  tracks {nseg}  vias {nvia}')
print(f'simulated GND pour: {filled*G*G:.0f} mm2 of copper added across {sorted(POUR)}')
print()

# ---- islands per net, joined across layers through vias ----------------
struct = np.ones((3,3), bool)
bad_pads = []
per_net = {}
for v in sorted({p['v'] for p in PADS}):
    nm = nname.get(v, '?')
    if nm.startswith('unconnected-'): continue
    labs = []; off = 0
    for li in range(len(LAY)):
        lab, n = ndimage.label(own[li] == v, structure=struct)
        lab[lab > 0] += off; off += n; labs.append(lab)
    parent = list(range(off+1))
    def fr(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def un(a, c):
        a, c = fr(a), fr(c)
        if a != c: parent[max(a,c)] = min(a,c)
    for li in range(len(LAY)-1):
        for lj in range(li+1, len(LAY)):
            both = (labs[li] > 0) & (labs[lj] > 0) & vmap[li] & vmap[lj]
            if both.any():
                for a, c in set(zip(labs[li][both].tolist(), labs[lj][both].tolist())): un(a, c)
    # which island does each pad sit in
    groups = {}
    for p in [q for q in PADS if q['v'] == v]:
        gx, gy = int(round(p['x']/G)), int(round(p['y']/G))
        gid = None
        for ln in p['on']:
            li = LI[ln]
            sub = labs[li][max(0,gx-2):gx+3, max(0,gy-2):gy+3]
            nz = [int(z) for z in np.unique(sub) if z > 0]
            if nz: gid = fr(nz[0]); break
        groups.setdefault(gid, []).append(p)
    per_net[nm] = groups
    if len(groups) > 1 or None in groups:
        big = max((g for g in groups if g is not None), key=lambda g: len(groups[g]), default=None)
        for gid, ps in groups.items():
            if gid == big: continue
            for p in ps:
                bad_pads.append((nm, p['ref'], p['pin'], round(p['x'],2), round(p['y'],2),
                                 'no copper at all' if gid is None else 'separate island'))

print(f'{"net":13} {"pad":10} {"at":>16}   problem')
print('-'*62)
if not bad_pads:
    print('  every netted pad is in the same island as the rest of its net')
else:
    for nm, ref, pin, x, y, why in bad_pads:
        print(f'{nm:13} {ref+"."+pin:10} {f"({x}, {y})":>16}   {why}')
print()
tot = len([n for n in per_net])
okn = len([n for n, g in per_net.items() if len(g) == 1 and None not in g])
print(f'PADS: {len(PADS)-len(bad_pads)}/{len(PADS)} netted pads properly connected'
      f'   |   NETS: {okn}/{tot} whole (with the pour simulated)')
