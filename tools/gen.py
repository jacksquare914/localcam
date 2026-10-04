import sys, uuid, datetime
sys.path.insert(0,'/home/claude')
from sexp import parse, find, val, unq
from spec import PARTS, NETS, SYMLIB, CORE_SYM

NS=uuid.UUID('6f1c2a44-3b7e-4d1a-9c55-localcam1000'.replace('localcam1000','0a1b2c3d4e5f'))
def U(): return str(uuid.uuid4())
def UD(key): return str(uuid.uuid5(NS,key))   # deterministic: same key -> same uuid every build
def q(s): return '"'+str(s).replace('\\','\\\\').replace('"','\\"')+'"'
def dump(n):
    if isinstance(n,str):
        return q(n[1:]) if n.startswith('"') else n
    return '('+' '.join(dump(x) for x in n)+')'

# ---------- symbol sources ----------
def libpath(lib): return CORE_SYM if lib=='Core1106' else f'{SYMLIB}/{lib}.kicad_sym'
_c={}
def libtree(lib):
    if lib not in _c: _c[lib]=parse(open(libpath(lib)).read())
    return _c[lib]
def symnode(lib,name):
    for s in find(libtree(lib),'symbol'):
        if unq(s[1])==name: return s
    raise KeyError(f'{lib}:{name}')
def resolved(lib,name):
    """Flatten (extends): parent's graphics + child's properties, with the nested
    unit symbols renamed parent_u_s -> child_u_s (KiCad matches units by name)."""
    s=symnode(lib,name); e=val(s,'extends')
    if not e: return s
    par_name=unq(e); par=resolved(lib,par_name)
    childprops={unq(p[1]):p for p in find(s,'property')}
    out=[]
    for x in par:
        if isinstance(x,list) and x and x[0]=='property':
            out.append(childprops.pop(unq(x[1]), x))
        elif isinstance(x,list) and x and x[0]=='symbol':
            y=[z for z in x]; nm=unq(y[1])
            if nm.startswith(par_name): y[1]='"'+name+nm[len(par_name):]
            out.append(y)
        elif isinstance(x,list) and x and x[0]=='extends':
            continue
        else:
            out.append(x)
    for p in reversed(list(childprops.values())): out.insert(2,p)
    out[1]='"'+name
    return out

def pins_of(lib,name):
    s=resolved(lib,name); out={}
    def walk(n):
        for p in find(n,'pin'):
            at=find(p,'at')[0]
            out[unq(val(p,'number'))]=(float(at[1]),float(at[2]),
                                       float(at[3]) if len(at)>3 else 0.0,
                                       float(val(p,'length')))
        for sub in find(n,'symbol'): walk(sub)
    walk(s); return out

# ---------- grid snap: KiCad schematic grid is 50 mil = 1.27 mm ----------
GRID=1.27
def snap(v): return round(round(v/GRID)*GRID, 4)
PLACE={ref:(snap(at[0]),snap(at[1])) for ref,(_,_,_,_,at) in PARTS.items()}

# ---------- build lib_symbols: verbatim KiCad 10 library bodies (flattened) ----------
used={}                                        # lib_id -> node
for ref,(lib,name,valstr,fp,at) in PARTS.items():
    lid=f'{lib}:{name}'
    if lid not in used:
        n=[x for x in resolved(lib,name)]
        n[1]='"'+lid                            # rename to Lib:Name
        used[lid]=n

# ---------- emit (KiCad 10.0 dialect, version 20260101) ----------
SHEET_U=UD('sheet:root')
L=['(kicad_sch (version 20260101) (generator "eeschema") (generator_version "10.0")',
   f'  (uuid {q(SHEET_U)})','  (paper "A2")',
   '  (title_block (title "LocalCam-1 Rev A") '
   f'(date {q(datetime.date.today().isoformat())}) (rev "A") '
   '(comment 1 "Generated from spec.py - do not hand-edit") '
   '(comment 2 "5V in on VCC5V0_SYS 79/80/81; module PMIC outputs 3V3 (78) and 1V8 (77)"))',
   '  (lib_symbols']
for lid,n in used.items(): L.append('    '+dump(n))
L.append('  )')

