#!/usr/bin/env python3
"""
rot_ceramics.py -- rotate the leg-A bridge ceramics 180 degrees.

    py tools\\rot_ceramics.py            dry run: computes and prints, writes nothing
    py tools\\rot_ceramics.py --write    back up, patch, verify, write

WHY
The C-H-C-H thermal ordering (docs/20 section 20.2) forces leg A to be
low-side-then-high-side and leg B to be high-side-then-low-side.  So leg A's
+60V pad sits on the RIGHT of the leg and leg B's on the LEFT.  Every bridge
ceramic is placed at 0 deg, which puts pad 1 (+60V) on the left: correct for
leg B, backwards for leg A.  Rotating leg A's ceramics 180 deg takes that
leg's commutation loop from 17.72 mm to 12.89 mm.  Rotation only -- x, y,
nets and courtyards are untouched.

FIDELITY
Reproduces exactly what the KiCad GUI writes for a 0 -> 180 rotation, as
established by diffing U1 (0 deg) against U2 (180 deg) in this same board
file: the footprint (at) gains the angle, and every (at) inside a
(property ...) or (fp_text ...) sub-block has 180 added to its angle field.
Local offsets, pads and graphics are not touched.

SAFETY
Refuses to run while KiCad holds the lock file.  Reads and writes bytes so
CRLF survives.  Prints the numbers it COMPUTED by re-deriving the geometry
from the patched buffer -- not the numbers it was told to expect -- and
writes nothing unless those agree.
"""
import math, os, re, shutil, sys

PCB = 'final_lev.kicad_pcb'
WRITE = '--write' in sys.argv
TARGETS = set('C3 C5 C6 C7 C8 C212 C214 C215 C216 C217'.split())
LEGS = {'CH1 A': ('Q1', '2', 'Q2', '3'), 'CH1 B': ('Q3', '2', 'Q4', '3'),
        'CH2 A': ('Q201', '2', 'Q202', '3'), 'CH2 B': ('Q203', '2', 'Q204', '3')}
EXPECT = {'CH1 A': 12.89, 'CH1 B': 16.73, 'CH2 A': 12.89, 'CH2 B': 16.73}
TOL = 0.05

AT = re.compile(r'^(\t+\(at )(-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?(\).*)$')


def num(v):
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else ('%g' % v)


# ---------------------------------------------------------------- geometry
def crt(blk, x, y, ang):
    pts = []
    for mm in re.finditer(r'\(fp_(?:line|poly|rect)((?:.|\n)*?)\n\t\t\)', blk):
        b = mm.group(0)
        if '"F.CrtYd"' not in b:
            continue
        for a, c in re.findall(r'\((?:xy|start|end) ([-\d.]+) ([-\d.]+)\)', b):
            pts.append((float(a), float(c)))
    for mm in re.finditer(r'\(fp_circle((?:.|\n)*?)\n\t\t\)', blk):
        b = mm.group(0)
        if '"F.CrtYd"' not in b:
            continue
        c = re.search(r'\(center ([-\d.]+) ([-\d.]+)\)', b)
        e = re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', b)
        cx, cy = float(c.group(1)), float(c.group(2))
        rr = math.hypot(float(e.group(1)) - cx, float(e.group(2)) - cy)
        pts += [(cx - rr, cy - rr), (cx + rr, cy + rr)]
    if not pts:
        return None
    a = math.radians(-ang)
    o = [(x + lx * math.cos(a) - ly * math.sin(a),
          y + lx * math.sin(a) + ly * math.cos(a)) for lx, ly in pts]
    return (min(p[0] for p in o), max(p[0] for p in o),
            min(p[1] for p in o), max(p[1] for p in o))


def parse(text):
    """text must use \\n line endings."""
    F = {}
    for m in re.finditer(r'\(footprint ((?:.|\n)*?)\n\t\)\n', text):
        b = m.group(0)
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        if not (at and rm):
            continue
        x, y = float(at.group(1)), float(at.group(2))
        ang = float(at.group(3) or 0)
        pads = {}
        for pm in re.finditer(r'\(pad "([^"]+)"((?:.|\n)*?)\n\t\t\)', b):
            pa = re.search(r'\(at ([-\d.]+) ([-\d.]+)', pm.group(2))
            nt = re.search(r'\(net "([^"]+)"', pm.group(2))
            a = math.radians(-ang)
            lx, ly = float(pa.group(1)), float(pa.group(2))
            pads[pm.group(1)] = ((x + lx * math.cos(a) - ly * math.sin(a),
                                  y + lx * math.sin(a) + ly * math.cos(a)),
                                 nt.group(1) if nt else None)
        F[rm.group(1)] = {'x': x, 'y': y, 'ang': ang, 'pads': pads,
                          'c': crt(b, x, y, ang)}
    return F


def overlaps(F):
    ks = [k for k in F if F[k]['c']]
    bad = []
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = F[ks[i]]['c'], F[ks[j]]['c']
            if (min(a[1], b[1]) - max(a[0], b[0]) > 1e-6 and
                    min(a[3], b[3]) - max(a[2], b[2]) > 1e-6):
                bad.append((ks[i], ks[j]))
    return bad


