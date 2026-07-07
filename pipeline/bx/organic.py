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
    """Tête prédateur : crâne allongé anguleux (+Y = avant), gueule ouverte rugissante
    avec dents, arcades marquées, couronne de cornes en spirale log, yeux enfoncés."""
    L = Vector(part['loc'])
    pitch = part.get('pitch', -6.0)
    skin = _mat(mats, part.get('mat', 'scales'))
    bone = _mat(mats, part.get('horns', {}).get('mat', 'bone'))
    Rp = Euler((math.radians(pitch), 0, 0)).to_matrix()
    out = []

    def W(p):
        """point local tête → monde (inclinaison du crâne incluse)."""
        v = Rp @ Vector(p)
        return (L.x + v.x, L.y + v.y, L.z + v.z)

    def R(rx=0.0, ry=0.0, rz=0.0):
        return (pitch + rx, ry, rz)

    def add_blob(nm, off, sc, rot=(0, 0, 0), mat=None):
        b = ops.blob(nm, W(off), sc, R(*rot))
        materials.assign(b, mat or skin)
        out.append(b)

    sk = part.get('skull', [0.30, 0.68, 0.30])
    sn = part.get('snout', [0.17, 0.60, 0.13])
    sno = part.get('snout_off', [0, 0.72, 0.03])
    jw = part.get('jaw', [0.14, 0.55, 0.085])
    gape = part.get('gape', 32.0)
    hinge = Vector(part.get('hinge', [0, -0.28, -0.15]))
    Rj = Euler((math.radians(-gape), 0, 0)).to_matrix()

    def J(p):
        """repère mâchoire inférieure (pivot arrière crâne, ouverte de `gape`°) → local tête."""
        return tuple(hinge + Rj @ Vector(p))

    # --- crâne très allongé + museau effilé dans son prolongement ---
    add_blob('skull', (0, 0, 0), sk)
    add_blob('skull_ridge', (0, -0.02, sk[2] * 0.70), (sk[0] * 0.5, sk[1] * 0.82, sk[2] * 0.34), (-4, 0, 0))
    add_blob('snout', tuple(sno), sn, (2, 0, 0))
    add_blob('snout_ridge', (sno[0], sno[1] + 0.04, sno[2] + sn[2] * 0.55),
             (sn[0] * 0.52, sn[1] * 0.80, sn[2] * 0.42), (2, 0, 0))
    for s, tag in ((1, 'l'), (-1, 'r')):
        add_blob(f'cheek_{tag}', (s * sk[0] * 0.66, -0.10, -sk[2] * 0.22),
                 (0.10, sk[1] * 0.52, 0.13), (0, 0, -s * 10))
        add_blob(f'brow_{tag}', (s * 0.16, 0.30, sk[2] * 0.62),
                 (0.125, 0.30, 0.05), (-8, -s * 16, -s * 12))

    # --- mâchoire inférieure ouverte + intérieur de gueule sombre ---
    add_blob('jaw_base', J((0, 0.10, 0.01)), (jw[0] * 0.9, 0.22, jw[2] * 1.2), (-gape, 0, 0))
    add_blob('jaw', J((0, 0.60, 0.0)), jw, (-gape, 0, 0))
    add_blob('jaw_tip', J((0, 0.60 + jw[1] * 0.72, 0.02)),
             (jw[0] * 0.6, jw[1] * 0.35, jw[2] * 0.8), (-gape, 0, 0))
    Rm = Euler((math.radians(-gape * 0.45), 0, 0)).to_matrix()
    add_blob('mouth', tuple(hinge + Rm @ Vector((0, 0.48, 0.0))),
             (jw[0] * 0.68, 0.42, 0.04), (-gape * 0.45, 0, 0), _mat(mats, 'mouth') or skin)

    # --- dents : rangées de spikes fins le long des deux mâchoires ---
    tp = part.get('teeth', {})
    tooth_mat = _mat(mats, tp.get('mat', 'teeth')) or bone
    nu, nl = tp.get('upper', 6), tp.get('lower', 5)
    y0, y1 = sno[1] - sn[1] * 0.40, sno[1] + sn[1] * 0.90
    for i in range(nu):
        t = (i + 0.5) / nu
        y = y0 + t * (y1 - y0)
        f = math.sqrt(max(0.08, 1 - ((y - sno[1]) / sn[1]) ** 2))
        h = (0.055 + 0.06 * t) * (1 + 0.18 * math.sin(i * 9.1))
        for s, tag in ((1, 'l'), (-1, 'r')):
            tth = ops.spike(f'tooth_u{tag}{i}', W((s * sn[0] * 0.72 * f, y, sno[2] - sn[2] * 0.80 * f - h * 0.18)),
                            h, h * 0.20, R(180))
            materials.assign(tth, tooth_mat)
            out.append(tth)
    jy0, jy1 = 0.60 - jw[1] * 0.30, 0.60 + jw[1] * 0.85
    for i in range(nl):
        t = (i + 0.5) / nl
        y = jy0 + t * (jy1 - jy0)
        f = math.sqrt(max(0.08, 1 - ((y - 0.60) / jw[1]) ** 2))
        h = (0.05 + 0.055 * t) * (1 + 0.18 * math.sin(i * 7.7 + 1.3))
        for s, tag in ((1, 'l'), (-1, 'r')):
            tth = ops.spike(f'tooth_l{tag}{i}', W(J((s * jw[0] * 0.72 * f, y, jw[2] * 0.72 * f + h * 0.18))),
                            h, h * 0.20, R(-gape))
            materials.assign(tth, tooth_mat)
            out.append(tth)

    # --- couronne de cornes : spirale log GVL, tailles en série décroissante, éventail symétrique ---
    hp = part.get('horns', {})
    pairs = hp.get('pairs', 5)
    sizes = laws.decay_series(pairs, base=1.0, ratio=hp.get('ratio', 0.8))
    raw = apply_law(hp.get('vocab', 'growth.horn_spiral'),
                    n=16, a=hp.get('a', 0.10), b=hp.get('b', 0.30),
                    turns=hp.get('turns', 0.6), rise=hp.get('rise', 0.55))
    base_radii = laws.power_taper(16, hp.get('r0', 0.08), 1.15, 0.008)
    for k in range(pairs):
        u = k / max(1, pairs - 1)
        sc = sizes[k]
        radii = [r * (0.5 + 0.5 * sc) for r in base_radii]
        yaw = hp.get('yaw0', 10) + u * hp.get('yaw_span', 62)
        hpitch = hp.get('pitch', 115) + u * 10
        bx, by, bz = 0.10 + 0.20 * u, -sk[1] * 0.72 + 0.15 * u, sk[2] * (0.55 - 0.90 * u)
        for s, tag in ((1, 'l'), (-1, 'r')):
            pts = ops.transform_pts(raw, loc=W((s * bx, by, bz)),
                                    rot_deg=(pitch + hpitch, 0, s * yaw),
                                    scale=sc * hp.get('scale', 1.0))
            h = ops.tube(f'horn_{tag}{k}', pts, radii)
            materials.assign(h, bone)
            out.append(h)

    # --- petites pointes sous la mâchoire et sur les joues ---
    for j, (jy, jz) in enumerate(((0.32, -0.10), (0.58, -0.09), (0.84, -0.08))):
        c = ops.spike(f'chin_{j}', W(J((0, jy, jz))), 0.11 - 0.02 * j, 0.028, R(-gape + 168))
        materials.assign(c, bone)
        out.append(c)
    for s, tag in ((1, 'l'), (-1, 'r')):
        c = ops.spike(f'cheekspike_{tag}', W((s * sk[0] * 0.85, -0.16, -0.10)),
                      0.14, 0.04, (pitch + 150, 0, s * 35))
        materials.assign(c, bone)
        out.append(c)

    # --- yeux émissifs, petits, enfoncés sous les arcades ---
    for s, tag in ((1, 'l'), (-1, 'r')):
        e = ops.blob(f'eye_{tag}', W((s * 0.215, 0.30, 0.105)), (0.045, 0.045, 0.045))
        materials.assign(e, _mat(mats, 'eye'))
        out.append(e)
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
    """Patte : tube conique articulé + pied + griffes."""
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
            fb = ops.blob(f'foot_{tag}', (s * f['loc'][0], f['loc'][1], f['loc'][2]),
                          f.get('scale', [0.24, 0.38, 0.12]))
            materials.assign(fb, _mat(mats, part.get('mat', 'scales')))
            out.append(fb)
            fl = f['loc']
            for j, dx in enumerate((-0.12, 0, 0.12)):
                c = ops.spike(f'claw_{tag}{j}', (s * (fl[0] + dx), fl[1] + f.get('scale', [0, 0.38, 0])[1], 0.06),
                              0.18, 0.045, (100, 0, 0))
                materials.assign(c, _mat(mats, 'bone'))
                out.append(c)
    return out


@builder('ground')
def ground(part, mats):
    g = ops.plane('ground', part.get('size', 80))
    materials.assign(g, _mat(mats, part.get('mat', 'rock')))
    return [g]


def build(spec):
    """Point d'entrée : spec dict → scène complète. Retourne le nombre d'objets."""
    core.reset()
    mats = {}
    for key, m in spec.get('materials', {}).items():
        mats[key] = getattr(materials, m['builder'])(name=key, **m.get('p', {}))
    count = 0
    for part in spec['parts']:
        count += len(BUILDERS[part['type']](part, mats))
    sc = spec.get('scene', {})
    core.world(**sc.get('world', {}))
    core.sun(**sc.get('sun', {}))
    for al in sc.get('area_lights', []):
        core.area_light(**al)
    core.camera(**sc.get('camera', {'loc': (9, -11, 3.5), 'target': (0, 0, 2), 'lens': 40}))
    return count
