#!/usr/bin/env python3
"""
place_testpoints.py -- place the thirteen test points.

    py tools\\place_testpoints.py            dry run
    py tools\\place_testpoints.py --write    back up, patch, verify, write

WHY THESE POSITIONS
A test point is only worth having if you can get a probe onto it, and a signal
measurement is only worth having if its ground reference is next to it. So the
three ground points were placed first, against the part each group serves, and
the signal points were then clustered around their own ground rather than
against the net they measure. A 6 mm trace to a test point costs nothing on
these signals; a 60 mm probe ground lead ruins the measurement.

Two keepouts the search respected, beyond courtyards and the board edge:

  the heatsink shadow, so nothing lands under the extrusion, and
  the four coil-pour corridors on B.Cu, 10.7 mm wide, because these are
  through-hole loops and their barrels would punch holes in a 30 A pour.

The first solve put TP213 in the 4.5 mm gap between two TO-220s under the
heatsink -- geometrically legal and impossible to reach with a probe hook. It
now sits in the clear channel between the two channels, below the ceramic row.

SAFETY
Refuses to run while KiCad holds the lock file. Bytes in, bytes out, so CRLF
survives. Re-parses its own patched buffer and recomputes every courtyard and
every group distance before writing.
"""
import math, os, re, shutil, sys

PCB = 'final_lev.kicad_pcb'
WRITE = '--write' in sys.argv

MOVES = {
    'TP201': (116.75, 120.15),
    'TP202': (214.25, 118.85),
    'TP203': (120.50, 121.70),
    'TP204': (210.65, 116.05),
    'TP205': (124.25, 116.40),
    'TP206': (210.35, 112.40),
    'TP207': (116.75, 116.40),
    'TP208': (214.25, 115.10),
    'TP209': (203.55, 174.70),
    'TP210': (196.05, 174.70),
    'TP211': (198.85, 171.10),
    'TP212': (199.80, 174.70),
    'TP213': (183.25, 70.00),
}
GROUPS = {'TP207': ('TP201', 'TP203', 'TP205'),
          'TP208': ('TP202', 'TP204', 'TP206'),
          'TP212': ('TP209', 'TP210', 'TP211')}
GROUP_MAX = 8.0          # mm, signal test point to its own ground point

# Reference text that collides with a neighbour's. Offsets are local to the
# footprint, so they move the silkscreen label only and nothing electrical.
# TP204 and TP208 sit 3.7 mm apart and their default labels, both at
# (0.7, 2.5), overlapped by 0.15 mm in x. TP204's goes to the left instead.
SILK = {'TP204': (-2.6, 0)}


def num(v):
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else ('%g' % v)


def crt(blk, x, y, ang):
    pts = []
    for mm in re.finditer(r'\(fp_(?:line|poly|rect|circle)((?:.|\n)*?)\n\t\t\)', blk):
        b = mm.group(0)
        if '"F.CrtYd"' not in b:
            continue
        if b.startswith('(fp_circle'):
            c = re.search(r'\(center ([-\d.]+) ([-\d.]+)\)', b)
            e = re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', b)
            cx, cy = float(c.group(1)), float(c.group(2))
            rr = math.hypot(float(e.group(1)) - cx, float(e.group(2)) - cy)
            pts += [(cx - rr, cy - rr), (cx + rr, cy + rr)]
        else:
            for a, c in re.findall(r'\((?:xy|start|end) ([-\d.]+) ([-\d.]+)\)', b):
                pts.append((float(a), float(c)))
    if not pts:
        return None
    a = math.radians(-ang)
    o = [(x + lx * math.cos(a) - ly * math.sin(a),
          y + lx * math.sin(a) + ly * math.cos(a)) for lx, ly in pts]
    return (min(p[0] for p in o), max(p[0] for p in o),
            min(p[1] for p in o), max(p[1] for p in o))


def parse(text):
    F = {}
    for m in re.finditer(r'\(footprint ((?:.|\n)*?)\n\t\)\n', text):
        b = m.group(0)
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        if not (at and rm):
            continue
        x, y = float(at.group(1)), float(at.group(2))
        ang = float(at.group(3) or 0)
        nets = {}
        for pm in re.finditer(r'\(pad "([^"]+)"((?:.|\n)*?)\n\t\t\)', b):
            nt = re.search(r'\(net "([^"]+)"', pm.group(2))
            nets[pm.group(1)] = nt.group(1) if nt else None
        F[rm.group(1)] = {'x': x, 'y': y, 'ang': ang, 'nets': nets,
                          'c': crt(b, x, y, ang)}
    return F


