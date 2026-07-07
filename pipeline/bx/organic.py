"""bx.organic — générateurs de parties anatomiques pilotés par spec JSON + lois GVL.
Chaque builder consomme un dict compact et retourne des objets Blender. Généraliste :
un dragon, un arbre ou un poisson ne diffèrent que par leur spec."""
import math

from mathutils import Euler, Vector

from gvl import laws, apply_law
from . import core, ops, materials

BUILDERS = {}


def builder(name):
    def reg(fn):
        BUILDERS[name] = fn
        return fn
    return reg


def _mat(mats, key):
    return mats.get(key)


@builder('spine')
def spine(part, mats):
    """Corps principal : tube conique + crête dorsale double rangée, pointes courbées vers l'arrière."""
    pts = [tuple(p) for p in part['pts']]
    radii = part['radii']
    body = ops.tube(part.get('id', 'spine'), pts, radii)
    materials.assign(body, _mat(mats, part.get('mat', 'scales')))
    out = [body]
    sp = part.get('spikes')
    if sp:
        n = sp.get('n', 20)
        path = laws.lerp_path(pts, n)
        rads = laws.lerp_path([(r, 0, 0) for r in radii], n)
        i0 = sp.get('skip', 2)
        for i in range(i0, n - 1):
            p, r = path[i], rads[i][0]
            nxt = path[i + 1]
            dy, dz = nxt[1] - p[1], nxt[2] - p[2]
            d = math.hypot(dy, dz) or 1e-3
            uy, uz = dy / d, dz / d          # tangente avant
            vy, vz = -uz, uy                 # normale « dessus »
            t = i / (n - 1)
            env = math.sin(math.pi * t) ** 0.6 * min(1.0, r * 2.0 + 0.3)
            for row, sx in ((0, 1.0), (1, -1.0)):
                jit = 1.0 + 0.30 * math.sin(i * 7.3 + row * 2.6)
                h = max(0.07, sp.get('h0', 0.65) * env * jit * (1.0 if row == 0 else 0.85))
                bx = p[0] + sx * 0.07 * r
                by, bz = p[1], p[2] + r * 0.92
                s_pts = [(bx, by, bz),
                         (bx, by + vy * h * 0.55 - uy * h * 0.16, bz + vz * h * 0.55 - uz * h * 0.16),
                         (bx, by + vy * h * 0.92 - uy * h * 0.50, bz + vz * h * 0.92 - uz * h * 0.50)]
                s = ops.tube(f'dorsal_{i}_{row}', s_pts, [h * 0.22, h * 0.12, 0.008])
                materials.assign(s, _mat(mats, sp.get('mat', 'bone')))
                out.append(s)
    return out


