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
        padinfo = {}
        for pm in re.finditer(r'\(pad "([^"]+)"((?:.|\n)*?)\n\t\t\)', b):
            pn, pb = pm.group(1), pm.group(2)
            pa = re.search(r'\(at ([-\d.]+) ([-\d.]+)', pb)
            nt = re.search(r'\(net "([^"]+)"', pb)
            lx, ly = float(pa.group(1)), float(pa.group(2))
            a = math.radians(-ang)
            pads[pn] = ((x + lx * math.cos(a) - ly * math.sin(a),
                         y + lx * math.sin(a) + ly * math.cos(a)),
                        nt.group(1) if nt else None)
            pt = re.search(r'\(pintype "([^"]+)"', pb)
            pf = re.search(r'\(pinfunction "([^"]+)"', pb)
            padinfo[pn] = {'pintype': pt.group(1) if pt else '',
                           'fn': pf.group(1) if pf else ''}
        vm = re.search(r'\(property "Value" "([^"]*)"', b)
        rt = re.search(r'\(property "Reference" "[^"]+"\s*\(at '
                       r'([-\d.]+) ([-\d.]+)', b)
        rtxy = None
        if rt:
            ra = math.radians(-ang)
            rlx, rly = float(rt.group(1)), float(rt.group(2))
            rtxy = (x + rlx * math.cos(ra) - rly * math.sin(ra),
                    y + rlx * math.sin(ra) + rly * math.cos(ra))
        F[ref] = {'x': x, 'y': y, 'ang': ang, 'pads': pads,
                  'padinfo': padinfo, 'val': vm.group(1) if vm else '',
                  'reftext': rtxy,
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




# =====================================================================
# PLACEMENT CHECKS -- added 2026-08-24
#
# WHY THESE EXIST: every check above is geometric (overlaps, loops,
# clearances) and all of them passed while two current-sense amplifiers
# sat 38 and 62 mm from their only bypass capacitor. A checker finds what
# somebody thought to check, so these encode the rest of the pre-routing
# review as measurements rather than memory.
#
# Thresholds are stated here, not implied. Change them here and every
# number in the project's documents moves with them.
# =====================================================================

DECOUPLE_OK = 3.0        # mm, IC supply pin to nearest capacitor on that rail
DECOUPLE_FAIL = 6.0
FILTER_OK = 5.0          # mm, filter capacitor to the pin it filters
FILTER_FAIL = 15.0
CHANNEL_SKEW = 1.0       # mm, tolerated CH1/CH2 mismatch on mirrored measurements
RAILS = ('+12V', '+5V', '+3.3V')

_R = []


def _say(sev, text):
    _R.append((sev, text))
    print('  %-5s %s' % (sev, text))


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def padlist(F):
    out = []
    for ref, d in F.items():
        for pn, (p, nm) in d['pads'].items():
            info = d.get('padinfo', {}).get(pn, {})
            out.append({'ref': ref, 'pad': pn, 'net': nm, 'xy': p,
                        'pintype': info.get('pintype', ''),
                        'fn': info.get('fn', '')})
    return out


def by_net(P):
    n = {}
    for p in P:
        if p['net']:
            n.setdefault(p['net'], []).append(p)
    return n


def nets_of(P, ref):
    return {p['net'] for p in P if p['ref'] == ref}


def check_decoupling(F, P, N):
    print('\ndecoupling -- IC supply pin to nearest capacitor on the same rail')
    worst = 0.0
    for p in P:
        if p['pintype'] != 'power_in' or p['net'] not in RAILS:
            continue
        cands = [q for q in N.get(p['net'], [])
                 if q['ref'].startswith('C') and 'GND' in nets_of(P, q['ref'])]
        if not cands:
            _say('FAIL', '%s.%s [%s] has no capacitor anywhere on its rail'
                 % (p['ref'], p['pad'], p['net']))
            continue
        b = min(cands, key=lambda q: _d(p['xy'], q['xy']))
        dist = _d(p['xy'], b['xy'])
        worst = max(worst, dist)
        sev = ('ok' if dist <= DECOUPLE_OK
               else 'warn' if dist < DECOUPLE_FAIL else 'FAIL')
        if sev != 'ok':
            _say(sev, '%s.%s [%s] nearest cap %s at %.2f mm'
                 % (p['ref'], p['pad'], p['net'], b['ref'], dist))
    print('  worst supply-pin distance %.2f mm   (ok <= %.1f, fail >= %.1f)'
          % (worst, DECOUPLE_OK, DECOUPLE_FAIL))


def check_filters(F, P, N):
    print('\nfilter capacitors -- cap to the nearest IC or connector pin it filters')
    print('  connector pins are graded strictly. Everything else is reported')
    print('  only: this check cannot tell an RF filter from an RC time constant')
    seen = set()
    for p in sorted(P, key=lambda q: q['ref']):
        if not p['ref'].startswith('C') or not p['net'] or p['net'] == 'GND':
            continue
        if p['ref'] in seen:
            continue
        nets = nets_of(P, p['ref'])
        if 'GND' not in nets or (nets & set(RAILS)) or '+60V' in nets:
            continue
        # Measure to the nearest IC or connector pin on the net, i.e. the
        # thing being filtered. Series resistors are expected to sit next to
        # the cap, and a net can legitimately span the board (/RESET reaches
        # both channels), so 'furthest pin on the net' gives false alarms.
        others = [q for q in N[p['net']] if q['ref'] != p['ref']
                  and (q['ref'][0] in 'UJ')]
        if not others:
            continue
        seen.add(p['ref'])
        far = min(others, key=lambda q: _d(p['xy'], q['xy']))
        dist = _d(p['xy'], far['xy'])
        strict = far['ref'].startswith('J')      # an I/O filter belongs at the pin
        if dist <= FILTER_OK:
            sev = 'ok'
        elif strict and dist >= FILTER_FAIL:
            sev = 'FAIL'
        else:
            sev = 'warn'
        if sev != 'ok':
            _say(sev, '%s on %s is %.2f mm from %s.%s%s'
                 % (p['ref'], p['net'], dist, far['ref'], far['pad'],
                    '  [connector]' if strict else ''))


def check_gate_paths(F, P, N):
    print('\ngate path -- driver output pin, series resistor, FET gate')
    res = {}
    for gnet in sorted(n for n in N if '/G_Q' in n):
        gp = [p for p in N[gnet] if p['ref'].startswith('Q')]
        rs = [p for p in N[gnet] if p['ref'].startswith('R')]
        if not (gp and rs):
            continue
        r = min(rs, key=lambda p: _d(p['xy'], gp[0]['xy']))
        seg2 = _d(r['xy'], gp[0]['xy'])
        seg1 = None
        for o in [q for q in P if q['ref'] == r['ref'] and q['pad'] != r['pad']]:
            drv = [q for q in N.get(o['net'], []) if q['ref'].startswith('U')]
            if drv:
                seg1 = min(_d(o['xy'], q['xy']) for q in drv)
        if seg1 is None:
            continue
        res[gnet] = seg1 + seg2
        print('  %-14s %5.2f mm' % (gnet, res[gnet]))
    _mirror(res, 'gate path')


def check_bootstrap(F, P, N):
    print('\nbootstrap capacitor to driver VB pin')
    res = {}
    for net in sorted(n for n in N if 'VB_' in n):
        cap = [p for p in N[net] if p['ref'].startswith('C')]
        drv = [p for p in N[net] if p['ref'].startswith('U')]
        if not (cap and drv):
            continue
        res[net] = min(_d(a['xy'], b['xy']) for a in cap for b in drv)
        print('  %-14s %5.2f mm' % (net, res[net]))
    _mirror(res, 'bootstrap')


def check_sense(F, P, N):
    print('\nshunt Kelvin pads to amplifier inputs')
    for ch, sh, amp in (('CH1', 'R11', 'U3'), ('CH2', 'R219', 'U203')):
        if sh not in F or amp not in F:
            continue
        try:
            pp = _d(F[sh]['pads']['2'][0], F[amp]['pads']['8'][0])
            nn = _d(F[sh]['pads']['3'][0], F[amp]['pads']['1'][0])
        except KeyError:
            continue
        print('  %s   P %6.2f mm   N %6.2f mm   mismatch %.2f mm'
              % (ch, pp, nn, abs(pp - nn)))


def check_hv_lv(F, P, N):
    print('\nclosest approach, 60 V nets to logic nets')
    hv = set(['+60V']) | set(n for n in N if 'SW_' in n or 'COIL_' in n
                             or 'VB_' in n)
    lv = set(n for n in N if n not in hv and n != 'GND')
    best = None
    for h in hv:
        for p in N[h]:
            for l in lv:
                for q in N[l]:
                    if q['ref'] == p['ref']:
                        continue      # pins inside one package: the vendor's problem
                    dd = _d(p['xy'], q['xy'])
                    if best is None or dd < best[0]:
                        best = (dd, '%s.%s[%s]' % (p['ref'], p['pad'], h),
                                '%s.%s[%s]' % (q['ref'], q['pad'], l))
    if best:
        print('  %.2f mm   %s  <->  %s' % best)
        if best[0] < 0.6:
            _say('FAIL', 'below the IPC-2221 uncoated minimum of 0.6 mm at 51-100 V')


def check_silk(F):
    print('\nsilkscreen reference designator collisions')
    T = [(r, d['reftext'][0], d['reftext'][1], len(r) * 0.75, 1.0)
         for r, d in F.items() if d.get('reftext')]
    n = 0
    for i in range(len(T)):
        for j in range(i + 1, len(T)):
            a, b = T[i], T[j]
            if (abs(a[1] - b[1]) < (a[3] + b[3]) / 2
                    and abs(a[2] - b[2]) < (a[4] + b[4]) / 2):
                n += 1
                if n <= 6:
                    _say('warn', '%s and %s reference text overlap' % (a[0], b[0]))
    print('  overlapping pairs: %d' % n)


def check_pad_orientation():
    """Pads must be turned the same way as the footprint they belong to.

    A pad's (at x y angle) in this file is the pad's ABSOLUTE angle, so a body
    rotated to 90 normally has its pads written at 90. The quantity that must
    hold constant is the DIFFERENCE, pad angle minus body angle, because some
    library footprints legitimately define a pad already turned: KiCad's
    Diode_SMD:D_SMC_Handsoldering declares its pads 90 off its own outline, and
    D2 and D205 inherit that honestly.

    So the baseline is not zero, it is whatever the other placements of the same
    library footprint use. A script that rewrites a footprint's (at) line and
    leaves the pads behind shows up as one instance disagreeing with its own
    library id. That is exactly how C1, C20, C227, C213 and C239 were found:
    5 parts turned 90 out of a population that was otherwise 0.

    Off by 180 a rectangle is unchanged, so that is graded a warning. Off by 90
    the pad's length and width swap and the copper stops matching the part's
    terminations, which is a fabrication defect. No DRC on this board reported
    either one.
    """
    print('\npad rotation vs footprint rotation')

    def n(a):
        return round(((a % 360) + 360) % 360, 3)

    seen = {}
    for m in re.finditer(r'\(footprint ((?:.|\n)*?)\n\t\)\n', s):
        b = m.group(0)
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b)
        fp = re.match(r'\(footprint "([^"]+)"', b)
        if not (rm and at and fp):
            continue
        fa = n(float(at.group(3) or 0))
        for pm in re.finditer(r'\(pad "([^"]+)" \w+ [\w_]+\n\t\t\t'
                              r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\n\t\t\t'
                              r'\(size ([\d.]+) ([\d.]+)\)', b):
            key = (fp.group(1), pm.group(1))
            rel = n(float(pm.group(4) or 0) - fa)
            seen.setdefault(key, []).append(
                (rm.group(1), fa, rel, float(pm.group(5)), float(pm.group(6))))

    odd = {}
    for key, rows in seen.items():
        counts = {}
        for _, _, rel, _, _ in rows:
            counts[rel] = counts.get(rel, 0) + 1
        base = max(counts, key=lambda r: (counts[r], -r))
        if counts[base] == len(rows):
            continue
        for ref, fa, rel, sw, sh in rows:
            if rel == base:
                continue
            off = n(rel - base)
            square = abs(sw - sh) < 1e-9
            sev = 2 if (off in (90.0, 270.0) and not square) else 1
            prev = odd.get(ref)
            if prev is None or sev > prev[0]:
                odd[ref] = (sev, fa, off, sw, sh, key[0], base, counts[base], len(rows))

    for ref in sorted(odd, key=lambda r: (-odd[r][0], r)):
        sev, fa, off, sw, sh, fpn, base, nbase, ntot = odd[ref]
        where = ('%s, %d of %d placements sit at %g'
                 % (fpn.split(':')[-1], nbase, ntot, base))
        if sev == 2:
            _say('FAIL', '%s body at %g deg has pads %g deg off its own library '
                         'baseline: the %.3f x %.3f mm pad is turned across the '
                         'part instead of along it (%s)'
                 % (ref, fa, off, sw, sh, where))
        else:
            _say('warn', '%s body at %g deg has pads %g deg off its own library '
                         'baseline. Same rectangle, so shape is unaffected (%s)'
                 % (ref, fa, off, where))
    if not odd:
        print('  every footprint agrees with the other placements of its own '
              'library footprint. 0 mismatched')