def loops(F):
    d = lambda p, q: math.hypot(p[0] - q[0], p[1] - q[1])
    cer = [r for r, v in F.items() if len(v['pads']) == 2 and
           {p[1] for p in v['pads'].values()} == {'+60V', 'GND'} and
           63 < v['y'] < 70]
    out = {}
    for leg, (hs, hp, ls, lp) in LEGS.items():
        hv = F[hs]['pads'][hp][0]
        gp = F[ls]['pads'][lp][0]
        out[leg] = sorted((d(hv, F[c]['pads']['1'][0]) +
                           d(F[c]['pads']['2'][0], gp), c) for c in cer)[:2]
    return out


# ------------------------------------------------------------------ guards
if not os.path.exists(PCB):
    sys.exit('cannot find %s -- run this from the project folder' % PCB)
lock = '~' + PCB + '.lck'
if os.path.exists(lock):
    sys.exit('REFUSING: %s exists, so KiCad has the board open.\n'
             'Close KiCad first -- a save from the editor silently overwrites '
             'external edits.' % lock)

raw = open(PCB, 'rb').read()
crlf_before = raw.count(b'\r\n')
lf_before = raw.count(b'\n') - crlf_before
txt = raw.decode('utf-8')
eol = '\r\n' if crlf_before else '\n'
lines = txt.split(eol)

# --------------------------------------------------------- locate footprints
blocks, start, depth = [], None, 0
for i, ln in enumerate(lines):
    if ln.startswith('\t(footprint '):
        start, depth = i, 0
    if start is not None:
        depth += ln.count('(') - ln.count(')')
        if depth <= 0 and i > start:
            blocks.append((start, i))
            start = None

# ------------------------------------------------------------------- patch
touched, skipped = [], []
for a, b in blocks:
    ref = None
    for i in range(a, b + 1):
        m = re.match(r'\t\t\(property "Reference" "([^"]+)"', lines[i])
        if m:
            ref = m.group(1)
            break
    if ref not in TARGETS:
        continue
    sub = None
    hits = 0
    for i in range(a, b + 1):
        ln = lines[i]
        if ln.startswith('\t\t(') and not ln.startswith('\t\t(at '):
            sub = ln[3:].split(' ')[0].split(')')[0]
        m = AT.match(ln)
        if not m:
            continue
        is_fp = ln.startswith('\t\t(at ')
        is_txt = ln.startswith('\t\t\t(at ') and sub in ('property', 'fp_text')
        if not (is_fp or is_txt):
            continue
        ang = (float(m.group(4) or 0) + 180.0) % 360.0
        lines[i] = '%s%s %s %s%s' % (m.group(1), m.group(2), m.group(3),
                                     num(ang), m.group(5))
        hits += 1
    touched.append((ref, hits))

out = eol.join(lines)
blob = out.encode('utf-8')
crlf_after = blob.count(b'\r\n')
lf_after = blob.count(b'\n') - crlf_after

# ------------------------------------------------- recompute from the patch
F = parse(out.replace('\r\n', '\n'))
ov = overlaps(F)
lp = loops(F)

print('targets requested : %d' % len(TARGETS))
print('footprints patched: %d  ->  %s' %
      (len(touched), ', '.join('%s(%d at-lines)' % t for t in sorted(touched))))
print('line endings      : CRLF %d -> %d   bare LF %d -> %d' %
      (crlf_before, crlf_after, lf_before, lf_after))
print('bytes             : %d -> %d' % (len(raw), len(blob)))
print('')
print('recomputed FROM THE PATCHED BUFFER:')
print('  courtyard overlaps: %d' % len(ov))
for leg in ('CH1 A', 'CH1 B', 'CH2 A', 'CH2 B'):
    pair = '   '.join('%5.2f mm (%s)' % (v, c) for v, c in lp[leg])
    print('  %-6s %s' % (leg, pair))
for r, _ in sorted(touched):
    d = F[r]
    print('  %-5s at (%s, %s) rot %s' % (r, num(d['x']), num(d['y']), num(d['ang'])))

ok = True
if len(touched) != len(TARGETS):
    print('FAIL: patched %d footprints, expected %d' % (len(touched), len(TARGETS))); ok = False
if crlf_after != crlf_before or lf_after != lf_before:
    print('FAIL: line endings changed'); ok = False
if ov:
    print('FAIL: %d courtyard overlaps' % len(ov)); ok = False
for leg, want in EXPECT.items():
    got = lp[leg][0][0]
    if abs(got - want) > TOL:
        print('FAIL: %s loop %.2f mm, expected %.2f mm' % (leg, got, want)); ok = False
for r, _ in touched:
    if abs(F[r]['ang'] - 180.0) > 1e-9:
        print('FAIL: %s rot is %s, expected 180' % (r, F[r]['ang'])); ok = False

if not ok:
    sys.exit('\nnothing written.')
print('\nall checks pass.')

if WRITE:
    bak = PCB + '.bak'
    n = 0
    while os.path.exists(bak):
        n += 1
        bak = '%s.bak%d' % (PCB, n)
    shutil.copyfile(PCB, bak)
    open(PCB, 'wb').write(blob)
    disk = open(PCB, 'rb').read()
    print('backup  : %s' % bak)
    print('written : %s  (%d bytes, CRLF %d, bare LF %d)  identical to buffer: %s'
          % (PCB, len(disk), disk.count(b'\r\n'),
             disk.count(b'\n') - disk.count(b'\r\n'), disk == blob))
else:
    print('dry run -- nothing written. Re-run with --write to apply.')