@builder('head')
def head(part, mats):
    """Tête loftée par sections superellipse (GVL) : crâne→museau continu, mâchoire
    inférieure articulée ouverte de `gape`°, dents courbes, yeux sous arcades,
    narines, couronne de cornes en spirale log."""
    L = Vector(part['loc'])
    pitch = part.get('pitch', -8.0)
    gape = part.get('gape', 26.0)
    exp = part.get('exp', 1.7)
    skin = _mat(mats, part.get('mat', 'scales'))
    hp = part.get('horns', {})
    bone_m = _mat(mats, hp.get('mat', 'bone'))
    tooth_m = _mat(mats, 'teeth') or bone_m
    Rp = Euler((math.radians(pitch), 0, 0)).to_matrix()
    Rj = Euler((math.radians(-gape), 0, 0)).to_matrix()
    out = []

    def W(p):
        v = Rp @ Vector(p)
        return (L.x + v.x, L.y + v.y, L.z + v.z)

    def WJ(p):
        """repère mâchoire inférieure (pivot arrière, ouverte de gape°) → monde."""
        return W(Rj @ Vector(p))

    def interp_w(secs, y):
        for (y0, w0, _), (y1, w1, _) in zip(secs, secs[1:]):
            if y0 <= y <= y1:
                f = (y - y0) / (y1 - y0)
                return w0 + f * (w1 - w0)
        return secs[-1][1]

    # --- crâne + museau : sections (y, demi-largeur, demi-hauteur), gueule plate z≈0 ---
    upper = part.get('upper', [[-0.05, 0.26, 0.21], [0.20, 0.31, 0.24], [0.45, 0.27, 0.19],
                               [0.70, 0.21, 0.13], [0.95, 0.155, 0.09], [1.18, 0.10, 0.055]])
    lower = part.get('lower', [[0.00, 0.20, 0.090], [0.30, 0.185, 0.075], [0.60, 0.155, 0.060],
                               [0.90, 0.115, 0.048], [1.06, 0.075, 0.038]])
    rings = [[W((x, y, z + hh * 0.82)) for x, z in laws.superellipse(w, hh, exp)]
             for y, w, hh in upper]
    sk = ops.ring_loft('skull', rings)
    materials.assign(sk, skin)
    out.append(sk)
    rings = [[WJ((x, y, z - hh * 0.85)) for x, z in laws.superellipse(w, hh, exp)]
             for y, w, hh in lower]
    jw = ops.ring_loft('jaw', rings)
    materials.assign(jw, skin)
    out.append(jw)

    # --- dents : tubes effilés courbes le long des bords de gueule ---
    for i in range(6):
        y = 0.42 + i * 0.13
        w = interp_w(upper, y) * 0.78
        l = (0.07 + 0.012 * i + (0.03 if i == 4 else 0)) * (1 + 0.15 * math.sin(i * 9.1))
        for s, tag in ((1, 'l'), (-1, 'r')):
            x = s * w
            t = ops.tube(f'tooth_u{tag}{i}',
                         [W((x, y, -0.005)), W((x * 0.97, y + 0.015, -l * 0.55)), W((x * 0.92, y + 0.03, -l))],
                         [0.020, 0.012, 0.003])
            materials.assign(t, tooth_m)
            out.append(t)
    for i in range(5):
        y = 0.35 + i * 0.16
        w = interp_w(lower, y) * 0.75
        l = (0.06 + 0.010 * i) * (1 + 0.15 * math.sin(i * 7.7 + 1.3))
        for s, tag in ((1, 'l'), (-1, 'r')):
            x = s * w
            t = ops.tube(f'tooth_l{tag}{i}',
                         [WJ((x, y, 0.005)), WJ((x * 0.97, y + 0.015, l * 0.55)), WJ((x * 0.92, y + 0.03, l))],
                         [0.018, 0.011, 0.003])
            materials.assign(t, tooth_m)
            out.append(t)

    # --- yeux enfoncés sous arcades + narines ---
    for s, tag in ((1, 'l'), (-1, 'r')):
        e = ops.blob(f'eye_{tag}', W((s * 0.245, 0.30, 0.135)), (0.05, 0.05, 0.05))
        materials.assign(e, _mat(mats, 'eye'))
        out.append(e)
        n = ops.blob(f'nostril_{tag}', W((s * 0.065, 1.10, 0.075)), (0.020, 0.030, 0.016))
        materials.assign(n, _mat(mats, 'eye'))
        out.append(n)

    # --- couronne de cornes : spirale log GVL, série décroissante, éventail arrière ---
    pairs = hp.get('pairs', 5)
    sizes = laws.decay_series(pairs, base=1.0, ratio=hp.get('ratio', 0.78))
    raw = apply_law(hp.get('vocab', 'growth.horn_spiral'),
                    n=16, a=hp.get('a', 0.10), b=hp.get('b', 0.30),
                    turns=hp.get('turns', 0.6), rise=hp.get('rise', 0.55))
    base_radii = laws.power_taper(16, hp.get('r0', 0.075), 1.15, 0.008)
    for k in range(pairs):
        u = k / max(1, pairs - 1)
        sc = sizes[k]
        radii = [r * (0.5 + 0.5 * sc) for r in base_radii]
        yaw = 8 + u * 55
        hpitch = hp.get('pitch', -35) - u * 15
        base = (0.09 + 0.15 * u, 0.05 - 0.22 * u, 0.34 - 0.12 * u)
        for s, tag in ((1, 'l'), (-1, 'r')):
            pts = ops.transform_pts(raw, loc=W((s * base[0], base[1], base[2])),
                                    rot_deg=(pitch + hpitch, 0, s * yaw),
                                    scale=sc * hp.get('scale', 1.0))
            h = ops.tube(f'horn_{tag}{k}', pts, radii)
            materials.assign(h, bone_m)
            out.append(h)
    # petites cornes d'arcade + pointes de joue
    for s, tag in ((1, 'l'), (-1, 'r')):
        b = ops.spike(f'horn_brow_{tag}', W((s * 0.22, 0.38, 0.26)), 0.14, 0.035,
                      (pitch - 35, 0, s * 15))
        materials.assign(b, bone_m)
        out.append(b)
        c = ops.spike(f'horn_cheek_{tag}', W((s * 0.30, 0.12, -0.02)), 0.16, 0.045,
                      (pitch + 95, 0, s * 55))
        materials.assign(c, bone_m)
        out.append(c)
    return out