def _poly_in(pt, poly):
    x, y = pt
    n, c = len(poly), False
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def _cells(z, step=0.25):
    """Rasterised interior of a zone, memoised. Bounding boxes lie about L shapes."""
    if 'cells' not in z:
        xs = [p[0] for p in z['pts']]
        ys = [p[1] for p in z['pts']]
        S = set()
        y = min(ys) + step / 2
        while y < max(ys):
            x = min(xs) + step / 2
            while x < max(xs):
                if _poly_in((x, y), z['pts']):
                    S.add((round(x, 2), round(y, 2)))
                x += step
            y += step
        z['cells'] = S
    return z['cells']


def check_zones():
    """Overlapping copper zones need distinct priorities, same net or not.

    KiCad raises zones_intersect for any two zones that overlap on a layer and
    share a priority. This checker reported 0 FAIL on a board carrying four of
    them, because it had nothing to say about zones at all. Now it does.

    Blocks are found by counting brackets, not by a lazy regex: '\n\t)' appears
    inside a zone at the end of connect_pads, so a non-greedy match ends the
    block early and silently loses zones. That mistake has cost this project
    three wrong answers already.

    Overlap is tested by rasterising both outlines at 0.25 mm, not by comparing
    bounding boxes. The +60 V plane on In2.Cu is L-shaped -- a body plus a finger
    reaching down to J101 -- and its bounding box overlaps both GND fills beside
    it while the copper does not touch them anywhere. A box test called that a
    collision twice. A checker that cries wolf is one you learn to skip.
    """
    print('\nzone overlap and priority')
    lines = s.split('\n')
    Z, start, depth = [], None, 0
    for i, ln in enumerate(lines):
        if start is None and ln.startswith('\t(zone'):
            start, depth = i, 0
        if start is not None:
            depth += ln.count('(') - ln.count(')')
            if depth <= 0 and i >= start:
                b = '\n'.join(lines[start:i + 1])
                nm = re.search(r'\(name "([^"]*)"', b)
                ly = re.search(r'\(layer "([^"]*)"', b)
                nt = re.search(r'\(net "([^"]*)"', b)
                pr = re.search(r'\(priority (\d+)\)', b)
                pm = re.search(r'\(polygon\n\t\t\t\(pts\n((?:.|\n)*?)\n\t\t\t\)', b)
                pts = re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', pm.group(1)) if pm else []
                if pts:
                    pts_f = [(float(a), float(c)) for a, c in pts]
                    xs = [float(a) for a, _ in pts]
                    ys = [float(c) for _, c in pts]
                    Z.append({'pts': pts_f, 'name': nm.group(1) if nm else '?',
                              'layer': ly.group(1) if ly else '?',
                              'net': nt.group(1) if nt else '?',
                              'pri': int(pr.group(1)) if pr else 0,
                              'bb': (min(xs), max(xs), min(ys), max(ys))})
                start = None
    if not Z:
        _say('FAIL', 'no zones parsed. The board has copper pours, so this is a '
                     'parser failure, not an empty board')
        return
    for z in sorted(Z, key=lambda z: (z['layer'], z['name'])):
        print('  %-14s %-7s %-10s priority %d   %.1f x %.1f mm'
              % (z['name'], z['layer'], z['net'], z['pri'],
                 z['bb'][1] - z['bb'][0], z['bb'][3] - z['bb'][2]))
    n = 0
    for i in range(len(Z)):
        for j in range(i + 1, len(Z)):
            a, b = Z[i], Z[j]
            if a['layer'] != b['layer']:
                continue
            if not (min(a['bb'][1], b['bb'][1]) - max(a['bb'][0], b['bb'][0]) > 1e-9
                    and min(a['bb'][3], b['bb'][3]) - max(a['bb'][2], b['bb'][2]) > 1e-9):
                continue
            if not _cells(a) & _cells(b):
                continue
            if a['pri'] == b['pri']:
                n += 1
                _say('FAIL', '%s and %s overlap on %s and both sit at priority %d. '
                             'KiCad calls this zones_intersect'
                     % (a['name'], b['name'], a['layer'], a['pri']))
    print('  %d zones, %d same-priority overlaps' % (len(Z), n))


