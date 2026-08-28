#!/usr/bin/env python3
"""
pour_a2.py -- the CH2 leg-A coil path. Same job as pour_a1.py, harder corner.

    py tools\\pour_a2.py            dry run
    py tools\\pour_a2.py --write    back up, patch, verify, write

WHY THIS ONE IS NOT A MIRROR OF pour_a1

R11 sits at 180 degrees and R219 sits at 0, so the two shunts are 180-degree
rotations of each other, not mirror images. Each block is internally consistent
-- tap, filter and amplifier pin line up on the same side in both channels --
but the consequence shows up only when you try to take 30 A off the pad:

    R11.4  /COIL_A1  x[105.35,108.65] y[64.85,66.88]   open space directly above
    R219.4 /COIL_A2  x[251.33,254.63] y[66.12,68.15]   R219.3 sits 0.51 mm above it

CH1's coil pad faces an empty 11 x 5.5 mm band. CH2's is fenced: the SNS_N
Kelvin tap covers its top right, the SW_A pad is 1.66 mm to its left. A single
rectangle either misses the pad or swallows a sense tap, and wrapping a Kelvin
tap in a node that swings the full bus every cycle is not on the table.

THE SHAPE

Four same-net rectangles that overlap and merge on fill, rather than one
polygon with an interior notch:

    F1  x[247.5,258.5] y[59.0,64.5]    via field, above the fence
    F2  x[250.0,258.5] y[65.95,68.9]   pad lobe, contains R219.4 whole
    F3  x[250.0,252.9] y[64.0,66.6]    left channel past SNS_N, 2.90 mm
    F4  x[254.95,258.5] y[64.0,66.6]   right channel past SNS_N, 3.55 mm

F3 and F4 are the price of the fence: 6.45 mm of total width across a 1.36 mm
gap, where CH1 has 10 mm of uninterrupted copper. As a continuous conductor
6.45 mm of 2 oz would run 46 C hot at 30 A, but this constriction is 1.4 mm
long with large copper on both sides, so conduction sideways dominates and the
real rise is far below that. The four vias in F2 exist to reduce it further:
they take current straight off the pad into B.Cu without crossing the fence at
all.

VIAS  15 in F1 on a 2.0 mm grid, 4 in F2 beside the pad. 19 total, 1.58 A each.

SAFETY  Same as pour_a1: refuses to run under the KiCad lock, bytes in and
bytes out so CRLF survives, re-parses its own output, checks clearance layer by
layer, and asserts the parser saw pads at all before believing anything.
"""
import math, os, re, shutil, sys, uuid

PCB = 'final_lev.kicad_pcb'
WRITE = '--write' in sys.argv
NET = '/COIL_A2'
CLR = 0.3

ZB = (247.5, 258.5, 59.0, 149.0)
# name: (x0, x1, y0, y1, priority)
# The four overlap on purpose so they merge into one pour, and KiCad requires
# intersecting zones to carry DISTINCT priorities even when they share a net.
# Same priority is a zones_intersect error, which is how the first cut failed.
# Order runs outward from the pad: F2 owns the pad, then the two channels, then
# the via field. Same net, so the fills merge whatever the order.
ZF = {'COIL_A2_F2': (250.0, 258.5, 65.95, 68.9, 5),
      'COIL_A2_F3': (250.0, 252.9, 64.0, 66.6, 4),
      'COIL_A2_F4': (254.95, 258.5, 64.0, 66.6, 3),
      'COIL_A2_F1': (247.5, 258.5, 59.0, 64.5, 2)}
VIAS = ([(x, y) for y in (60.0, 61.8, 63.6)
         for x in (248.5, 250.5, 252.5, 254.5, 256.5)]
        + [(x, y) for y in (66.7, 68.2) for x in (255.9, 257.7)])
VIA_PAD, VIA_DRILL = 1.2, 0.6
BOND_PAD = ('R219', '4')
CONN_PAD = ('J204', '1')


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
    x0, x1, y0, y1 = r
    return math.hypot(max(x0 - (p['x'] + p['w'] / 2), (p['x'] - p['w'] / 2) - x1, 0),
                      max(y0 - (p['y'] + p['h'] / 2), (p['y'] - p['h'] / 2) - y1, 0))


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


def via_text(eol, x, y):
    return eol.join(['\t(via', '\t\t(at %s %s)' % (num(x), num(y)),
                     '\t\t(size %s)' % num(VIA_PAD), '\t\t(drill %s)' % num(VIA_DRILL),
                     '\t\t(layers "F.Cu" "B.Cu")', '\t\t(free yes)',
                     '\t\t(net "%s")' % NET, '\t\t(uuid "%s")' % uuid.uuid4(), '\t)'])


def top_blocks(lines, head):
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
crlf_before = raw.count(b'\r\n')
lf_before = raw.count(b'\n') - crlf_before
txt = raw.decode('utf-8')
eol = '\r\n' if crlf_before else '\n'
lines = txt.split(eol)

zones = top_blocks(lines, '\t(zone')
vias0 = top_blocks(lines, '\t(via')
print('before:  %d zones, %d vias' % (len(zones), len(vias0)))
for a, b in zones:
    nm = re.search(r'\(name "([^"]*)"', eol.join(lines[a:b + 1]))
    ly = re.search(r'\(layer "([^"]*)"', eol.join(lines[a:b + 1]))
    print('   %-14s %s' % (nm.group(1) if nm else '?', ly.group(1) if ly else '?'))

