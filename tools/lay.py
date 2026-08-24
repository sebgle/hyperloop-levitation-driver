#!/usr/bin/env python3
"""
lay.py -- layout analysis for final_lev.kicad_pcb

Run from the folder containing final_lev.kicad_pcb:
    python3 lay.py

Parses the board into:
    F[ref] = {
        'x','y','ang' : footprint origin and rotation
        'pads'        : {padnum: ((abs_x, abs_y), netname_or_None)}
        'c'           : true courtyard bbox (xmin, xmax, ymin, ymax) on F.CrtYd,
                        including fp_circle (radial caps) -- NOT pad extents.
    }

WHY COURTYARDS, NOT PAD EXTENTS: checking pad extents alone once caused parts to be
declared "clear" when their courtyards overlapped badly (the Molex 38969-0002 courtyard
is 26.6 x 29.9 mm, far larger than its pads). Always check F.CrtYd.

KiCad transform used throughout:
    a = radians(-ang)
    out = (x + lx*cos(a) - ly*sin(a),  y + lx*sin(a) + ly*cos(a))

Net syntax note: pads carry (net "NAME") with no net number in this file.
"""
import re, math, sys, os

PCB = sys.argv[1] if len(sys.argv) > 1 else 'final_lev.kicad_pcb'
if not os.path.exists(PCB):
    sys.exit('cannot find %s -- run this from the project folder' % PCB)
# encoding is explicit: on Windows, open() defaults to the locale encoding (cp1252),
# which would throw or corrupt the moment a micro/ohm/degree sign appears in a field.
s = open(PCB, encoding='utf-8', errors='replace').read()

# ---------------------------------------------------------------- board outline
_r = re.search(r'\(gr_rect\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)'
               r'(?:.|\n)*?\(layer "Edge\.Cuts"\)', s)
if _r:
    OUTLINE = (min(float(_r.group(1)), float(_r.group(3))),
               max(float(_r.group(1)), float(_r.group(3))),
               min(float(_r.group(2)), float(_r.group(4))),
               max(float(_r.group(2)), float(_r.group(4))))
else:
    OUTLINE = (100.0, 260.0, 50.0, 190.0)

HEATSINK_FACE_Y = 58.6          # extrusion face; shadow covers x 122..243 above this

# ------------------------------------------------------- the pending leg swap
LEGB = 'D207 R224 R226 Q203 R229 C226 C230 U207 C229 D206 Q204 D208 R225 R227 R228 R231'.split()
LEGA = 'R213 R232 R215 R217 Q202 D204 D209 C228 U206 C227 C231 R212 Q201 R214 R216 D203'.split()
CERB = 'C219 C220 C221 C222 C223'.split()   # bridge ceramics riding with leg B
CERA = 'C212 C214 C215 C216 C217'.split()   # bridge ceramics riding with leg A
SHIFT = {r: -30.0 for r in LEGB + CERB}
SHIFT.update({r: 30.0 for r in LEGA + CERA})


def crt(blk, x, y, ang):
    """True courtyard bbox in board coords. Handles fp_line/poly/rect AND fp_circle."""
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


def parse(apply_swap=False):
    F = {}
    for m in re.finditer(r'\(footprint ((?:.|\n)*?)\n\t\)\n', s):
        b = m.group(0)
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        if not (at and rm):
            continue
        ref = rm.group(1)
        x, y = float(at.group(1)), float(at.group(2))
        ang = float(at.group(3) or 0)
        if apply_swap and ref in SHIFT:
            x += SHIFT[ref]
        fpn = re.match(r'\(footprint "([^"]+)"', b)
        pads = {}
        for pm in re.finditer(r'\(pad "([^"]+)"((?:.|\n)*?)\n\t\t\)', b):
            pn, pb = pm.group(1), pm.group(2)
            pa = re.search(r'\(at ([-\d.]+) ([-\d.]+)', pb)
            nt = re.search(r'\(net "([^"]+)"', pb)
            lx, ly = float(pa.group(1)), float(pa.group(2))
            a = math.radians(-ang)
            pads[pn] = ((x + lx * math.cos(a) - ly * math.sin(a),
                         y + lx * math.sin(a) + ly * math.cos(a)),
                        nt.group(1) if nt else None)
        F[ref] = {'x': x, 'y': y, 'ang': ang, 'pads': pads,
                  'c': crt(b, x, y, ang), 'fpn': fpn.group(1) if fpn else ''}
    return F