def overlaps(F):
    ks = [k for k in F if F[k]['c']]
    bad = []
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = F[ks[i]]['c'], F[ks[j]]['c']
            if (min(a[1], b[1]) - max(a[0], b[0]) > 1e-6
                    and min(a[3], b[3]) - max(a[2], b[2]) > 1e-6):
                bad.append((ks[i], ks[j]))
    return bad


if not os.path.exists(PCB):
    sys.exit('cannot find %s -- run this from the project folder' % PCB)
lock = '~' + PCB + '.lck'
if os.path.exists(lock):
    sys.exit('REFUSING: %s exists, so KiCad has the board open.' % lock)

raw = open(PCB, 'rb').read()
crlf_before = raw.count(b'\r\n')
lf_before = raw.count(b'\n') - crlf_before
txt = raw.decode('utf-8')
eol = '\r\n' if crlf_before else '\n'
lines = txt.split(eol)

blocks, start, depth = [], None, 0
for i, ln in enumerate(lines):
    if ln.startswith('\t(footprint '):
        start, depth = i, 0
    if start is not None:
        depth += ln.count('(') - ln.count(')')
        if depth <= 0 and i > start:
            blocks.append((start, i))
            start = None

AT = re.compile(r'^(\t\t\(at )(-?[\d.]+) (-?[\d.]+)((?: -?[\d.]+)?\).*)$')
touched = []
silked = []
for a, b in blocks:
    ref = None
    for i in range(a, b + 1):
        m = re.match(r'\t\t\t\(property "Reference" "([^"]+)"', lines[i]) or \
            re.match(r'\t\t\(property "Reference" "([^"]+)"', lines[i])
        if m:
            ref = m.group(1)
            break
    if ref not in MOVES:
        continue
    nx, ny = MOVES[ref]
    for i in range(a, b + 1):
        m = AT.match(lines[i])
        if m:
            lines[i] = '%s%s %s%s' % (m.group(1), num(nx), num(ny), m.group(4))
            break
    if ref in SILK:
        sx, sy = SILK[ref]
        for i in range(a, b + 1):
            if '(property "Reference"' in lines[i]:
                for j in range(i + 1, min(i + 4, b + 1)):
                    mm = re.match(r'^(\t+\(at )(-?[\d.]+) (-?[\d.]+)(.*)$', lines[j])
                    if mm:
                        lines[j] = '%s%s %s%s' % (mm.group(1), num(sx), num(sy), mm.group(4))
                        silked.append(ref)
                        break
                break
    touched.append(ref)

out = eol.join(lines)
blob = out.encode('utf-8')
after = parse(out.replace('\r\n', '\n'))
ov = overlaps(after)

print('test points requested: %d' % len(MOVES))
print('test points patched  : %d' % len(touched))
print('silk labels moved   : %d  %s' % (len(silked), ' '.join(silked)))
print('line endings         : CRLF %d -> %d   bare LF %d -> %d'
      % (crlf_before, blob.count(b'\r\n'), lf_before,
         blob.count(b'\n') - blob.count(b'\r\n')))
print('bytes                : %d -> %d\n' % (len(raw), len(blob)))
print('recomputed FROM THE PATCHED BUFFER:')
print('  courtyard overlaps: %d' % len(ov))
ok = len(touched) == len(MOVES) and len(silked) == len(SILK) and not ov
if blob.count(b'\r\n') != crlf_before:
    print('FAIL: line endings changed'); ok = False
for g, members in sorted(GROUPS.items()):
    gx, gy = after[g]['x'], after[g]['y']
    for t in members:
        d = math.hypot(after[t]['x'] - gx, after[t]['y'] - gy)
        flag = '' if d <= GROUP_MAX else '   OVER LIMIT'
        print('  %-6s [%-14s] %5.2f mm from its ground %s%s'
              % (t, after[t]['nets']['1'], d, g, flag))
        if d > GROUP_MAX:
            ok = False
print('  %-6s [%-14s] bridge reference at (%s, %s)'
      % ('TP213', after['TP213']['nets']['1'], num(after['TP213']['x']), num(after['TP213']['y'])))
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
    print('backup  : %s' % bak)
    print('written : %s  (%d bytes)  identical: %s'
          % (PCB, len(open(PCB, 'rb').read()), open(PCB, 'rb').read() == blob))
else:
    print('dry run -- nothing written. Re-run with --write to apply.')
