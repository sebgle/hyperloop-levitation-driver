#!/usr/bin/env python3
"""
pour_b1.py -- the CH1 leg-B coil path, bridge midpoint to the yoke connector.

    py tools\\pour_b1.py            dry run
    py tools\\pour_b1.py --write    back up, patch, verify, write

NO VIA FIELD HERE. Every pad carrying the 30 A on this net is through-hole --
Q3 pin 3, Q4 pin 2, J203 pin 2 -- so a B.Cu pour reaches all three down their
own barrels. That is why the A legs needed 15 and 19 vias and this one needs
none: the A legs terminate on a surface-mount shunt.

STILL UNCONNECTED AFTER THIS RUNS: U2.6, C16.2 and R6.1 -- the high-side
driver's VS reference, its bootstrap capacitor and a gate resistor. All three
are surface mount on the front and carry no coil current. Connecting them is a
routing job, not a pour job, and DRC will keep listing them until it is done.

THE FENCE AT THE PIN ROW

TO-220 pins sit on 2.54 mm pitch and both coil pins have a foreign neighbour
0.64 mm away:

    Q3.2 +60V  156.59-158.49         Q4.1 gate  169.05-170.95
    Q3.3 COIL  159.13-161.03         Q4.2 COIL  171.59-173.49
                                     Q4.3 GND   174.13-176.03

One rectangle over the row would swallow the gate pin and both rail pins,
leaving each as a 0.3 mm island inside the switching node. Instead two narrow
lobes reach up to the coil pins only and the body starts below the row at
y 63.4, so no foreign pad ends up inside this pour at all. The copper arriving
at each pin is then about 1.9 mm wide, which is the pad itself. A TO-220 lead is
the constriction and no pour geometry can widen it.

SHAPE  Five overlapping same-net rectangles with distinct priorities, the
pattern pour_a2 settled on after KiCad rejected equal priorities.

    Ba  x[158.8,173.8]   y[63.4,138.2]   vertical run, 15.0 mm wide
    Bb  x[115.15,159.5]  y[127.5,138.2]  west along the clear band, 10.7 mm
    Bc  x[115.15,125.85] y[137.5,148.0]  drop onto J203.2, 10.7 mm
    L1  x[158.83,161.33] y[60.5,64.0]    lobe to Q3.3
    L2  x[171.29,173.79] y[60.5,64.0]    lobe to Q4.2

The y 127.5-138.2 band is free of through-hole pads across its whole 44 mm
span: the test points sit above it at y 116-122, the bulk cap row below at 143.

SAFETY  Refuses to run under the KiCad lock. Bytes in, bytes out, so CRLF
survives. Re-parses its own output, checks clearance layer by layer, asserts the
parser saw pads at all, and refuses to write if two of its zones share a
priority.
"""
import math, os, re, shutil, sys, uuid

PCB = 'final_lev.kicad_pcb'
WRITE = '--write' in sys.argv
NET = '/COIL_B1'
CLR = 0.3
PREFIX = 'COIL_B1_'

# name: (x0, x1, y0, y1, priority)
ZONES = {'COIL_B1_Ba': (158.8, 173.8, 63.4, 138.2, 11),
         'COIL_B1_Bb': (115.15, 159.5, 127.5, 138.2, 12),
         'COIL_B1_Bc': (115.15, 125.85, 137.5, 148.0, 13),
         'COIL_B1_L1': (158.83, 161.33, 60.5, 64.0, 14),
         'COIL_B1_L2': (171.29, 173.79, 60.5, 64.0, 15)}
LAYER = 'B.Cu'
BOND_PADS = [('Q3', '3'), ('Q4', '2'), ('J203', '2')]


def num(v):
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else ('%g' % v)