# ------------------------------------------------------------------- analyses
def overlaps(F):
    ks = [k for k in F if F[k]['c']]
    bad = []
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = F[ks[i]]['c'], F[ks[j]]['c']
            ox = min(a[1], b[1]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[2], b[2])
            if ox > 1e-6 and oy > 1e-6:
                bad.append((ks[i], ks[j], round(ox, 3), round(oy, 3)))
    return bad


def netmap(F):
    n = {}
    for r, d in F.items():
        for pn, (p, nm) in d['pads'].items():
            if nm:
                n.setdefault(nm, []).append((r, pn, p))
    return n


def span(pts):
    return max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in pts for b in pts) if len(pts) > 1 else 0.0


def dist_bbox_pt(c, px, py):
    dx = max(c[0] - px, 0, px - c[1])
    dy = max(c[2] - py, 0, py - c[3])
    return math.hypot(dx, dy)


def report(F, tag):
    print('=' * 62)
    print(tag, ' -- %d footprints, outline x[%g,%g] y[%g,%g]'
          % (len(F), OUTLINE[0], OUTLINE[1], OUTLINE[2], OUTLINE[3]))
    print('=' * 62)

    bad = overlaps(F)
    print('courtyard overlaps: %d' % len(bad))
    for t in bad[:25]:
        print('   %-6s %-6s  overlap %.3f x %.3f mm' % t)

    NM = netmap(F)
    print('\nswitching-node / coil net spans:')
    for net in ('/CH1/SW_A', '/CH2/SW_A', '/CH1/SW_B', '/CH2/SW_B',
                '/COIL_B1', '/COIL_B2', '/COIL_A1', '/COIL_A2'):
        if net in NM:
            print('  %-12s %6.1f mm   %s'
                  % (net, span([p for _, _, p in NM[net]]),
                     ' '.join('%s.%s' % (r, pn) for r, pn, _ in NM[net])))

    # Loop metric: two-segment path length, high-side drain pad -> ceramic +60V pad,
    # plus ceramic GND pad -> low-side source pad. NOT a closed loop perimeter, and not
    # comparable to figures quoted elsewhere under a different definition.
    print('\ncommutation loops (drain -> ceramic + ceramic -> source, two nearest ceramics):')
    cer = [r for r in F
           if F[r]['pads'].get('1') and F[r]['pads'].get('2')
           and F[r]['pads']['1'][1] == '+60V' and F[r]['pads']['2'][1] == 'GND'
           and abs(F[r]['y'] - 66) < 5]
    for leg, hi, lo in (('CH1 A', 'Q1', 'Q2'), ('CH1 B', 'Q3', 'Q4'),
                        ('CH2 A', 'Q201', 'Q202'), ('CH2 B', 'Q203', 'Q204')):
        if hi not in F or lo not in F:
            continue
        dp = F[hi]['pads']['2'][0]
        sp = F[lo]['pads']['3'][0]
        best = sorted((math.hypot(dp[0] - F[c]['pads']['1'][0][0], dp[1] - F[c]['pads']['1'][0][1])
                       + math.hypot(sp[0] - F[c]['pads']['2'][0][0], sp[1] - F[c]['pads']['2'][0][1]), c)
                      for c in cer)[:2]
        print('  %-7s %s' % (leg, '  '.join('%.1f mm (%s)' % (a, b) for a, b in best)))

    holes = {r: (F[r]['x'], F[r]['y']) for r in F if re.fullmatch(r'H\d+', r)}
    if holes:
        w = sorted((dist_bbox_pt(F[r]['c'], hx, hy), r, h)
                   for r in F if F[r]['c'] and not re.fullmatch(r'H\d+', r)
                   for h, (hx, hy) in holes.items())
        print('\nclosest footprint -> mounting hole:')
        for d, r, h in w[:5]:
            print('  %-6s -> %-3s %6.2f mm' % (r, h, d))

    eg = sorted((min(F[r]['c'][0] - OUTLINE[0], OUTLINE[1] - F[r]['c'][1],
                     F[r]['c'][2] - OUTLINE[2], OUTLINE[3] - F[r]['c'][3]), r)
                for r in F if F[r]['c'])
    print('\nclosest footprint -> board outline (negative = outside):')
    for d, r in eg[:5]:
        print('  %-6s %7.3f mm' % (r, d))

    hs = [(round(HEATSINK_FACE_Y - F[r]['c'][2], 2), r)
          for r in F if F[r]['c'] and F[r]['c'][2] < HEATSINK_FACE_Y
          and F[r]['c'][1] > 122 and F[r]['c'][0] < 243 and not re.fullmatch(r'H\d+', r)]
    print('\nheatsink-shadow intrusions (face at y=%.1f, x 122..243): %s'
          % (HEATSINK_FACE_Y, sorted(hs, reverse=True) or 'none'))


