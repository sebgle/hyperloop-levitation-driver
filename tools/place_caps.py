#!/usr/bin/env python3
"""
place_caps.py -- move eight capacitors next to the pins they serve.

    py tools\\place_caps.py            dry run: computes and prints, writes nothing
    py tools\\place_caps.py --write    back up, patch, verify, write

WHY
`lay.py`'s placement checks reported seven failures. Six of them are these
capacitors sitting too far from the pin they exist to serve:

    U3.6   INA240 supply    58.17 mm from its only +3.3 V capacitor
    U203.6 INA240 supply    38.95 mm
    U1.5   IR2184 supply     6.09 mm  (its partner U2 is at 2.97 mm)
    U206.5 IR2184 supply     6.09 mm
    C209   current out       21.88 mm from J202.15
    C210   current out       28.60 mm from J202.16

The INA240 pair matters most. REF2 on that part is tied to +3.3 V, so the
rail does not merely power the amplifier, it sets the measurement zero. Rail
noise becomes current-measurement offset, on the chain the +/-45 A trip
depends on, centimetres from 30 A switching at 0.5 V/ns.

Positions were found by searching outward from each target pin on a 0.05 mm
grid, rejecting anything whose courtyard collides, leaves the board outline
by less than 0.5 mm, or intrudes on the heatsink shadow. Ground ends need no
neighbouring GND pad: In1.Cu is a solid ground plane, so they reach it with a
via.

SAFETY
Refuses to run while KiCad holds the lock file. Reads and writes bytes so
CRLF survives. Re-parses its own patched buffer, recomputes every courtyard
and every target distance from the patched geometry, and writes nothing
unless they agree. The numbers it prints are the ones it computed.
"""
import math, os, re, shutil, sys

PCB = 'final_lev.kicad_pcb'
WRITE = '--write' in sys.argv

#   ref  ->  (x, y, rotation, target pin, distance required after the move)
MOVES = {
    'C20':  (114.2, 80.45, 270, ('U3', '6')),
    'C213': (245.8, 78.55,  90, ('U203', '6')),
    'C2':   (138.2, 78.90,   0, ('U1', '5')),
    'C1':   (132.85, 81.70, 270, ('U1', '5')),
    'C228': (233.2, 78.90,   0, ('U206', '5')),
    'C227': (227.85, 81.70, 270, ('U206', '5')),
    'C209': (171.7, 172.75,  0, ('J202', '15')),
    'C210': (167.6, 172.60, 180, ('J202', '16')),
}
TARGET_MAX = 3.0            # mm, rail pad to the pin it serves
OUTLINE = (100.0, 260.0, 50.0, 190.0)
EDGE = 0.5
HEATSINK_FACE_Y = 58.6


def num(v):
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else ('%g' % v)


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
            if (min(a[1], b[1]) - max(a[0], b[0]) > 1e-6
                    and min(a[3], b[3]) - max(a[2], b[2]) > 1e-6):
                bad.append((ks[i], ks[j]))
    return bad


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

before = parse(txt.replace('\r\n', '\n'))

# -------------------------------------------------------------- find blocks
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
AT = re.compile(r'^(\t+\(at )(-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?(\).*)$')
touched = []
for a, b in blocks:
    ref = None
    for i in range(a, b + 1):
        m = re.match(r'\t\t\(property "Reference" "([^"]+)"', lines[i])
        if m:
            ref = m.group(1)
            break
    if ref not in MOVES:
        continue
    nx, ny, nang = MOVES[ref][0], MOVES[ref][1], MOVES[ref][2]
    sub, oldang = None, None
    for i in range(a, b + 1):
        ln = lines[i]
        if ln.startswith('\t\t(') and not ln.startswith('\t\t(at '):
            sub = ln[3:].split(' ')[0].split(')')[0]
        m = AT.match(ln)
        if not m:
            continue
        if ln.startswith('\t\t(at '):
            oldang = float(m.group(4) or 0)
            lines[i] = '%s%s %s%s%s' % (m.group(1), num(nx), num(ny),
                                        (' ' + num(nang)) if nang else '',
                                        m.group(5))
        elif (ln.startswith('\t\t\t(at ') and sub in ('property', 'fp_text')
              and oldang is not None):
            ang = (float(m.group(4) or 0) + (nang - oldang)) % 360
            lines[i] = '%s%s %s %s%s' % (m.group(1), m.group(2), m.group(3),
                                         num(ang), m.group(5))
    touched.append(ref)

out = eol.join(lines)
blob = out.encode('utf-8')
crlf_after = blob.count(b'\r\n')
lf_after = blob.count(b'\n') - crlf_after

# ------------------------------------------- recompute from the patched text
after = parse(out.replace('\r\n', '\n'))
ov = overlaps(after)

print('capacitors requested: %d' % len(MOVES))
print('capacitors patched  : %d  ->  %s' % (len(touched), ' '.join(sorted(touched))))
print('line endings        : CRLF %d -> %d   bare LF %d -> %d'
      % (crlf_before, crlf_after, lf_before, lf_after))
print('bytes               : %d -> %d' % (len(raw), len(blob)))
print('')
print('recomputed FROM THE PATCHED BUFFER:')
print('  courtyard overlaps: %d' % len(ov))
ok = True
for ref, (x, y, ang, (tref, tpad)) in sorted(MOVES.items()):
    rail = [pn for pn, (p, nt) in after[ref]['pads'].items() if nt != 'GND'][0]
    tp = before[tref]['pads'][tpad][0]
    was = min(math.hypot(before[ref]['pads'][pn][0][0] - tp[0],
                         before[ref]['pads'][pn][0][1] - tp[1])
              for pn in before[ref]['pads'])
    now = math.hypot(after[ref]['pads'][rail][0][0] - tp[0],
                     after[ref]['pads'][rail][0][1] - tp[1])
    flag = '' if now <= TARGET_MAX else '   OVER LIMIT'
    print('  %-5s -> %-8s  %7.2f mm  ->  %5.2f mm%s'
          % (ref, tref + '.' + tpad, was, now, flag))
    if now > TARGET_MAX:
        ok = False

if len(touched) != len(MOVES):
    print('FAIL: patched %d, expected %d' % (len(touched), len(MOVES)))
    ok = False
if crlf_after != crlf_before or lf_after != lf_before:
    print('FAIL: line endings changed')
    ok = False
if ov:
    print('FAIL: %d courtyard overlaps: %s' % (len(ov), ov[:5]))
    ok = False

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
    print('written : %s  (%d bytes)  identical to buffer: %s'
          % (PCB, len(disk), disk == blob))
else:
    print('dry run -- nothing written. Re-run with --write to apply.')