def parse_pads(text):
    P = []
    for m in re.finditer(r'\(footprint ((?:.|\n)*?)\n\t\)\n', text):
        b = m.group(0)
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
        if not (rm and at):
            continue
        x, y = float(at.group(1)), float(at.group(2))
        a = math.radians(-float(at.group(3) or 0))
        for pm in re.finditer(r'\(pad "([^"]+)" (\w+) [\w_]+\n\t\t\t'
                              r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\n\t\t\t'
                              r'\(size ([\d.]+) ([\d.]+)\)((?:.|\n)*?)\n\t\t\)', b):
            pn, typ, lx, ly, _pa, sw, sh, rest = pm.groups()
            lx, ly = float(lx), float(ly)
            nt = re.search(r'\(net "([^"]*)"', rest)
            lm = re.search(r'\(layers ([^)]*)\)', rest)
            P.append({'x': x + lx * math.cos(a) - ly * math.sin(a),
                      'y': y + lx * math.sin(a) + ly * math.cos(a),
                      'ref': rm.group(1), 'pad': pn,
                      'net': nt.group(1) if nt else '<no net>',
                      'w': float(sw), 'h': float(sh),
                      'layers': lm.group(1) if lm else ''})
    return P


def on_layer(lays, layer):
    return '"*.Cu"' in lays or ('"%s"' % layer) in lays


def gap(p, r):
    return math.hypot(max(r[0] - (p['x'] + p['w'] / 2), (p['x'] - p['w'] / 2) - r[1], 0),
                      max(r[2] - (p['y'] + p['h'] / 2), (p['y'] - p['h'] / 2) - r[3], 0))


def zone_text(eol, name, layer, rect, priority):
    x0, x1, y0, y1 = rect[:4]
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return eol.join([
        '\t(zone', '\t\t(net "%s")' % NET, '\t\t(layer "%s")' % layer,
        '\t\t(uuid "%s")' % uuid.uuid4(), '\t\t(name "%s")' % name,
        '\t\t(hatch edge 0.5)', '\t\t(priority %d)' % priority,
        '\t\t(connect_pads yes', '\t\t\t(clearance %s)' % num(CLR), '\t\t)',
        '\t\t(min_thickness 0.25)', '\t\t(fill yes', '\t\t\t(thermal_gap 0.5)',
        '\t\t\t(thermal_bridge_width 0.5)', '\t\t\t(island_removal_mode 0)', '\t\t)',
        '\t\t(polygon', '\t\t\t(pts',
        '\t\t\t\t' + ' '.join('(xy %s %s)' % (num(a), num(b)) for a, b in pts),
        '\t\t\t)', '\t\t)', '\t)'])


def top_blocks(lines, head):
    """Bracket counting, not a lazy regex: '\\n\\t)' occurs inside a zone."""
    out, start, depth = [], None, 0
    for i, ln in enumerate(lines):
        if start is None and ln.startswith(head):
            start, depth = i, 0
        if start is not None:
            depth += ln.count('(') - ln.count(')')
            if depth <= 0 and i >= start:
                out.append((start, i))
                start = None
    return out


if not os.path.exists(PCB):
    sys.exit('cannot find %s -- run this from the project folder' % PCB)
if os.path.exists('~' + PCB + '.lck'):
    sys.exit('REFUSING: ~%s.lck exists, so KiCad has the board open.' % PCB)

raw = open(PCB, 'rb').read()
lf_before = raw.count(b'\n') - raw.count(b'\r\n')
txt = raw.decode('utf-8')
eol = '\r\n' if b'\r\n' in raw else '\n'
lines = txt.split(eol)

zones = top_blocks(lines, '\t(zone')
print('before: %d zones' % len(zones))
existing_pri = {}
drop, anchor = [], None
for a, b in zones:
    blk = eol.join(lines[a:b + 1])
    if PREFIX in blk:
        drop.append((a, b))
        anchor = a if anchor is None else min(anchor, a)
    else:
        nm = re.search(r'\(name "([^"]*)"', blk)
        ly = re.search(r'\(layer "([^"]*)"', blk)
        pr = re.search(r'\(priority (\d+)\)', blk)
        pm = re.search(r'\(polygon\n\t\t\t\(pts\n((?:.|\n)*?)\n\t\t\t\)',
                       blk.replace(eol, '\n'))
        pts = re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', pm.group(1)) if pm else []
        if pts:
            xs = [float(u) for u, _ in pts]
            ys = [float(v) for _, v in pts]
            existing_pri[nm.group(1) if nm else '?'] = (
                ly.group(1) if ly else '?', int(pr.group(1)) if pr else 0,
                (min(xs), max(xs), min(ys), max(ys)))
if anchor is None:
    anchor = zones[-1][1] + 1
print('replacing %d existing %s zone blocks' % (len(drop), PREFIX))

