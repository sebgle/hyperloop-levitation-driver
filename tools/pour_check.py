#!/usr/bin/env python3
"""
pour_check.py -- audit copper pours drawn as arbitrary polygons.

    py tools\\pour_check.py [board.kicad_pcb]

WHY THIS EXISTS
lay.py's zone check treats every zone as its bounding box, which is exact only
while the zones are rectangles. Hand-drawn single-polygon pours are not, and a
bounding box would have called a staircase a solid block and missed every neck.
This one rasterises the real outline.

WHAT IT REPORTS, per coil net:
  bonded pads        every pad of the net that the polygon actually encloses
  enclosed foreign   any other net's pad sitting inside the pour, which strands
                     it as an island in a node that swings the full bus
  clearance          true polygon-edge distance, not box distance
  width profile      the narrowest cut across the conductor along its path, and
                     the IPC-2221 temperature rise that width implies at 30 A
                     (external, 2 oz, I = 0.048 * dT^0.44 * A^0.725, A in mil^2)

A pour is only as good as its narrowest cut. 10.7 mm buys nothing if the copper
necks to 6 mm somewhere in the middle, so the number that matters is the
minimum, not the nominal.
"""
import math, re, sys

PCB = sys.argv[1] if len(sys.argv) > 1 else 'final_lev.kicad_pcb'
STEP = 0.05
OZ2 = 0.0696          # mm, 2 oz copper
AMPS = 30.0
CLR = 0.3
TARGET_W = 10.7        # mm, the width this project sized 30 A on 2 oz to
NETS = ('/COIL_A1', '/COIL_A2', '/COIL_B1', '/COIL_B2')

