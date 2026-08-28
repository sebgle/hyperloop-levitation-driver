#!/usr/bin/env python3
"""
fix_pours.py -- move the vertices that left the coil pours under-width.

    py tools\\fix_pours.py            dry run
    py tools\\fix_pours.py --write    back up, patch, verify, write

WHAT AND WHY

The hand-redrawn single-polygon pours were right in shape and wrong in three
places. Measured with pour_check.py, which rasterises the real outline instead
of its bounding box:

  COIL_B1_B / COIL_B2_B   the west and east bands came in at y=134 instead of
                          138.2, making them 6.50 mm tall where 30 A on 2 oz
                          external needs 10.7. That is a 46 C rise against the
                          20 C the whole board is sized to, held for 33 mm on
                          CH1 and 27 mm on CH2.

  the two drops           9.90 mm and 10.50 mm onto J203.2 and J204.2, so 23 C
                          and 21 C. Marginal rather than dangerous, and free.

  COIL_A2_F               its lower edge at y=69.5 overlapped R211 pad 2
                          (/CH2/SNS_N_F, y 69.30-70.70) by 0.20 mm, putting a
                          Kelvin-sense filter pad partly inside the coil node.
                          The edge goes to 68.9, not 69.0: 69.0 would land on
                          exactly 0.300 mm, and a clearance sitting precisely on
                          its own limit fails or passes on rounding.

Only vertices move. No zone is added, removed, renamed or re-prioritised, and
the 34 vias are untouched.

filled_polygon data is stripped from every zone this edits, because the fill
belongs to KiCad. Press B after opening.
"""
import math, os, re, shutil, sys

PCB = 'final_lev.kicad_pcb'
WRITE = '--write' in sys.argv

NEW = {
    'COIL_A2_F': [(247.5, 59), (258.5, 59), (258.5, 68.9), (251, 68.9),
                  (251, 66), (255, 66), (255, 64.5), (247.5, 64.5)],
    'COIL_B1_B': [(125.85, 150), (125.85, 138.2), (174, 138.2), (173.79, 60.5),
                  (171.29, 60.5), (171.29, 64), (161.33, 64), (161.33, 60.5),
                  (158.83, 60.5), (159.5, 127.5), (115.15, 127.5), (115.15, 150)],
    'COIL_B2_B': [(235.5, 161.5), (246.2, 161.5), (246.2, 127.5), (208.5, 127.5),
                  (208.5, 60.5), (206.29, 60.5), (206.29, 64), (196.33, 64),
                  (196.33, 60.5), (193.83, 60.5), (193.8, 138.2), (235.5, 138.2)],
}
CLR = 0.3
AMPS, OZ2 = 30.0, 0.0696


def num(v):
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else ('%g' % v)


def blocks(lines, head):
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


def sub_blocks(seg, head):
    """Same bracket walk, one level in, for filled_polygon inside a zone."""
    out, start, depth = [], None, 0
    for i, ln in enumerate(seg):
        if start is None and ln.lstrip().startswith(head):
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

zs = blocks(lines, '\t(zone')
print('zones found: %d' % len(zs))
edited, out_lines, cursor = [], [], 0
for a, b in zs:
    nm = re.search(r'\(name "([^"]*)"', eol.join(lines[a:b + 1]))
    name = nm.group(1) if nm else '?'
    if name not in NEW:
        continue
    seg = lines[a:b + 1]
    # 1. replace the outline point list
    pi = [i for i, ln in enumerate(seg) if ln.strip().startswith('(polygon')]
    assert len(pi) == 1, '%s: expected one (polygon' % name
    ptsi = [i for i in range(pi[0], len(seg)) if '(xy ' in seg[i]]
    lo, hi = ptsi[0], ptsi[-1]
    indent = seg[lo][:len(seg[lo]) - len(seg[lo].lstrip())]
    seg[lo:hi + 1] = [indent + ' '.join('(xy %s %s)' % (num(x), num(y))
                                        for x, y in NEW[name])]
    # 2. drop KiCad's cached fill for this zone
    for s0, s1 in reversed(sub_blocks(seg, '(filled_polygon')):
        del seg[s0:s1 + 1]
    lines[a:b + 1] = seg + [None] * (b - a + 1 - len(seg))
    edited.append(name)

lines = [l for l in lines if l is not None]
out = eol.join(lines)
blob = out.encode('utf-8')
print('zones edited: %s' % ', '.join(edited))

# ---------------------------------------------------------------- verify
after = out.replace('\r\n', '\n')
ok = len(edited) == len(NEW)
if not ok:
    print('FAIL: expected to edit %d zones, edited %d' % (len(NEW), len(edited)))
if (blob.count(b'\n') - blob.count(b'\r\n')) != lf_before:
    print('FAIL: a bare LF appeared')
    ok = False

al = after.split('\n')
zs2 = blocks(al, '\t(zone')
if len(zs2) != len(zs):
    print('FAIL: zone count changed %d -> %d' % (len(zs), len(zs2)))
    ok = False
for a, b in zs2:
    blk = '\n'.join(al[a:b + 1])
    nm = re.search(r'\(name "([^"]*)"', blk)
    name = nm.group(1) if nm else '?'
    pm = re.search(r'\(polygon\n\t\t\t\(pts\n((?:.|\n)*?)\n\t\t\t\)', blk)
    pts = [(float(x), float(y)) for x, y in
           re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', pm.group(1))] if pm else []
    if name in NEW:
        want = [(float(num(x)), float(num(y))) for x, y in NEW[name]]
        if pts != want:
            print('FAIL: %s vertices did not take' % name)
            ok = False
        if '(filled_polygon' in blk:
            print('FAIL: %s still carries a cached fill' % name)
            ok = False
print('vias: %d (unchanged: %s)'
      % (len(re.findall(r'\n\t\(via\n', after)),
         len(re.findall(r'\n\t\(via\n', after)) == len(re.findall(r'\n\t\(via\n', txt.replace('\r\n', '\n')))))
print('bytes: %d -> %d   bare LF %d -> %d'
      % (len(raw), len(blob), lf_before, blob.count(b'\n') - blob.count(b'\r\n')))

if not ok:
    sys.exit('\nnothing written.')
print('\nvertex edits verified. Run tools/pour_check.py afterwards for the geometry.')

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
