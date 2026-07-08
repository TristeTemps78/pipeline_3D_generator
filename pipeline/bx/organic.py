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
            if t > 0.72:  # pas de fondu vers 0 côté tête : fusion avec la couronne de cornes
                fade = (t - 0.72) / 0.28
                env = max(env, 0.62 * (1 - fade) + 0.42 * fade)
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

    # --- orbites : creux sous l'arcade sourcilière, carvé dans le crâne (boolean) ---
    eyep = part.get('eye', {})
    ex, ey, ez = eyep.get('pos', (0.25, 0.315, 0.20))
    esr = eyep.get('socket_r', 0.088)
    egr = eyep.get('globe_r', 0.072)
    for s, tag in ((1, 'l'), (-1, 'r')):
        cutter = ops.blob(f'eye_cutter_{tag}', W((s * ex, ey, ez)),
                          (esr * 0.95, esr * 0.78, esr * 0.95))
        sk = ops.boolean_diff(sk, cutter, name='skull')
        materials.assign(sk, skin)

    # --- naseaux : ouverture carvée dans le museau (boolean, même schéma que les
    # orbites) — pas un blob posé dessus. Le monticule charnu vient après, enfoncé
    # aux 2/3 dans la surface pour fondre le raccord au lieu de flotter dessus. ---
    np_ = part.get('nostril', {})
    npos = np_.get('pos', (0.065, 1.10, 0.075))
    nk = np_.get('size', 0.03)
    for s, tag in ((1, 'l'), (-1, 'r')):
        cx, cy, cz = s * npos[0], npos[1], npos[2]
        cutter = ops.blob(f'nostril_cutter_{tag}', W((cx, cy, cz)),
                          (nk * 1.05, nk * 1.7, nk * 0.85), rot_deg=(pitch - 18, 0, s * 20))
        sk = ops.boolean_diff(sk, cutter, name='skull')
        materials.assign(sk, skin)
    out.append(sk)

    rings = [[WJ((x, y, z - hh * 0.85)) for x, z in laws.superellipse(w, hh, exp)]
             for y, w, hh in lower]
    jw = ops.ring_loft('jaw', rings)
    materials.assign(jw, skin)
    out.append(jw)

    # --- dents : tubes effilés courbes le long des bords de gueule.
    # `tooth_scale` grossit longueur ET rayon ; les rangées suivent la longueur du
    # museau via tooth_span_* (y début/fin) — une gueule agrandie garde ses dents
    # réparties jusqu'au bout du museau au lieu de s'arrêter à mi-chemin. ---
    ts = part.get('tooth_scale', 1.0)
    su = part.get('tooth_span_upper', (0.42, 1.07))
    nu = part.get('teeth_upper', 6)
    fu_idx = set(part.get('fang_idx_upper', ()))
    fu_scale = part.get('fang_scale_upper', 1.0)
    for i in range(nu):
        y = su[0] + i * (su[1] - su[0]) / max(1, nu - 1)
        w = interp_w(upper, y) * 0.78
        l = (0.07 + 0.012 * i) * (1 + 0.15 * math.sin(i * 9.1)) * ts
        if i in fu_idx:
            l *= fu_scale
        for s, tag in ((1, 'l'), (-1, 'r')):
            x = s * w
            t = ops.tube(f'tooth_u{tag}{i}',
                         [W((x, y, -0.005)), W((x * 0.97, y + 0.015, -l * 0.55)), W((x * 0.92, y + 0.03, -l))],
                         [0.020 * ts, 0.012 * ts, 0.003])
            materials.assign(t, tooth_m)
            out.append(t)
    sl = part.get('tooth_span_lower', (0.35, 0.99))
    nl = part.get('teeth_lower', 5)
    fl_idx = set(part.get('fang_idx_lower', ()))
    fl_scale = part.get('fang_scale_lower', 1.0)
    for i in range(nl):
        y = sl[0] + i * (sl[1] - sl[0]) / max(1, nl - 1)
        w = interp_w(lower, y) * 0.75
        l = (0.06 + 0.010 * i) * (1 + 0.15 * math.sin(i * 7.7 + 1.3)) * ts
        if i in fl_idx:
            l *= fl_scale
        for s, tag in ((1, 'l'), (-1, 'r')):
            x = s * w
            t = ops.tube(f'tooth_l{tag}{i}',
                         [WJ((x, y, 0.005)), WJ((x * 0.97, y + 0.015, l * 0.55)), WJ((x * 0.92, y + 0.03, l))],
                         [0.018 * ts, 0.011 * ts, 0.003])
            materials.assign(t, tooth_m)
            out.append(t)

    # --- globe enchâssé (calotte seule visible) + bourrelets de paupière ---
    for s, tag in ((1, 'l'), (-1, 'r')):
        g = ops.blob(f'eye_{tag}', W((s * ex * 0.88, ey - 0.006, ez)), (egr, egr, egr))
        materials.assign(g, _mat(mats, 'eye'))
        out.append(g)
        lu = ops.blob(f'lid_up_{tag}', W((s * ex, ey + 0.025, ez + esr * 0.68)),
                      (esr * 0.80, esr * 0.46, esr * 0.30), rot_deg=(0, 0, s * 10))
        materials.assign(lu, skin)
        out.append(lu)
        ll = ops.blob(f'lid_lo_{tag}', W((s * ex, ey - 0.02, ez - esr * 0.66)),
                      (esr * 0.72, esr * 0.42, esr * 0.24))
        materials.assign(ll, skin)
        out.append(ll)

    # --- naseaux (suite) : cavité sombre logée sous l'ouverture carvée (donne la
    # profondeur qu'on ne voit pas dans le trou seul) + monticule charnu enfoncé
    # aux 2/3 dans le museau (centre déplacé vers l'intérieur, pas posé dessus) ---
    for s, tag in ((1, 'l'), (-1, 'r')):
        cx, cy, cz = s * npos[0], npos[1], npos[2]
        cavity = ops.blob(f'nostril_cavity_{tag}', W((cx * 1.02, cy + nk * 0.25, cz - nk * 0.2)),
                          (nk * 0.55, nk * 0.8, nk * 0.42), rot_deg=(pitch - 18, 0, s * 20))
        materials.assign(cavity, _mat(mats, 'eye'))
        out.append(cavity)
        mound = ops.blob(f'nose_mound_{tag}', W((cx, cy - nk * 0.55, cz - nk * 0.7)),
                         (nk * 2.2, nk * 2.8, nk * 1.7), rot_deg=(pitch - 8, 0, s * 14))
        materials.assign(mound, skin)
        out.append(mound)

    # --- couronne de cornes : spirale log GVL, profil à 2 maîtresses + dégradé,
    # densifiée pour se fondre dans la crête dorsale du cou (pas de trou tête-cou) ---
    pairs = hp.get('pairs', 11)
    master_k = hp.get('master_k', 2.4)
    master_w = hp.get('master_w', 1.7)
    size_min = hp.get('size_min', 0.24)
    size_bump = hp.get('size_bump', 0.85)
    sizes = []
    for k in range(pairs):
        bump = math.exp(-((k - master_k) / master_w) ** 2)
        sizes.append(size_min + size_bump * bump)
    raw = apply_law(hp.get('vocab', 'growth.horn_spiral'),
                    n=16, a=hp.get('a', 0.10), b=hp.get('b', 0.30),
                    turns=hp.get('turns', 0.6), rise=hp.get('rise', 0.55))
    base_radii = laws.power_taper(16, hp.get('r0', 0.075), 1.15, 0.008)
    # ancrages : lerp base_from -> base_to (repère local tête, x=côté y=avant z=haut)
    # + éventail yaw0..yaw0+yaw_spread. « 2 maîtresses arrière » = master_w étroit,
    # size_bump fort, pitch très négatif (couchées vers la nuque), yaw_spread faible.
    bf = hp.get('base_from', (0.08, 0.10, 0.35))
    bt = hp.get('base_to', (0.27, -0.24, 0.19))
    for k in range(pairs):
        u = k / max(1, pairs - 1)
        sc = sizes[k]
        radii = [r * (0.45 + 0.55 * sc) for r in base_radii]
        yaw = hp.get('yaw0', 6) + u * hp.get('yaw_spread', 62)
        hpitch = hp.get('pitch', -35) - u * hp.get('pitch_spread', 20)
        jit = 0.05 * math.sin(k * 5.1)
        base = (bf[0] + (bt[0] - bf[0]) * u, bf[1] + (bt[1] - bf[1]) * u,
                bf[2] + (bt[2] - bf[2]) * u + jit)
        for s, tag in ((1, 'l'), (-1, 'r')):
            pts = ops.transform_pts(raw, loc=W((s * base[0], base[1], base[2])),
                                    rot_deg=(pitch + hpitch, 0, s * (yaw + 6 * jit)),
                                    scale=sc * hp.get('scale', 1.0))
            h = ops.tube(f'horn_{tag}{k}', pts, radii)
            materials.assign(h, bone_m)
            out.append(h)
    # petites cornes d'arcade + pointes de joue (ancrées sur l'os, base large) ;
    # feature_scale suit l'agrandissement du crâne (positions ET tailles locales)
    hk = part.get('feature_scale', 1.0)
    for s, tag in ((1, 'l'), (-1, 'r')):
        b = ops.spike(f'horn_brow_{tag}', W((s * 0.22 * hk, 0.38 * hk, 0.26 * hk)),
                      0.14 * hk, 0.038 * hk, (pitch - 35, 0, s * 15))
        materials.assign(b, bone_m)
        out.append(b)
        c = ops.spike(f'horn_cheek_{tag}', W((s * 0.30 * hk, 0.12 * hk, -0.02 * hk)),
                      0.16 * hk, 0.048 * hk, (pitch + 95, 0, s * 55))
        materials.assign(c, bone_m)
        out.append(c)
    # --- picots de remplissage : densifient la couronne entre/autour des cornes
    # principales, petites tailles variées, ancrés dans les plaques crâniennes ---
    fill_n = hp.get('fill_n', 7)
    for j in range(fill_n):
        u = j / max(1, fill_n - 1)
        jit = 0.6 + 0.4 * math.sin(j * 3.7)
        h = (0.05 + 0.05 * jit) * (1.3 if 0.25 < u < 0.55 else 1.0) * hk
        r = (0.016 + 0.012 * jit) * hk
        loc_local = ((0.14 + 0.13 * u) * hk, (0.44 - 0.62 * u) * hk,
                     (0.33 - 0.14 * u) * hk + 0.02 * math.sin(j * 4.3))
        for s, tag in ((1, 'l'), (-1, 'r')):
            fp = ops.spike(f'horn_fill_{tag}{j}', W((s * loc_local[0], loc_local[1], loc_local[2])),
                           h, r, (pitch - 20 - 45 * u, 0, s * (18 + 50 * u)))
            materials.assign(fp, bone_m)
            out.append(fp)
    return out