new = eol.join(zone_text(eol, n, LAYER, r, r[4]) for n, r in sorted(ZONES.items()))
skip = set()
for a, b in drop:
    skip.update(range(a, b + 1))
keep = []
for i, ln in enumerate(lines):
    if i == anchor:
        keep.append(new)
    if i in skip:
        continue
    keep.append(ln)
if anchor >= len(lines):
    keep.append(new)
out = eol.join(keep)
blob = out.encode('utf-8')

# ---------------------------------------------------------------- verify
P = parse_pads(out.replace('\r\n', '\n'))
ok = True
print('\nrecomputed FROM THE PATCHED BUFFER:')
print('  pads parsed          : %d' % len(P))
if len(P) < 500:
    print('  FAIL: parser matched too few pads to trust anything below')
    ok = False
z2 = top_blocks(out.split(eol), '\t(zone')
print('  zones                : %d  (%d new)' % (len(z2), len(ZONES)))
if len(z2) != len(zones) - len(drop) + len(ZONES):
    print('  FAIL: unexpected zone count')
    ok = False
if (blob.count(b'\n') - blob.count(b'\r\n')) != lf_before:
    print('  FAIL: a bare LF appeared')
    ok = False

pop = [p for p in P if on_layer(p['layers'], LAYER)]
for name, r in sorted(ZONES.items()):
    worst, bonded = None, []
    for p in pop:
        g = gap(p, r)
        if p['net'] == NET:
            if g == 0:
                bonded.append('%s.%s' % (p['ref'], p['pad']))
            continue
        if worst is None or g < worst[0]:
            worst = (g, '%s.%s [%s]' % (p['ref'], p['pad'], p['net']))
    flag = '' if worst[0] >= CLR else '   *** UNDER %.2f mm' % CLR
    print('  %-11s %5.2f x %6.2f  pri %-3d closest foreign %.3f mm (%s)%s'
          % (name.replace(PREFIX, ''), r[1] - r[0], r[3] - r[2], r[4],
             worst[0], worst[1], flag))
    if bonded:
        print('              bonded to %s' % ', '.join(sorted(bonded)))
    if worst[0] < CLR:
        ok = False

for ref, pad in BOND_PADS:
    hit = [p for p in P if p['ref'] == ref and p['pad'] == pad]
    if not hit or not any(gap(hit[0], r) == 0 for r in ZONES.values()):
        print('  FAIL: %s.%s is not inside any zone' % (ref, pad))
        ok = False

# no foreign pad may end up enclosed, which is what the two lobes are for
for p in pop:
    if p['net'] == NET:
        continue
    for name, r in ZONES.items():
        if r[0] < p['x'] < r[1] and r[2] < p['y'] < r[3]:
            print('  FAIL: %s.%s [%s] sits inside %s'
                  % (p['ref'], p['pad'], p['net'], name))
            ok = False
print('  enclosed foreign pads: none' if ok else '')

# priorities: distinct among ALL zones that overlap on this layer
allz = dict(existing_pri)
for n, r in ZONES.items():
    allz[n] = (LAYER, r[4], (r[0], r[1], r[2], r[3]))
names = sorted(allz)
clash = 0
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a, b = allz[names[i]], allz[names[j]]
        if a[0] != b[0]:
            continue
        if (min(a[2][1], b[2][1]) - max(a[2][0], b[2][0]) > 1e-9
                and min(a[2][3], b[2][3]) - max(a[2][2], b[2][2]) > 1e-9
                and a[1] == b[1]):
            print('  FAIL: %s and %s overlap on %s at the same priority %d'
                  % (names[i], names[j], a[0], a[1]))
            clash += 1
            ok = False
print('  zone priorities      : %s' % ', '.join(
    '%s=%d' % (n.replace(PREFIX, ''), r[4]) for n, r in sorted(ZONES.items())))
print('  same-priority overlaps across the whole board: %d' % clash)
print('  line endings         : bare LF %d -> %d'
      % (lf_before, blob.count(b'\n') - blob.count(b'\r\n')))
print('  bytes                : %d -> %d' % (len(raw), len(blob)))

if not ok:
    sys.exit('\nnothing written.')
print('\nall checks pass.')

if WRITE:
    bak, n = PCB + '.bak', 0
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