s = open(PCB, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
lines = s.split('\n')


def top_blocks(head):
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


Z = []
for a, b in top_blocks('\t(zone'):
    blk = '\n'.join(lines[a:b + 1])
    nm = re.search(r'\(name "([^"]*)"', blk)
    ly = re.search(r'\(layer "([^"]*)"', blk)
    nt = re.search(r'\(net "([^"]*)"', blk)
    pr = re.search(r'\(priority (\d+)\)', blk)
    pm = re.search(r'\(polygon\n\t\t\t\(pts\n((?:.|\n)*?)\n\t\t\t\)', blk)
    pts = [(float(x), float(y)) for x, y in
           re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', pm.group(1))] if pm else []
    if pts:
        Z.append({'name': nm.group(1) if nm else '?', 'layer': ly.group(1) if ly else '?',
                  'net': nt.group(1) if nt else '?', 'pri': int(pr.group(1)) if pr else 0,
                  'pts': pts})
assert Z, 'no zones parsed'

P = []
for m in re.finditer(r'\(footprint ((?:.|\n)*?)\n\t\)\n', s):
    b = m.group(0)
    rm = re.search(r'\(property "Reference" "([^"]+)"', b)
    at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
    if not (rm and at):
        continue
    x, y = float(at.group(1)), float(at.group(2))
    ang = math.radians(-float(at.group(3) or 0))
    for pm in re.finditer(r'\(pad "([^"]+)" (\w+) [\w_]+\n\t\t\t'
                          r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\n\t\t\t'
                          r'\(size ([\d.]+) ([\d.]+)\)((?:.|\n)*?)\n\t\t\)', b):
        pn, typ, lx, ly, _pa, sw, sh, rest = pm.groups()
        lx, ly = float(lx), float(ly)
        nt = re.search(r'\(net "([^"]*)"', rest)
        lm = re.search(r'\(layers ([^)]*)\)', rest)
        P.append({'x': x + lx * math.cos(ang) - ly * math.sin(ang),
                  'y': y + lx * math.sin(ang) + ly * math.cos(ang),
                  'ref': rm.group(1), 'pad': pn,
                  'net': nt.group(1) if nt else '<no net>',
                  'w': float(sw), 'h': float(sh),
                  'lay': lm.group(1) if lm else ''})
assert len(P) >= 500, 'parser matched only %d pads' % len(P)
print('%s: %d zones, %d pads\n' % (PCB, len(Z), len(P)))


def inside(pt, poly):
    x, y = pt
    n, c = len(poly), False
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def seg_dist(p, q, r, t):
    def d_pt_seg(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        u = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
        return math.hypot(px - (ax + u * dx), py - (ay + u * dy))
    return min(d_pt_seg(p[0], p[1], r[0], r[1], t[0], t[1]),
               d_pt_seg(q[0], q[1], r[0], r[1], t[0], t[1]),
               d_pt_seg(r[0], r[1], p[0], p[1], q[0], q[1]),
               d_pt_seg(t[0], t[1], p[0], p[1], q[0], q[1]))


def pad_to_poly(p, poly):
    """0 if the pad touches or is inside; otherwise the true edge gap."""
    x0, x1 = p['x'] - p['w'] / 2, p['x'] + p['w'] / 2
    y0, y1 = p['y'] - p['h'] / 2, p['y'] + p['h'] / 2
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if any(inside(c, poly) for c in corners) or inside((p['x'], p['y']), poly):
        return 0.0
    best = 1e9
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if inside(a, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]):
            return 0.0
        for j in range(4):
            best = min(best, seg_dist(corners[j], corners[(j + 1) % 4], a, b))
    return best


def enclosed(p, poly):
    x0, x1 = p['x'] - p['w'] / 2, p['x'] + p['w'] / 2
    y0, y1 = p['y'] - p['h'] / 2, p['y'] + p['h'] / 2
    return all(inside(c, poly) for c in
               [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def on_layer(lays, layer):
    return '"*.Cu"' in lays or ('"%s"' % layer) in lays


def dT(width_mm):
    if width_mm <= 0:
        return float('inf')
    A = width_mm * OZ2 * 1550.0031          # mm^2 -> mil^2
    k = 0.048 * (A ** 0.725)
    return (AMPS / k) ** (1 / 0.44)


def sustained_min(prof, span=0.5):
    """Smallest cut that persists for at least `span` mm of scan.

    A polygon with a slanted edge tapers to nothing at its corner, so the raw
    minimum finds a sliver that no current has to cross -- it sits in parallel
    with the rest of the conductor, not in series. Only a narrow section that
    holds for a real distance is a bottleneck.
    """
    keys = sorted(prof)
    best = None
    for i, k in enumerate(keys):
        v = prof[k]
        j, held = i, 0.0
        while j + 1 < len(keys) and prof[keys[j + 1]] <= v * 1.02:
            held += keys[j + 1] - keys[j]
            j += 1
        if held >= span and (best is None or v < best[1]):
            best = (k, v)
    return best or (keys[0], prof[keys[0]])


def runs(poly, axis):
    """Interior run lengths along each cut. axis 'h': widths per row."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    prof = {}
    if axis == 'h':
        a0, a1, b0, b1 = min(ys), max(ys), min(xs), max(xs)
    else:
        a0, a1, b0, b1 = min(xs), max(xs), min(ys), max(ys)
    a = a0 + STEP / 2
    while a < a1:
        tot, n = 0.0, 0
        b = b0 + STEP / 2
        while b < b1:
            pt = (b, a) if axis == 'h' else (a, b)
            if inside(pt, poly):
                tot += STEP
                n += 1
            b += STEP
        if n:
            prof[round(a, 3)] = tot
        a += STEP
    return prof


for net in NETS:
    zs = [z for z in Z if z['net'] == net]
    if not zs:
        print('%s: NO ZONE\n' % net)
        continue
    for z in zs:
        poly = z['pts']
        pop = [p for p in P if on_layer(p['lay'], z['layer'])]
        bonded = [p for p in pop if p['net'] == net and pad_to_poly(p, poly) == 0]
        foreign_in = [p for p in pop if p['net'] != net and pad_to_poly(p, poly) == 0]
        worst = None
        for p in pop:
            if p['net'] == net:
                continue
            g = pad_to_poly(p, poly)
            if worst is None or g < worst[0]:
                worst = (g, '%s.%s [%s]' % (p['ref'], p['pad'], p['net']))
        xs = [q[0] for q in poly]
        ys = [q[1] for q in poly]
        print('%-14s %-6s pri %-3d %d vertices   bbox %.1f x %.1f mm'
              % (z['name'], z['layer'], z['pri'], len(poly),
                 max(xs) - min(xs), max(ys) - min(ys)))
        print('   bonded        : %s' % (', '.join(
            '%s.%s' % (p['ref'], p['pad']) for p in bonded) or 'NOTHING'))
        if foreign_in:
            for p in foreign_in:
                tag = 'FULLY ENCLOSED' if enclosed(p, poly) else 'clipped by the outline'
                print('   *** FOREIGN   : %s.%s [%s] %s'
                      % (p['ref'], p['pad'], p['net'], tag))
        print('   clearance     : %.3f mm to %s%s'
              % (worst[0], worst[1], '' if worst[0] >= CLR else '   *** UNDER 0.30'))
        if z['layer'] == 'B.Cu':
            hp = runs(poly, 'h')
            vp = runs(poly, 'v')
            hmin = sustained_min(hp)[::-1]
            vmin = sustained_min(vp)[::-1]
            # A cut that lands on this net's own through-hole pads is measuring
            # the component lead, not a pour neck. A TO-220 pin is 1.9 mm wide
            # and no outline can widen it, so flagging it as under-width would
            # be noise that trains you to ignore the check.
            at_pad = any(p['net'] == net and 'thru' not in '' and
                         p['y'] - p['h'] / 2 - 0.5 <= hmin[1] <= p['y'] + p['h'] / 2 + 0.5
                         for p in bonded)
            note = ('   = the component leads themselves, not a pour neck' if at_pad
                    else ('' if hmin[0] >= TARGET_W
                          else '   *** under the %.1f mm this board sizes 30 A to' % TARGET_W))
            print('   narrowest horizontal cut (current down): %6.2f mm at y = %7.2f'
                  '   -> dT %3.0f C at 30 A%s'
                  % (hmin[0], hmin[1], dT(hmin[0]), note))
            print('   narrowest vertical cut   (current across): %6.2f mm at x = %7.2f'
                  '   -> dT %3.0f C at 30 A%s'
                  % (vmin[0], vmin[1], dT(vmin[0]),
                     '' if vmin[0] >= TARGET_W else '   *** under the %.1f mm this board sizes 30 A to' % TARGET_W))
        print()
