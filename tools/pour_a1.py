#!/usr/bin/env python3
"""
pour_a1.py -- lay the CH1 leg-A coil path: two zones and the via array.

    py tools\\pour_a1.py            dry run
    py tools\\pour_a1.py --write    back up, patch, verify, write

WHAT IT BUILDS
    COIL_A1_B   B.Cu  x[101.5,112.5] y[59,161]   the 30 A pour, 11.0 mm wide
    COIL_A1_F   F.Cu  x[101.5,111.5] y[59,65.5]  the landing pad off the shunt
    15 vias     1.2 mm pad / 0.6 mm drill, 2.0 mm grid, 2.0 A each

WHY THESE NUMBERS
    11.0 mm against the 10.7 mm IPC-2221 asks for 30 A on 2 oz external at
    dT = 20 C. The F.Cu zone stops at x 111.5 and y 65.5 so it does not wrap
    R11 pads 1 and 2. Pad 2 is a Kelvin sense tap and COIL_A1 swings the full
    bus every cycle, so ringing that pad with this net would put the switching
    edge straight onto the one measurement the overcurrent trip depends on.

    The zones are written WITHOUT their filled_polygon. KiCad regenerates that
    on 'B'. Anything this script computed about fill geometry would be a guess;
    the fill belongs to the application.

SAFETY
    Refuses to run while KiCad holds the lock. Bytes in, bytes out, so CRLF
    survives. Re-parses its own patched buffer and rechecks every clearance,
    layer by layer, against all 509 pads before writing. Asserts the parser
    matched pads at all, because a regex that matches nothing looks exactly
    like a board with nothing on it.
"""
import math, os, re, shutil, sys, uuid

PCB = 'final_lev.kicad_pcb'
WRITE = '--write' in sys.argv
NET = '/COIL_A1'
CLR = 0.3

ZB = (101.5, 112.5, 59.0, 161.0)     # B.Cu pour
ZF = (101.5, 111.5, 59.0, 65.5)      # F.Cu landing zone
VIAS = [(x, y) for y in (60.0, 62.0, 64.0)
        for x in (102.5, 104.5, 106.5, 108.5, 110.5)]
VIA_PAD, VIA_DRILL = 1.2, 0.6


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
                      'layers': lm.group(1) if lm else '', 'type': typ})
    return P


def on_layer(lays, layer):
    return '"*.Cu"' in lays or ('"%s"' % layer) in lays


def gap_to_rect(p, r):
    x0, x1, y0, y1 = r
    return math.hypot(max(x0 - (p['x'] + p['w'] / 2), (p['x'] - p['w'] / 2) - x1, 0),
                      max(y0 - (p['y'] + p['h'] / 2), (p['y'] - p['h'] / 2) - y1, 0))


def zone_text(eol, name, layer, rect, priority):
    x0, x1, y0, y1 = rect
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    L = ['\t(zone',
         '\t\t(net "%s")' % NET,
         '\t\t(layer "%s")' % layer,
         '\t\t(uuid "%s")' % uuid.uuid4(),
         '\t\t(name "%s")' % name,
         '\t\t(hatch edge 0.5)',
         '\t\t(priority %d)' % priority,
         '\t\t(connect_pads yes',
         '\t\t\t(clearance %s)' % num(CLR),
         '\t\t)',
         '\t\t(min_thickness 0.25)',
         '\t\t(fill yes',
         '\t\t\t(thermal_gap 0.5)',
         '\t\t\t(thermal_bridge_width 0.5)',
         '\t\t\t(island_removal_mode 0)',
         '\t\t)',
         '\t\t(polygon',
         '\t\t\t(pts',
         '\t\t\t\t' + ' '.join('(xy %s %s)' % (num(a), num(b)) for a, b in pts),
         '\t\t\t)',
         '\t\t)',
         '\t)']
    return eol.join(L)


def via_text(eol, x, y):
    return eol.join(['\t(via',
                     '\t\t(at %s %s)' % (num(x), num(y)),
                     '\t\t(size %s)' % num(VIA_PAD),
                     '\t\t(drill %s)' % num(VIA_DRILL),
                     '\t\t(layers "F.Cu" "B.Cu")',
                     '\t\t(free yes)',
                     '\t\t(net "%s")' % NET,
                     '\t\t(uuid "%s")' % uuid.uuid4(),
                     '\t)'])


def top_blocks(lines, head):
    """(start, end) line spans of top-level items beginning with head."""
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
vias = top_blocks(lines, '\t(via')
segs = top_blocks(lines, '\t(segment')
print('before:  %d zones, %d vias, %d segments' % (len(zones), len(vias), len(segs)))
for a, b in zones:
    nm = [l for l in lines[a:b] if '(name "' in l]
    ly = [l for l in lines[a:b] if '(layer "' in l]
    print('   zone %-16s %s' % (nm[0].strip() if nm else '?', ly[0].strip() if ly else '?'))

