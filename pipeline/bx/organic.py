"""bx.organic — générateurs de parties anatomiques pilotés par spec JSON + lois GVL.
Chaque builder consomme un dict compact et retourne des objets Blender. Généraliste :
un dragon, un arbre ou un poisson ne diffèrent que par leur spec."""
import math

from mathutils import Vector

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
    """Corps principal : tube conique le long des points de contrôle + crête dorsale."""
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
            pitch = -math.degrees(math.atan2(nxt[1] - p[1], (nxt[2] - p[2]) or 1e-3))
            t = i / (n - 1)
            h = max(0.08, sp.get('h0', 0.4) * math.sin(math.pi * t) ** 0.6 * min(1.0, r * 2.0 + 0.3))
            s = ops.spike(f'dorsal_{i}', (p[0], p[1], p[2] + r * 0.9 + h * 0.35),
                          height=h, radius=h * 0.28, rot_deg=(pitch * 0.4 - 12, 0, 0))
            materials.assign(s, _mat(mats, sp.get('mat', 'bone')))
            out.append(s)
    return out


@builder('head')
def head(part, mats):
    """Tête : crâne + museau + mâchoire (ellipsoïdes), cornes en spirale log, yeux."""
    L = tuple(part['loc'])
    skin = _mat(mats, part.get('mat', 'scales'))
    out = []
    for nm, off, sc, rot in [
        ('skull', (0, 0, 0), part.get('skull', [0.38, 0.6, 0.34]), (-12, 0, 0)),
        ('snout', part.get('snout_off', [0, 0.62, -0.06]), part.get('snout', [0.2, 0.5, 0.16]), (-8, 0, 0)),
        ('jaw', part.get('jaw_off', [0, 0.5, -0.22]), part.get('jaw', [0.16, 0.42, 0.09]), (12, 0, 0)),
        ('brow_l', (0.15, 0.3, 0.14), [0.11, 0.18, 0.07], (-15, 0, -8)),
        ('brow_r', (-0.15, 0.3, 0.14), [0.11, 0.18, 0.07], (-15, 0, 8)),
    ]:
        b = ops.blob(nm, (L[0] + off[0], L[1] + off[1], L[2] + off[2]), sc, rot)
        materials.assign(b, skin)
        out.append(b)
    hp = part.get('horns', {})
    raw = apply_law(hp.get('vocab', 'growth.horn_spiral'),
                    n=20, a=hp.get('a', 0.09), b=hp.get('b', 0.3),
                    turns=hp.get('turns', 0.85), rise=hp.get('rise', 0.5))
    radii = laws.power_taper(20, hp.get('r0', 0.09), 1.2, 0.012)
    for side, x in [('l', 0.17), ('r', -0.17)]:
        pts = ops.transform_pts(raw, loc=(L[0] + x, L[1] - 0.18, L[2] + 0.2),
                                rot_deg=(hp.get('pitch', 55), 0, 20 if side == 'l' else -20))
        h = ops.tube(f'horn_{side}', pts, radii)
        materials.assign(h, _mat(mats, hp.get('mat', 'bone')))
        out.append(h)
    for side, x in [('l', 0.26), ('r', -0.26)]:
        e = ops.blob(f'eye_{side}', (L[0] + x, L[1] + 0.32, L[2] + 0.12), (0.06, 0.06, 0.06))
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