@builder('dewlap')
def dewlap(part, mats):
    """Fanon de gorge : chapelet de masses charnues qui pendent sous la mâchoire/le cou,
    avec petits plis superposés (chaque maillon = un blob principal + un pli secondaire
    décalé vers l'avant-bas, silhouette de peau lâche plutôt que tube lisse)."""
    pts = [tuple(p) for p in part['pts']]
    sizes = part['sizes']
    mat = _mat(mats, part.get('mat', 'scales'))
    out = []
    n = len(pts)
    for i, (p, r) in enumerate(zip(pts, sizes)):
        # masse principale très allongée le long du cou (recouvre le point suivant) :
        # fond la chaîne en une seule poche continue plutôt qu'un chapelet de perles
        # étroit en X et très allongé en Y : quille de peau lâche continue le long de
        # la gorge — des ratios proches de la sphère rendent comme un chapelet d'œufs
        b = ops.blob(f"dewlap_{part.get('id', 'd')}_{i}", p, (r * 0.5, r * 2.7, r * 0.78))
        materials.assign(b, mat)
        out.append(b)
        if i < n - 1:
            # petit pli superposé entre deux maillons, discret (pas une grosse sphère)
            nxt = pts[i + 1]
            mid = tuple((p[k] + nxt[k]) / 2 for k in range(3))
            fr = (r + sizes[i + 1]) * 0.30
            fold = (mid[0], mid[1], mid[2] - fr * 0.55)
            f = ops.blob(f"dewlap_fold_{part.get('id', 'd')}_{i}", fold, (fr * 0.75, fr * 1.3, fr * 0.55))
            materials.assign(f, mat)
            out.append(f)
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