# drop every existing via and any COIL_A1 zone; keep everything else untouched
drop = list(vias)
anchor = None
for a, b in zones:
    blk = eol.join(lines[a:b + 1])
    if '"COIL_A1_F"' in blk or '"COIL_A1_B"' in blk:
        drop.append((a, b))
        anchor = a if anchor is None else min(anchor, a)
if anchor is None:
    anchor = zones[0][0]
print('removing %d via blocks and %d COIL_A1 zone blocks'
      % (len(vias), len(drop) - len(vias)))

new = zone_text(eol, 'COIL_A1_B', 'B.Cu', ZB, 1) + eol + \
      zone_text(eol, 'COIL_A1_F', 'F.Cu', ZF, 2) + eol + \
      eol.join(via_text(eol, x, y) for x, y in VIAS)

keep, di = [], sorted(drop)
skip = set()
for a, b in di:
    skip.update(range(a, b + 1))
for i, ln in enumerate(lines):
    if i == anchor:
        keep.append(new)
    if i in skip:
        continue
    keep.append(ln)
out = eol.join(keep)
blob = out.encode('utf-8')

# ---------------------------------------------------------------- verify
after = out.replace('\r\n', '\n')
P = parse_pads(after)
z2 = top_blocks(out.split(eol), '\t(zone')
v2 = top_blocks(out.split(eol), '\t(via')
ok = True
print('\nrecomputed FROM THE PATCHED BUFFER:')
print('  pads parsed          : %d' % len(P))
if len(P) < 500:
    print('  FAIL: parser matched too few pads to trust any clearance below')
    ok = False
print('  zones                : %d   vias: %d' % (len(z2), len(v2)))
if len(z2) != 3 or len(v2) != len(VIAS):
    print('  FAIL: expected 3 zones and %d vias' % len(VIAS))
    ok = False
# The line COUNT changes here on purpose, so CRLF totals must not be compared.
# What must hold is that no bare LF appears: every newline is still part of CRLF.
if (blob.count(b'\n') - blob.count(b'\r\n')) != lf_before:
    print('  FAIL: a bare LF appeared -- line endings are no longer uniform')
    ok = False

for label, rect, layer in (('COIL_A1_B', ZB, 'B.Cu'), ('COIL_A1_F', ZF, 'F.Cu')):
    pop = [p for p in P if on_layer(p['layers'], layer)]
    worst = None
    bonded = []
    for p in pop:
        g = gap_to_rect(p, rect)
        if p['net'] == NET:
            if g == 0:
                bonded.append('%s.%s' % (p['ref'], p['pad']))
            continue
        if worst is None or g < worst[0]:
            worst = (g, '%s.%s [%s]' % (p['ref'], p['pad'], p['net']))
    print('  %-9s %5.1f x %5.1f mm on %-5s  %d pads on layer, bonded to %s'
          % (label, rect[1] - rect[0], rect[3] - rect[2], layer, len(pop),
             ', '.join(bonded) or 'NOTHING'))
    print('              closest foreign pad %.2f mm (%s)' % worst)
    if worst[0] < CLR:
        print('              FAIL: under the %.2f mm clearance' % CLR)
        ok = False
    if not bonded:
        print('              FAIL: zone touches no pad on its own net')
        ok = False

worst = None
for x, y in VIAS:
    if not (ZF[0] + VIA_PAD / 2 <= x <= ZF[1] - VIA_PAD / 2
            and ZF[2] + VIA_PAD / 2 <= y <= ZF[3] - VIA_PAD / 2):
        print('  FAIL: via (%s, %s) is not inside the F.Cu landing zone' % (x, y))
        ok = False
    for p in P:
        if p['net'] == NET:
            continue
        d = math.hypot(max(abs(x - p['x']) - p['w'] / 2, 0),
                       max(abs(y - p['y']) - p['h'] / 2, 0)) - VIA_PAD / 2
        if worst is None or d < worst[0]:
            worst = (d, '%s.%s [%s]' % (p['ref'], p['pad'], p['net']))
print('  vias                 : %d at %.2f A each, closest foreign %.2f mm (%s)'
      % (len(VIAS), 30.0 / len(VIAS), worst[0], worst[1]))
if worst[0] < CLR:
    print('              FAIL: under the %.2f mm clearance' % CLR)
    ok = False
print('  line endings         : CRLF %d -> %d   bare LF %d -> %d'
      % (crlf_before, blob.count(b'\r\n'), lf_before,
         blob.count(b'\n') - blob.count(b'\r\n')))
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