def check_testpoints(F):
    print('\ntest points')
    tp = [r for r, d in F.items() if 'TestPoint' in d['fpn'] or r.startswith('TP')]
    if tp:
        print('  %d found: %s' % (len(tp), ' '.join(sorted(tp))))
    else:
        _say('FAIL', 'no test points. A 60 V / 30 A prototype needs somewhere '
                     'to put a probe, and adding them after routing means '
                     'ripping up copper')


def _mirror(res, label):
    """CH1 and CH2 are mirrored, so matching measurements should agree."""
    pairs = {}
    for k, v in res.items():
        key = k.replace('/CH1/', '').replace('/CH2/', '')
        pairs.setdefault(key, {})['CH1' if '/CH1/' in k else 'CH2'] = v
    for k, v in sorted(pairs.items()):
        if len(v) == 2 and abs(v['CH1'] - v['CH2']) > CHANNEL_SKEW:
            _say('warn', '%s %s differs between channels: %.2f vs %.2f mm'
                 % (label, k, v['CH1'], v['CH2']))


def checks(F):
    print('\n' + '=' * 62)
    print('PLACEMENT CHECKS')
    print('=' * 62)
    del _R[:]
    P = padlist(F)
    N = by_net(P)
    check_decoupling(F, P, N)
    check_filters(F, P, N)
    check_gate_paths(F, P, N)
    check_bootstrap(F, P, N)
    check_sense(F, P, N)
    check_hv_lv(F, P, N)
    check_silk(F)
    check_pad_orientation()
    check_zones()
    check_testpoints(F)
    fails = sum(1 for s, _ in _R if s == 'FAIL')
    warns = sum(1 for s, _ in _R if s == 'warn')
    print('\n' + '-' * 62)
    print('PLACEMENT CHECKS: %d FAIL, %d warn' % (fails, warns))
    print('-' * 62)
    return fails

if __name__ == '__main__':
    B = parse(False)
    report(B, 'CURRENT BOARD')
    checks(B)
    # The CH2 leg A/B swap was APPLIED 2026-08-22 (commit c9f1e50).
    # leg_audit() and window_check() described the board BEFORE that edit, and
    # parse(True) would shift the legs a SECOND time -- 26 courtyard overlaps
    # and parts 13 mm off the board. The SHIFT table and those functions are
    # kept as a record of the edit, but are no longer run.
    # See docs/20_layout_phase.md section 20.4.