def _apply_displace(spec, groups):
    """Rides/plis géométriques (C4, Displace réel après Subsurf SIMPLE — pas de bruit
    shader) sur des parts précises HORS fusion `fuse` (membrane d'aile, fanon, peau nue
    des pattes). `detail.displace_targets` = liste de {target(s), match(sous-chaîne de
    nom d'objet optionnelle), layers:[...], subdiv}. Câblé séparément de
    `_apply_fuse_detail` car ce dragon n'utilise pas `fuse` (corps en parts distinctes)."""
    entries = spec.get('detail', {}).get('displace_targets', [])
    if not entries:
        return
    from . import detail as _detail
    for e in entries:
        targets = e.get('targets') or ([e['target']] if 'target' in e else [])
        match = e.get('match')
        objs = [o for t in targets for o in groups.get(t, [])
                if o.type == 'MESH' and (not match or match in o.name)]
        for ob in objs:
            _detail.displace_layers(ob, e.get('layers', []), subdiv=e.get('subdiv', 1))


def _apply_armor(spec, groups):
    """Écailles GÉOMÉTRIQUES chevauchantes ciblées par groupe de parts (I1, sans passer
    par fuse). `detail.armor` = liste d'entrées {target(s), instance{...}, density,
    scale, caudal, curvature, mask{axis,range,to}, scale_grad{axis,range,scale_lo,scale_hi},
    exclude:[sous-chaînes de nom d'objet à sauter, ex. cornes/dents/yeux]}.
    Permet de restreindre les plaques à une région (cou, tête) sans dupliquer la géométrie
    du corps ni toucher aux parts non concernées."""
    entries = spec.get('detail', {}).get('armor', [])
    if not entries:
        return
    from . import detail as _detail
    for idx, e in enumerate(entries):
        targets = e.get('targets') or ([e['target']] if 'target' in e else [])
        exclude = e.get('exclude', [])
        # bake CURVE->MESH une seule fois par target : plusieurs entrées d'armure
        # peuvent viser le même groupe (ex. corps découpé en zones queue/flanc/cou) —
        # realize_to_mesh() supprime l'objet CURVE d'origine, donc on met le groupe à
        # jour en place pour que les entrées suivantes réutilisent le mesh déjà baké.
        for t in targets:
            groups[t] = [core.realize_to_mesh(o) if o.type == 'CURVE' else o
                        for o in groups.get(t, [])]
        objs = [o for t in targets for o in groups.get(t, [])
                if o.type == 'MESH' and not any(x in o.name for x in exclude)]
        if not objs:
            continue
        # bibliothèque d'archétypes (T11) ou plaque unique (rétro-compatible).
        # `realize` défaut False (T12) : instances vivantes + attribut 'scale_seed'
        # → micro par écaille côté shader, mémoire ~divisée par 10.
        archs = e.get('archetypes')
        if archs:
            plate = [_detail.archetype(f'armor_plate_{idx}_{k}', **a)
                     for k, a in enumerate(archs)]
            for p in plate:
                materials.assign(p, _mat(spec.get('_mats', {}), e.get('mat', 'scales')))
        else:
            plate = _detail.keeled_scale(name=f'armor_plate_{idx}', **e.get('instance', {}))
            materials.assign(plate, _mat(spec.get('_mats', {}), e.get('mat', 'scales')))
        realize = e.get('realize', False)
        for j, ob in enumerate(objs):
            _detail.armor_scales(
                ob, plate, density=e.get('density', 400.0),
                scale=tuple(e.get('scale', (0.08, 0.14))),
                seed=e.get('seed', 1) + j,
                caudal=tuple(e.get('caudal', (0, -1, 0))),
                curvature=e.get('curvature', True),
                mask=e.get('mask'), scale_grad=e.get('scale_grad'),
                distance_min=e.get('distance_min', 0.0),
                index_grad=e.get('index_grad'),
                index_noise=tuple(e.get('index_noise', (3.0, 1.4))),
                rot_jitter=e.get('rot_jitter', 0.0),
                realize=realize,
                store_seed=e.get('store_seed', not realize),
                name=f'armor_{idx}_{ob.name}')


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
    _apply_displace(spec, groups)
    _apply_armor(spec, groups)
    sc = spec.get('scene', {})
    core.world(**sc.get('world', {}))
    core.sun(**sc.get('sun', {}))
    for al in sc.get('area_lights', []):
        core.area_light(**al)
    core.camera(**sc.get('camera', {'loc': (9, -11, 3.5), 'target': (0, 0, 2), 'lens': 40}))
    return count