@builder('wing')
def wing(part, mats):
    """Aile de wyverne : bras + doigts osseux en éventail, membrane à affaissement caténaire."""
    out = []
    sides = [1, -1] if part.get('side', 'both') == 'both' else [1]
    sag = part.get('sag', 0.55)
    nt = part.get('samples', 9)
    sub = part.get('columns_between', 4)
    for s in sides:
        tag = 'L' if s > 0 else 'R'
        sh = (s * part['shoulder'][0], part['shoulder'][1], part['shoulder'][2])
        el = (s * part['elbow'][0], part['elbow'][1], part['elbow'][2])
        wr = (s * part['wrist'][0], part['wrist'][1], part['wrist'][2])
        arm = ops.tube(f'arm_{tag}', [sh, el, wr], [0.22, 0.16, 0.12])
        materials.assign(arm, _mat(mats, part.get('bone_mat', 'scales')))
        out.append(arm)
        rays = [tuple((s * p[0], p[1], p[2])) for p in part['tips']]
        anchor = (s * part['anchor'][0], part['anchor'][1], part['anchor'][2])
        cols = []
        ends = rays + [anchor]
        W = Vector(wr)
        for j in range(len(ends) - 1):
            a, b = Vector(ends[j]), Vector(ends[j + 1])
            steps = sub if j < len(ends) - 2 else sub + 2
            for k in range(steps):
                u = k / steps
                e = a.lerp(b, u)
                col = []
                for i in range(nt):
                    t = i / (nt - 1)
                    v = W.lerp(e, t)
                    v.z -= sag * math.sin(math.pi * u) * t
                    col.append(tuple(v))
                cols.append(col)
        cols.append([tuple(W.lerp(Vector(anchor), i / (nt - 1))) for i in range(nt)])
        mem = ops.grid_surface(f'membrane_{tag}', cols)
        core.solidify(mem, 0.025)
        materials.assign(mem, _mat(mats, part.get('mat', 'membrane')))
        out.append(mem)
        fr = laws.power_taper(nt, 0.085, 1.1, 0.015)
        for j, tip in enumerate(rays):
            fpts = [tuple(W.lerp(Vector(tip), i / (nt - 1))) for i in range(nt)]
            f = ops.tube(f'finger_{tag}{j}', fpts, fr)
            materials.assign(f, _mat(mats, part.get('bone_mat', 'scales')))
            out.append(f)
            claw = ops.spike(f'wclaw_{tag}{j}', tip, 0.22, 0.05, (150, 0, 0))
            materials.assign(claw, _mat(mats, 'bone'))
            out.append(claw)
    return out