drop, anchor, oldvias = [], None, 0
for a, b in zones:
    if 'COIL_A2_' in eol.join(lines[a:b + 1]):
        drop.append((a, b))
        anchor = a if anchor is None else min(anchor, a)
for a, b in vias0:
    if '(net "%s")' % NET in eol.join(lines[a:b + 1]):
        drop.append((a, b))
        oldvias += 1
if anchor is None:
    anchor = zones[-1][1] + 1          # append after the last existing zone
print('replacing %d existing COIL_A2 zone blocks and %d of its vias'
      % (len(drop) - oldvias, oldvias))

new = eol.join([zone_text(eol, 'COIL_A2_B', 'B.Cu', ZB, 1)]
               + [zone_text(eol, n, 'F.Cu', r, r[4]) for n, r in sorted(ZF.items())]
               + [via_text(eol, x, y) for x, y in VIAS])

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
v2 = top_blocks(out.split(eol), '\t(via')
print('  zones                : %d   vias: %d (%d new)'
      % (len(z2), len(v2), len(VIAS)))
if (len(z2) != len(zones) - (len(drop) - oldvias) + 5
        or len(v2) != len(vias0) - oldvias + len(VIAS)):
    print('  FAIL: unexpected zone or via count')
    ok = False
if (blob.count(b'\n') - blob.count(b'\r\n')) != lf_before:
    print('  FAIL: a bare LF appeared')
    ok = False

for name, rect, layer in ([('COIL_A2_B', ZB, 'B.Cu')]
                          + [(n, r[:4], 'F.Cu') for n, r in sorted(ZF.items())]):
    pop = [p for p in P if on_layer(p['layers'], layer)]
    worst, bonded = None, []
    for p in pop:
        g = gap(p, rect)
        if p['net'] == NET:
            if g == 0:
                bonded.append('%s.%s' % (p['ref'], p['pad']))
            continue
        if worst is None or g < worst[0]:
            worst = (g, '%s.%s [%s]' % (p['ref'], p['pad'], p['net']))
    flag = '' if worst[0] >= CLR else '   *** UNDER %.2f mm' % CLR
    print('  %-11s %5.2f x %5.2f on %-5s  closest foreign %.2f mm (%s)%s'
          % (name, rect[1] - rect[0], rect[3] - rect[2], layer, worst[0], worst[1], flag))
    if bonded:
        print('              bonded to %s' % ', '.join(sorted(bonded)))
    if worst[0] < CLR:
        ok = False

# the two pads this path exists to join must each be inside something
def covered(ref, pad, rects):
    for p in P:
        if p['ref'] == ref and p['pad'] == pad:
            return any(gap(p, r) == 0 for r in rects)
    return False
if not covered(*BOND_PAD, [r[:4] for r in ZF.values()]):
    print('  FAIL: %s.%s is not bonded to any F.Cu zone' % BOND_PAD)
    ok = False
if not covered(*CONN_PAD, [ZB]):
    print('  FAIL: %s.%s is not bonded to the B.Cu pour' % CONN_PAD)
    ok = False

worst = None
for x, y in VIAS:
    if not any(r[0] + VIA_PAD / 2 <= x <= r[1] - VIA_PAD / 2
               and r[2] + VIA_PAD / 2 <= y <= r[3] - VIA_PAD / 2 for r in ZF.values()):
        print('  FAIL: via (%s, %s) is not inside any F.Cu zone' % (x, y))
        ok = False
    if not (ZB[0] + VIA_PAD / 2 <= x <= ZB[1] - VIA_PAD / 2
            and ZB[2] + VIA_PAD / 2 <= y <= ZB[3] - VIA_PAD / 2):
        print('  FAIL: via (%s, %s) is not inside the B.Cu pour' % (x, y))
        ok = False
    for p in P:
        if p['net'] == NET:
            continue
        d = math.hypot(max(abs(x - p['x']) - p['w'] / 2, 0),
                       max(abs(y - p['y']) - p['h'] / 2, 0)) - VIA_PAD / 2
        if worst is None or d < worst[0]:
            worst = (d, '%s.%s [%s]' % (p['ref'], p['pad'], p['net']))
for i in range(len(VIAS)):
    for j in range(i + 1, len(VIAS)):
        d = math.dist(VIAS[i], VIAS[j]) - VIA_PAD
        if d < CLR:
            print('  FAIL: vias %s and %s are %.2f mm apart' % (VIAS[i], VIAS[j], d))
            ok = False
print('  vias                 : %d at %.2f A each, closest foreign %.2f mm (%s)'
      % (len(VIAS), 30.0 / len(VIAS), worst[0], worst[1]))
if worst[0] < CLR:
    ok = False
pri = [r[4] for r in ZF.values()]
if len(set(pri)) != len(pri):
    print('  FAIL: overlapping zones share a priority -- KiCad calls that zones_intersect')
    ok = False
print('  zone priorities      : %s' % ', '.join(
    '%s=%d' % (n.split('_')[-1], r[4]) for n, r in sorted(ZF.items())))
print('  neck past SNS_N      : %.2f + %.2f = %.2f mm of parallel width'
      % (ZF['COIL_A2_F3'][1] - ZF['COIL_A2_F3'][0],
         ZF['COIL_A2_F4'][1] - ZF['COIL_A2_F4'][0],
         (ZF['COIL_A2_F3'][1] - ZF['COIL_A2_F3'][0]) +
         (ZF['COIL_A2_F4'][1] - ZF['COIL_A2_F4'][0])))
print('  line endings         : bare LF %d -> %d' % (lf_before, blob.count(b'\n') - blob.count(b'\r\n')))
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