def leg_audit(F):
    """Confirm every leg-local net is fully contained in one moving block."""
    print('\n' + '=' * 62)
    print('LEG MEMBERSHIP AUDIT -- any net listed as SPANS-BOTH-LEGS or with an')
    print('unexpected "outside:" owner would break when the blocks move.')
    print('=' * 62)
    LA, LB = set(LEGA + CERA), set(LEGB + CERB)
    own = {}
    for r, d in F.items():
        for pn, (p, nm) in d['pads'].items():
            if nm:
                own.setdefault(nm, set()).add(r)
    for nm, o in sorted(own.items()):
        if not nm.startswith('/CH2/'):
            continue
        ina, inb, out = o & LA, o & LB, o - LA - LB
        if not (ina or inb):
            continue
        tag = []
        if ina and inb:
            tag.append('SPANS-BOTH-LEGS')
        if out:
            tag.append('outside:' + ','.join(sorted(out)))
        print('  %-18s A=%s B=%s %s' % (nm, sorted(ina), sorted(inb), ' '.join(tag)))


def window_check(F):
    """Verify the two selection windows catch exactly the intended footprints."""
    print('\n' + '=' * 62)
    print('SELECTION WINDOW CHECK (left-to-right drag = fully-enclosed only)')
    print('=' * 62)
    for nm, W, G in (('leg A', (183.0, 213.5, 57.5, 91.5), LEGA + CERA),
                     ('leg B', (213.6, 244.5, 57.5, 91.5), LEGB + CERB)):
        got = [r for r in F if F[r]['c']
               and F[r]['c'][0] >= W[0] and F[r]['c'][1] <= W[1]
               and F[r]['c'][2] >= W[2] and F[r]['c'][3] <= W[3]]
        print('  %s  window (%g,%g)-(%g,%g)  catches %d, expected %d'
              % (nm, W[0], W[2], W[1], W[3], len(got), len(G)))
        print('     extra:   %s' % (sorted(set(got) - set(G)) or 'none'))
        print('     missing: %s' % (sorted(set(G) - set(got)) or 'none'))


if __name__ == '__main__':
    B = parse(False)
    report(B, 'CURRENT BOARD')
    # The CH2 leg A/B swap was APPLIED 2026-08-22 (commit c9f1e50).
    # leg_audit() and window_check() described the board BEFORE that edit, and
    # parse(True) would shift the legs a SECOND time -- 26 courtyard overlaps
    # and parts 13 mm off the board. The SHIFT table and those functions are
    # kept as a record of the edit, but are no longer run.
    # See docs/20_layout_phase.md section 20.4.