@builder('limb')
def limb(part, mats):
    """Patte : tube conique articulé + pied à 3 orteils griffus."""
    out = []
    sides = [1, -1] if part.get('side', 'both') == 'both' else [1]
    for s in sides:
        tag = 'L' if s > 0 else 'R'
        pts = [(s * p[0], p[1], p[2]) for p in part['pts']]
        radii = part.get('radii') or laws.power_taper(len(pts), part.get('r0', 0.3), 1.0, 0.1)
        leg = ops.tube(f"{part.get('id', 'leg')}_{tag}", pts, radii)
        materials.assign(leg, _mat(mats, part.get('mat', 'scales')))
        out.append(leg)
        if part.get('foot'):
            f = part['foot']
            ax, ay, az = s * f['loc'][0], f['loc'][1], f['loc'][2]
            pad = ops.blob(f'footpad_{tag}', (ax, ay, az + 0.02), (0.15, 0.19, 0.10))
            materials.assign(pad, _mat(mats, part.get('mat', 'scales')))
            out.append(pad)
            for k, ang in enumerate((-26, 0, 26)):
                ra = math.radians(ang)
                dx, dy = math.sin(ra), math.cos(ra)
                toe = ops.tube(f'toe_{tag}{k}',
                               [(ax, ay - 0.04, az + 0.06),
                                (ax + dx * 0.20, ay + dy * 0.20, 0.085),
                                (ax + dx * 0.40, ay + dy * 0.40, 0.055)],
                               [0.105, 0.075, 0.042])
                materials.assign(toe, _mat(mats, part.get('mat', 'scales')))
                out.append(toe)
                tip = (ax + dx * 0.40, ay + dy * 0.40, 0.055)
                claw = ops.tube(f'claw_{tag}{k}',
                                [tip, (tip[0] + dx * 0.08, tip[1] + dy * 0.08, 0.035),
                                 (tip[0] + dx * 0.14, tip[1] + dy * 0.14, 0.004)],
                                [0.035, 0.020, 0.004])
                materials.assign(claw, _mat(mats, 'bone'))
                out.append(claw)
    return out


@builder('ground')
def ground(part, mats):
    g = ops.plane('ground', part.get('size', 80))
    materials.assign(g, _mat(mats, part.get('mat', 'rock')))
    return [g]


def _apply_fuse_detail(spec, groups):
    """Étapes post-assemblage validées (research/convergence.md) : fusion voxel du corps
    puis détail (displace + écailles). Optionnelles, pilotées par la spec.
    `groups` : id de part -> liste d'objets créés."""
    from . import fuse as _fuse, detail as _detail
    fspec = spec.get('fuse')
    if not fspec:
        return None
    objs = [o for n in fspec.get('parts', []) for o in groups.get(n, [])]
    if not objs:
        return None
    body = _fuse.voxel_fuse(objs, target_res=fspec.get('target_res', 200),
                            smooth_iters=fspec.get('smooth_iters', 5),
                            smooth_lambda=fspec.get('smooth_lambda', 0.5),
                            name=fspec.get('name', 'body'))
    if fspec.get('mat'):
        materials.assign(body, spec.get('_mats', {}).get(fspec['mat']))
    d = spec.get('detail', {})
    if d.get('displace'):
        _detail.displace_layers(body, d['displace'], subdiv=d.get('subdiv', 1))
    if d.get('scales'):
        sc = d['scales']
        plate = _detail.scale_plate(size=sc.get('plate_size', 1.0))
        _detail.scales(body, plate, density=sc.get('density', 120.0),
                       scale=tuple(sc.get('scale', (0.05, 0.12))),
                       curvature=sc.get('curvature', True))
    return body


def build(spec):
    """Point d'entrée : spec dict → scène complète. Retourne le nombre d'objets."""
    core.reset()
    mats = {}
    for key, m in spec.get('materials', {}).items():
        mats[key] = getattr(materials, m['builder'])(name=key, **m.get('p', {}))
    spec['_mats'] = mats
    count = 0
    groups = {}
    for i, part in enumerate(spec['parts']):
        objs = BUILDERS[part['type']](part, mats)
        groups[part.get('id') or f"{part['type']}_{i}"] = objs
        count += len(objs)
    _apply_fuse_detail(spec, groups)
    sc = spec.get('scene', {})
    core.world(**sc.get('world', {}))
    core.sun(**sc.get('sun', {}))
    for al in sc.get('area_lights', []):
        core.area_light(**al)
    core.camera(**sc.get('camera', {'loc': (9, -11, 3.5), 'target': (0, 0, 2), 'lens': 40}))
    return count