# --- symbol instances ---
FX='(effects (font (size 1.27 1.27)))'
for ref,(lib,name,valstr,fp,_at) in PARTS.items():
    X,Y=PLACE[ref]
    lid=f'{lib}:{name}'; pm=pins_of(lib,name)
    ys=[Y-p[1] for p in pm.values()] or [Y]
    L.append(f'  (symbol (lib_id {q(lid)}) (at {X} {Y} 0) (unit 1) (body_style 1)')
    nobom = ref.startswith(('TP','MH','PWR')); noboard = ref.startswith('PWR')
    L.append(f'    (exclude_from_sim no) (in_bom {"no" if nobom else "yes"}) (on_board {"no" if noboard else "yes"}) (in_pos_files {"no" if nobom else "yes"}) (dnp no) (uuid {q(UD("sym:"+ref))})')
    L.append(f'    (property "Reference" {q(ref)} (at {X} {round(min(ys)-5.08,4)} 0) {FX})')
    L.append(f'    (property "Value" {q(valstr)} (at {X} {round(max(ys)+5.08,4)} 0) {FX})')
    L.append(f'    (property "Footprint" {q(fp)} (at {X} {Y} 0) (hide yes) {FX})')
    L.append(f'    (property "Datasheet" "" (at {X} {Y} 0) (hide yes) {FX})')
    L.append(f'    (property "Description" "" (at {X} {Y} 0) (hide yes) {FX})')
    for pn in pm: L.append(f'    (pin {q(pn)} (uuid {q(U())}))')
    L.append(f'    (instances (project "LocalCam1" (path {q("/"+SHEET_U)} (reference {q(ref)}) (unit 1))))')
    L.append('  )')

# --- stubs + global labels: one per pin, per net ---
STUB=5.08
DIR={0:(-1,0,180), 180:(1,0,0), 90:(0,1,270), 270:(0,-1,90)}   # pin ang -> stub dx,dy,label ang
nlab=0
connected=set()                     # (ref,pin) that carry a net
for net,conns in NETS.items():
    seen=set()                      # KiCad stacks internally-common pins at one
    for ref,pn in conns:            # coordinate; one stub serves the whole stack
        lib,name,_,_,_at=PARTS[ref]; X,Y=PLACE[ref]
        pm=pins_of(lib,name)
        if pn not in pm: raise SystemExit(f'!! {ref} has no pin {pn}')
        connected.add((ref,pn))
        px,py,ang,_=pm[pn]
        sx,sy=round(X+px,4), round(Y-py,4)
        if (sx,sy) in seen: continue
        seen.add((sx,sy))
        dx,dy,la=DIR[int(ang)%360]
        ex,ey=sx+dx*STUB, sy+dy*STUB
        L.append(f'  (wire (pts (xy {sx} {sy}) (xy {ex} {ey})) '
                 f'(stroke (width 0) (type default)) (uuid {q(U())}))')
        L.append(f'  (global_label {q(net)} (shape passive) (at {ex} {ey} {la}) (fields_autoplaced yes)')
        L.append(f'    (effects (font (size 1.27 1.27)) (justify left)) (uuid {q(U())})')
        L.append(f'    (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
        L.append('  )')
        nlab+=1

# --- no-connect flags: every pin that carries no net is intentionally unused ---
nnc=0
for ref,(lib,name,_,_,_at) in PARTS.items():
    X,Y=PLACE[ref]; pm=pins_of(lib,name); seen=set()
    for pn,(px,py,ang,_) in pm.items():
        if (ref,pn) in connected: continue
        sx,sy=round(X+px,4), round(Y-py,4)
        if (sx,sy) in seen: continue          # stacked pins share one flag
        seen.add((sx,sy))
        L.append(f'  (no_connect (at {sx} {sy}) (uuid {q(U())}))')
        nnc+=1
L.append('  (sheet_instances (path "/" (page "1")))')
L.append('  (embedded_fonts no)')
L.append(')')
open('LocalCam1.kicad_sch','w').write('\n'.join(L)+'\n')
print(f'wrote LocalCam1.kicad_sch  parts={len(PARTS)} lib_symbols={len(used)} labels={nlab} no_connects={nnc}')
