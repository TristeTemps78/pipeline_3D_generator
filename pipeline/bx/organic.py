"""bx.organic — générateurs de parties anatomiques pilotés par spec JSON + lois GVL.
Chaque builder consomme un dict compact et retourne des objets Blender. Généraliste :
un dragon, un arbre ou un poisson ne diffèrent que par leur spec."""
import math

from mathutils import Euler, Quaternion, Vector

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
        # base/pointe et anneaux de croissance (feedback boucle 18 pt5 : piques
        # dorsales qui lisent comme de la fourrure/des plumes) : `base_frac`/`tip_r`
        # (rétro-compat, défauts = valeurs historiques 0.22/0.008) élargissent la base
        # d'implantation ; `rings` (absent par défaut = comportement inchangé) réutilise
        # `laws.growth_rings` (déjà utilisée par les cornes) sur le profil à 3 points
        # pour casser la lame lisse et translucide par un renflement médian discret.
        base_frac = sp.get('base_frac', 0.22)
        mid_frac = sp.get('mid_frac', 0.12)
        tip_r = sp.get('tip_r', 0.008)
        rp = sp.get('rings')
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
                s_radii = [h * base_frac, h * mid_frac, tip_r]
                if rp and rp.get('depth', 0.0):
                    mod = laws.growth_rings(3, depth=rp.get('depth', 0.12),
                                            freq=rp.get('freq', 3.0), sharp=rp.get('sharp', 2.0))
                    s_radii = [r * m for r, m in zip(s_radii, mod)]
                s = ops.tube(f'dorsal_{i}_{row}', s_pts, s_radii)
                materials.assign(s, _mat(mats, sp.get('mat', 'bone')))
                out.append(s)
    return out


def _apply_horn_growth(pts_local, radii, ring_p=None, curl=0.0, curl_power=1.6,
                       root_len=0.0, root_bulge=1.0):
    """Post-traitement générique d'un profil de pointe kératineuse (n points locaux +
    n rayons) : anneaux de croissance (`ring_p` = {depth,freq,sharp}, `growth.keratin_rings`),
    légère courbure de pointe (`curl`, décalage hors-plan croissant base->pointe sur
    l'axe X local, `growth.tip_curl`) et bourrelet d'implantation (`root_len` prolonge
    la base en arrière -vers l'intérieur du support porteur-, `root_bulge` l'élargit)
    -> remplace un cône/tube lisse planté par une base fondue avec anneaux/torsion.
    Partagé par les cornes maîtresses (profil en spirale GVL) et les pointes
    secondaires (arcade/joue, profil droit) : aucune valeur dragon, tout vient de la
    spec (défauts neutres -> comportement inchangé si absent)."""
    n = len(pts_local)
    pts_local = list(pts_local)
    radii = list(radii)
    if ring_p and ring_p.get('depth', 0.0):
        mod = laws.growth_rings(n, depth=ring_p.get('depth', 0.14),
                                freq=ring_p.get('freq', 4.0), sharp=ring_p.get('sharp', 3.0))
        radii = [r * m for r, m in zip(radii, mod)]
    if curl:
        off = laws.curl_offset(n, amount=curl, power=curl_power)
        pts_local = [(p[0] + o, p[1], p[2]) for p, o in zip(pts_local, off)]
    if root_len > 0:
        tang = Vector(pts_local[1]) - Vector(pts_local[0])
        tang = tang.normalized() if tang.length > 1e-6 else Vector((0, 0, -1))
        root_pt = Vector(pts_local[0]) - tang * root_len
        pts_local = [tuple(root_pt)] + pts_local
        radii = [radii[0] * root_bulge] + radii
    return pts_local, radii


def _kera_spike(name, base_world, height, r0, rot_deg, mat, ring_p=None, curl=0.0,
                curl_power=1.6, root_len=0.0, root_bulge=1.0, taper=1.3, rmin_frac=0.12, n=6):
    """Pointe kératineuse générique (arcade, joue...) : petit tube profilé avec anneaux/
    courbure/base fondue optionnels, remplace un cône lisse `ops.spike` planté sur le
    crâne. Même convention de placement que `ops.spike` : `base_world` est le CENTRE
    de la pointe (axe local Z, -height/2..+height/2), pas sa base."""
    pts_local = [(0.0, 0.0, -height / 2 + height * i / (n - 1)) for i in range(n)]
    radii = laws.power_taper(n, r0, taper, r0 * rmin_frac)
    pts_local, radii = _apply_horn_growth(pts_local, radii, ring_p, curl, curl_power,
                                          root_len, root_bulge)
    pts = ops.transform_pts(pts_local, loc=base_world, rot_deg=rot_deg)
    # résolution réduite (budget sommets) : un profil à N points de contrôle porte
    # déjà assez de détail pour les anneaux, pas besoin de la résolution NURBS/bevel
    # par défaut (pensée pour des tubes à 2-3 points).
    h = ops.tube(name, pts, radii, resolution_u=6, bevel_resolution=6)
    materials.assign(h, mat)
    return h


def _interp_scalar(ys, vals, y):
    """Interpolation linéaire générique le long d'une liste croissante `ys` (position)
    -> `vals` (valeur associée), clampée aux extrémités. Brique partagée par le profil
    de largeur des sections tête (`interp_w`), la courbure d'axe (`axis_flex`) et le
    bourrelet de lèvre (`_lip_bourrelet`) — un seul mécanisme d'échantillonnage pour
    tout ce qui suit le même profil `[y, w, hh]` que les dents."""
    if not ys:
        return 0.0
    if y <= ys[0]:
        return vals[0]
    if y >= ys[-1]:
        return vals[-1]
    for i in range(len(ys) - 1):
        y0, y1 = ys[i], ys[i + 1]
        if y0 <= y <= y1:
            f = (y - y0) / (y1 - y0) if y1 != y0 else 0.0
            return vals[i] + f * (vals[i + 1] - vals[i])
    return vals[-1]


def _lip_bourrelet(prefix, secs, y_span, Wf, mat, out, n=16, thickness=0.03,
                   thickness_min_frac=0.55, w_frac=0.9, z_frac=-0.2,
                   flex=None, ys_flex=None, noise_scale=0.14, noise_strength=0.4,
                   seed=0.0, mirror=True):
    """Bourrelet de lèvre/gencive GÉNÉRIQUE (boucle 17 CR3, feedback A2) : tube continu
    qui suit la largeur `secs` (sections [y,w,hh], le MÊME profil que le crâne/la
    mâchoire et les dents, cf. `interp_w`) et la courbure d'axe `flex` (optionnelle,
    cf. `growth.axis_flex`) au lieu de points codés en dur dans la spec (`ridges`
    gum_u/gum_l/lip_l — doute consigné boucle 15 : ils désynchronisent si les dents ou
    le profil bougent). `noise_scale`/`noise_strength` cassent la ligne d'ouverture
    droite (jitter sinusoïdal multi-fréquence sur le RAYON et un léger décalage en Z)
    -> lèvre charnue irrégulière plutôt qu'un tube lisse à section constante. `z_frac`
    place le bourrelet le long de la hauteur locale de la section, MÊME convention que
    les formules de ring du crâne/mâchoire (`z+hh*0.82` / `z-hh*0.85`) : un `z_frac`
    négatif (~-0.18 à -0.3) suit le bord bas de la superellipse (bouche du HAUT), un
    `z_frac` positif (~0.15 à 0.25) suit le bord haut (mâchoire du BAS)."""
    ys = [s[0] for s in secs]
    ws = [s[1] for s in secs]
    hs = [s[2] for s in secs]
    y0, y1 = y_span
    sides = ((1, 'l'), (-1, 'r')) if mirror else ((1, ''),)
    for s, tag in sides:
        pts, radii = [], []
        for i in range(n):
            t = i / max(1, n - 1)
            y = y0 + t * (y1 - y0)
            w = _interp_scalar(ys, ws, y)
            hh = _interp_scalar(ys, hs, y)
            fz = _interp_scalar(ys_flex, flex, y) if flex else 0.0
            ph = seed + t / max(noise_scale, 1e-4)
            jit = 0.6 * math.sin(ph * 2 * math.pi) + 0.4 * math.sin(ph * 5.3 + 1.7)
            z = fz + hh * z_frac + jit * noise_strength * hh * 0.15
            x = s * w * w_frac
            pts.append(Wf((x, y, z)))
            rr = thickness * (thickness_min_frac + (1 - thickness_min_frac) * math.sin(math.pi * t) ** 0.5)
            radii.append(max(thickness * 0.15, rr * (1 + 0.3 * jit)))
        tube = ops.tube(f'{prefix}_{tag}', pts, radii, resolution_u=8, bevel_resolution=6)
        materials.assign(tube, mat)
        out.append(tube)


@builder('head')
def head(part, mats):
    """Tête loftée par sections superellipse (GVL) : crâne→museau continu, mâchoire
    inférieure articulée ouverte de `gape`°, dents courbes, yeux sous arcades,
    narines, couronne de cornes en spirale log."""
    L = Vector(part['loc'])
    pitch = part.get('pitch', -8.0)
    # head_yaw (T17 CR2, défaut 0 = rétro-compat ; nommé à part de `yaw` local à la
    # couronne de cornes plus bas pour éviter toute collision de nom) : rotation de la
    # tête ENTIÈRE autour de l'axe vertical local (Z) -> tête légèrement tournée vers
    # la caméra sans toucher au `pitch` (nez haut/bas) ni dupliquer le builder. Comme
    # tout est placé en coordonnées LOCALES relatives à `L`/`Rp` (yeux, cornes, dents,
    # crêtes...), une seule rotation ici entraîne l'ensemble de la tête de façon rigide.
    head_yaw = part.get('yaw', 0.0)
    gape = part.get('gape', 26.0)
    exp = part.get('exp', 1.7)
    skin = _mat(mats, part.get('mat', 'scales'))
    hp = part.get('horns', {})
    bone_m = _mat(mats, hp.get('mat', 'bone'))
    tooth_m = _mat(mats, 'teeth') or bone_m
    Rp = Euler((math.radians(pitch), 0, math.radians(head_yaw))).to_matrix()
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
    # courbure non-linéaire du museau (boucle 17 CR3, feedback A1) : `snout_curve`
    # {dip,tip,dip_pos,sharp} pilote `growth.axis_flex` -> le museau plonge puis
    # remonte vers la pointe au lieu d'un loft quasi-droit (effet "pince"). Décalage
    # nul en t=0 (base du crâne) -> ne déplace PAS la jonction avec le cou/spine.
    sc = part.get('snout_curve')
    ys_u = [s[0] for s in upper]
    upper_flex = apply_law('growth.axis_flex', n=len(upper), **sc) if sc else [0.0] * len(upper)
    rings = [[W((x, y, z + hh * 0.82 + upper_flex[i])) for x, z in laws.superellipse(w, hh, exp)]
             for i, (y, w, hh) in enumerate(upper)]
    sk = ops.ring_loft('skull', rings)
    materials.assign(sk, skin)

    # --- orbites : creux sous l'arcade sourcilière, carvé dans le crâne (boolean) ---
    # cavité plus PROFONDE et légèrement enfoncée (feedback B "retrait net") : le
    # cutter précédent (0.95/0.78/0.95, centré pile sur `ex`) mordait à peine la
    # surface -> orbite qui se lisait comme un simple aplat. Étendu en profondeur
    # (axe X local = normale de la calotte, cf. EyeBuilder plus bas) et recentré vers
    # l'intérieur du crâne (`ex*0.92`) pour créer un vrai rebord visible autour du
    # globe, où viennent s'ancrer les paupières.
    eyep = part.get('eye', {})
    ex, ey, ez = eyep.get('pos', (0.25, 0.315, 0.20))
    esr = eyep.get('socket_r', 0.088)
    egr = eyep.get('globe_r', 0.072)
    for s, tag in ((1, 'l'), (-1, 'r')):
        cutter = ops.blob(f'eye_cutter_{tag}', W((s * ex * 0.92, ey, ez)),
                          (esr * 1.30, esr * 0.82, esr * 0.98))
        sk = ops.boolean_diff(sk, cutter, name='skull')
        materials.assign(sk, skin)

    # --- naseaux : ouverture carvée dans le museau (boolean, même schéma que les
    # orbites) — pas un blob posé dessus. Le monticule charnu vient après, enfoncé
    # aux 2/3 dans la surface pour fondre le raccord au lieu de flotter dessus. ---
    np_ = part.get('nostril', {})
    npos = np_.get('pos', (0.065, 1.10, 0.075))
    nk = np_.get('size', 0.03)
    # taille de la coupe (feedback boucle 18 pt4, « narines absentes ») : agrandie
    # (1.05/1.7/0.85 -> 1.15/1.85/1.0) pour une ouverture nette qui se voit à distance,
    # pas seulement un pli à peine visible.
    for s, tag in ((1, 'l'), (-1, 'r')):
        cx, cy, cz = s * npos[0], npos[1], npos[2]
        cutter = ops.blob(f'nostril_cutter_{tag}', W((cx, cy, cz)),
                          (nk * 1.15, nk * 1.85, nk * 1.0), rot_deg=(pitch - 18, 0, s * 20))
        sk = ops.boolean_diff(sk, cutter, name='skull')
        materials.assign(sk, skin)
    out.append(sk)

    # mâchoire inférieure : courbe INVERSE de celle du museau (`jaw_curve`, même loi) —
    # décalage nul en t=0 (pivot de la mâchoire, près de la charnière) donc l'ouverture
    # `gape` reste valide sans recalage.
    jc = part.get('jaw_curve')
    ys_l = [s[0] for s in lower]
    lower_flex = apply_law('growth.axis_flex', n=len(lower), **jc) if jc else [0.0] * len(lower)
    rings = [[WJ((x, y, z - hh * 0.85 + lower_flex[i])) for x, z in laws.superellipse(w, hh, exp)]
             for i, (y, w, hh) in enumerate(lower)]
    jw = ops.ring_loft('jaw', rings)
    materials.assign(jw, skin)
    out.append(jw)

    # --- dents : tubes effilés courbes le long des bords de gueule, VARIÉS (pas des
    # cônes identiques étirés) : le rayon suit désormais la longueur de chaque dent
    # (`rscale`, racine carrée -> proportions coniques naturelles) au lieu d'être
    # constant pour toute la rangée, `fang_girth_*` épaissit les crocs en plus de les
    # allonger (`fang_scale_*`), un second harmonique de jitter casse la régularité.
    # `tooth_scale` grossit longueur ET rayon ; les rangées suivent la longueur du
    # museau via tooth_span_* (y début/fin) — une gueule agrandie garde ses dents
    # réparties jusqu'au bout du museau au lieu de s'arrêter à mi-chemin. ---
    # graine générique de variance dents (feedback A3) : `tooth_seed` déphase les
    # sinusoïdes d'inclinaison/latéralité sans changer le nombre/l'espacement des
    # dents -> une seule valeur spec fait "rejouer" un autre jeu de dents irrégulières.
    ts = part.get('tooth_scale', 1.0)
    tooth_seed = part.get('tooth_seed', 0.0)
    gp = part.get('gum', {})
    gum_scale = gp.get('scale', 1.0)
    gum_flat = gp.get('flatten', 0.42)
    gum_seg = gp.get('seg', 10)
    su = part.get('tooth_span_upper', (0.42, 1.07))
    nu = part.get('teeth_upper', 6)
    fu_idx = set(part.get('fang_idx_upper', ()))
    fu_scale = part.get('fang_scale_upper', 1.0)
    fu_girth = part.get('fang_girth_upper', 1.3)
    lu_ref = ts * (0.07 + 0.012 * (nu - 1) * 0.5)
    for i in range(nu):
        y = su[0] + i * (su[1] - su[0]) / max(1, nu - 1)
        w = interp_w(upper, y) * 0.78
        fz = _interp_scalar(ys_u, upper_flex, y)
        jit_l = 1 + 0.15 * math.sin(i * 9.1 + tooth_seed) + 0.05 * math.sin(i * 3.3 + 0.6 + tooth_seed)
        is_fang = i in fu_idx
        l = (0.07 + 0.012 * i) * ts * jit_l
        if is_fang:
            l *= fu_scale
        rscale = max(0.55, min(1.9, (l / max(lu_ref, 1e-4)) ** 0.5))
        if is_fang:
            rscale *= fu_girth
        jit_r = 1 + 0.08 * math.sin(i * 6.1 + 1.1 + tooth_seed)
        radii = [0.021 * ts * rscale * jit_r, 0.0125 * ts * rscale * jit_r, 0.0032 * ts]
        # inclinaison avant/arrière + léger galbe latéral PAR DENT (`tooth_seed`) : une
        # rangée de cônes tous parallèles -> variance crédible, occasionnellement une
        # dent penche vers l'arrière au lieu de toutes pencher pareil vers l'avant.
        lean = 0.55 + 0.85 * math.sin(i * 3.7 + 1.1 + tooth_seed)
        twist = 0.05 * w * math.sin(i * 5.9 + 2.3 + tooth_seed)
        for s, tag in ((1, 'l'), (-1, 'r')):
            x = s * w
            mid = W((x * 0.97 + s * twist * 0.5, y + 0.015 * lean, fz - l * 0.55))
            tip = W((x * 0.92 + s * twist, y + 0.03 * lean, fz - l))
            t = ops.tube(f'tooth_u{tag}{i}', [W((x, y, fz - 0.005)), mid, tip], radii)
            materials.assign(t, tooth_m)
            out.append(t)
            # volume de gencive à la base (feedback A3) : petit bourrelet APLATI (pas
            # une sphère), fondu au bourrelet de lèvre (`lip_profile`, même matériau
            # peau) -> ancre la dent au lieu de la planter nue dans la mâchoire.
            gr = (0.022 * ts * rscale + 0.006) * gum_scale
            gb = ops.blob(f'gum_u{tag}{i}', W((x, y - 0.008, fz - 0.004)),
                         (gr, gr * 1.5, gr * gum_flat), rot_deg=(0, 0, s * 6), seg=gum_seg)
            materials.assign(gb, skin)
            out.append(gb)
    sl = part.get('tooth_span_lower', (0.35, 0.99))
    nl = part.get('teeth_lower', 5)
    fl_idx = set(part.get('fang_idx_lower', ()))
    fl_scale = part.get('fang_scale_lower', 1.0)
    fl_girth = part.get('fang_girth_lower', 1.3)
    ll_ref = ts * (0.06 + 0.010 * (nl - 1) * 0.5)
    for i in range(nl):
        y = sl[0] + i * (sl[1] - sl[0]) / max(1, nl - 1)
        w = interp_w(lower, y) * 0.75
        fz = _interp_scalar(ys_l, lower_flex, y)
        jit_l = 1 + 0.15 * math.sin(i * 7.7 + 1.3 + tooth_seed) + 0.05 * math.sin(i * 3.1 + 0.2 + tooth_seed)
        is_fang = i in fl_idx
        l = (0.06 + 0.010 * i) * ts * jit_l
        if is_fang:
            l *= fl_scale
        rscale = max(0.55, min(1.9, (l / max(ll_ref, 1e-4)) ** 0.5))
        if is_fang:
            rscale *= fl_girth
        jit_r = 1 + 0.08 * math.sin(i * 5.3 + 0.4 + tooth_seed)
        radii = [0.019 * ts * rscale * jit_r, 0.011 * ts * rscale * jit_r, 0.0032 * ts]
        lean = 0.55 + 0.85 * math.sin(i * 4.1 + 2.6 + tooth_seed)
        twist = 0.05 * w * math.sin(i * 6.7 + 0.4 + tooth_seed)
        for s, tag in ((1, 'l'), (-1, 'r')):
            x = s * w
            mid = WJ((x * 0.97 + s * twist * 0.5, y + 0.015 * lean, fz + l * 0.55))
            tip = WJ((x * 0.92 + s * twist, y + 0.03 * lean, fz + l))
            t = ops.tube(f'tooth_l{tag}{i}', [WJ((x, y, fz + 0.005)), mid, tip], radii)
            materials.assign(t, tooth_m)
            out.append(t)
            gr = (0.020 * ts * rscale + 0.006) * gum_scale
            gb = ops.blob(f'gum_l{tag}{i}', WJ((x, y - 0.008, fz + 0.004)),
                         (gr, gr * 1.5, gr * gum_flat), rot_deg=(0, 0, s * 6), seg=gum_seg)
            materials.assign(gb, skin)
            out.append(gb)

    # --- bourrelets de lèvre/gencive fondus (feedback A2) : suivent la MÊME courbe
    # que les dents (profil `upper`/`lower` + `snout_curve`/`jaw_curve`) au lieu de
    # points `ridges` codés en dur -> ne désynchronise plus si les dents bougent. ---
    lp = part.get('lip_profile')
    if lp:
        n_lip = lp.get('n', 16)
        pad0 = lp.get('pad_start', 0.10)
        pad1 = lp.get('pad_end', 0.05)
        span_u = (max(ys_u[0], su[0] - pad0), min(ys_u[-1], su[1] + pad1))
        span_l = (max(ys_l[0], sl[0] - pad0), min(ys_l[-1], sl[1] + pad1))
        _lip_bourrelet('lip_u', upper, span_u, W, skin, out, n=n_lip,
                       thickness=lp.get('thickness_upper', 0.032),
                       w_frac=lp.get('w_frac_upper', 0.92), z_frac=lp.get('z_frac_upper', -0.28),
                       flex=upper_flex, ys_flex=ys_u, noise_scale=lp.get('noise_scale', 0.16),
                       noise_strength=lp.get('noise_strength', 0.4), seed=0.0)
        _lip_bourrelet('lip_l', lower, span_l, WJ, skin, out, n=n_lip,
                       thickness=lp.get('thickness_lower', 0.028),
                       w_frac=lp.get('w_frac_lower', 0.90), z_frac=lp.get('z_frac_lower', 0.22),
                       flex=lower_flex, ys_flex=ys_l, noise_scale=lp.get('noise_scale', 0.16),
                       noise_strength=lp.get('noise_strength', 0.4), seed=1.7)

    # --- EyeBuilder (boucle 17 CR3, feedback B) : globe ISOLÉ (un seul objet, un seul
    # matériau `eye_globe` à gradient nodal sclère->iris->pupille fente verticale, cf.
    # `materials.eye_globe`) au lieu d'un empilement sclère+iris+pupille en 3 disques
    # sur un matériau émissif plat -- regard qui accroche la lumière (spéculaire bas +
    # clearcoat) plutôt qu'un flat-color mort. Paupières : anneau de 4 bourrelets
    # APLATIS (haut/bas/avant/arrière, pas des sphères) fondus à la peau, qui referment
    # l'orbite autour du globe. Objet + matériau restent séparés du reste de la tête
    # (préfixes `eye_`/`lid_` déjà filtrés partout où nécessaire, ex. detail.armor
    # `exclude` ; aucun groupe `bake` ne cible `head` pour l'instant donc pas de risque
    # de bake croisé, mais un futur `spec['bake']` visant `head` devra lister ces
    # préfixes dans `exclude_like`, même convention que `bake.gather_group_objects`).
    # convention de profondeur (axe X local = normale de la calotte/axe de vue,
    # cf. docstring `materials.eye_globe`) : le globe est placé au PLUS LOIN (`ex`
    # plein) pour poker à travers l'ouverture, les 4 bourrelets de paupière sont
    # RECULÉS (`ex*0.72`, X peu profond) pour rester un anneau de rebord fondu à la
    # peau plutôt qu'une masse qui recouvre toute la calotte visible du globe (bug
    # corrigé boucle 17 : les anciennes paupières, centrées plus en avant que le
    # globe, le cachaient entièrement -> "regard mort" par occlusion, pas seulement
    # par matériau plat).
    eye_m = _mat(mats, eyep.get('mat', 'eye'))
    # bourrelet supérieur (feedback boucle 18 pt2, « yeux = disques dorés plats ») :
    # `lid_upper_scale`/`lid_upper_zfrac` (rétro-compat, défauts = valeurs historiques
    # 0.30/0.5/0.24 et 0.74) permettent depuis la spec un capuchon plus couvrant qui
    # referme le haut du globe (regard « prédateur » mi-clos) sans dupliquer le
    # builder ni changer la géométrie des autres paupières.
    lus = eyep.get('lid_upper_scale', (0.30, 0.5, 0.24))
    luz = eyep.get('lid_upper_zfrac', 0.74)
    for s, tag in ((1, 'l'), (-1, 'r')):
        g = ops.blob(f'eye_{tag}', W((s * ex, ey - 0.006, ez)), (egr, egr, egr))
        materials.assign(g, eye_m)
        out.append(g)
        lu = ops.blob(f'lid_up_{tag}', W((s * ex * 0.72, ey + 0.02, ez + esr * luz)),
                      (esr * lus[0], esr * lus[1], esr * lus[2]), rot_deg=(0, 0, s * 10))
        materials.assign(lu, skin)
        out.append(lu)
        ll = ops.blob(f'lid_lo_{tag}', W((s * ex * 0.72, ey - 0.018, ez - esr * 0.72)),
                      (esr * 0.28, esr * 0.46, esr * 0.20))
        materials.assign(ll, skin)
        out.append(ll)
        lf = ops.blob(f'lid_fr_{tag}', W((s * ex * 0.72, ey + esr * 0.68, ez)),
                      (esr * 0.26, esr * 0.20, esr * 0.42), rot_deg=(0, 22, 0))
        materials.assign(lf, skin)
        out.append(lf)
        lb = ops.blob(f'lid_bk_{tag}', W((s * ex * 0.72, ey - esr * 0.64, ez)),
                      (esr * 0.24, esr * 0.18, esr * 0.38), rot_deg=(0, -20, 0))
        materials.assign(lb, skin)
        out.append(lb)

    # --- naseaux (suite) : cavité sombre logée sous l'ouverture carvée (donne la
    # profondeur qu'on ne voit pas dans le trou seul) + monticule charnu EN REBORD
    # (feedback boucle 18 pt4 : l'ancien monticule, plus grand que le trou et centré
    # dessus, l'ENGLOUTISSAIT entièrement -> aucune ouverture visible malgré un vrai
    # trou dans le maillage, cf. diagnostic bmesh boundary-edges). Le monticule est
    # maintenant plus PETIT que l'ouverture et poussé plus bas/profond : son sommet
    # reste sous le centre du trou -> il forme juste une lèvre charnue basse, le
    # reste de l'ouverture (haut) restant un vrai creux visible. ---
    for s, tag in ((1, 'l'), (-1, 'r')):
        cx, cy, cz = s * npos[0], npos[1], npos[2]
        cavity = ops.blob(f'nostril_cavity_{tag}', W((cx * 1.02, cy + nk * 0.3, cz - nk * 0.15)),
                          (nk * 0.7, nk * 1.0, nk * 0.55), rot_deg=(pitch - 18, 0, s * 20))
        # 'cavity' (pas 'eye' -> ce matériau est désormais le globe à gradient nodal
        # spéculaire de l'EyeBuilder, inadapté à une simple cavité sombre) : dark mat
        # neutre générique.
        materials.assign(cavity, _mat(mats, np_.get('cavity_mat', 'cavity')) or skin)
        out.append(cavity)
        mound = ops.blob(f'nose_mound_{tag}', W((cx, cy - nk * 0.25, cz - nk * 1.0)),
                         (nk * 1.35, nk * 1.55, nk * 0.6), rot_deg=(pitch - 8, 0, s * 14))
        materials.assign(mound, skin)
        out.append(mound)

    # --- traits fondus génériques pilotés par la spec : crêtes (`ridges`, tube fin
    # suivant des points) et masses charnues (`face_blobs`, blob aplati/allongé).
    # Aucune valeur dragon ici : sourcils, joues, menton, lèvres... tout vient du JSON.
    def _space(sp):
        return WJ if sp == 'jaw' else W

    for r in part.get('ridges', []):
        Wf = _space(r.get('space'))
        pts = r['pts']
        radii = r.get('radii', [0.02] * len(pts))
        sides = ((1, 'l'), (-1, 'r')) if r.get('mirror', True) else ((1, ''),)
        for s, tag in sides:
            wp = [Wf((s * x, y, z)) for x, y, z in pts]
            t = ops.tube(f"ridge_{r.get('id', 'r')}_{tag}", wp, radii)
            materials.assign(t, skin)
            out.append(t)

    for fb in part.get('face_blobs', []):
        Wf = _space(fb.get('space'))
        pos = fb['pos']
        scale = fb.get('scale', (0.05, 0.05, 0.03))
        rot = fb.get('rot', (0, 0, 0))
        sides = ((1, 'l'), (-1, 'r')) if fb.get('mirror', True) else ((1, ''),)
        for s, tag in sides:
            b = ops.blob(f"face_{fb.get('id', 'b')}_{tag}",
                        Wf((s * pos[0], pos[1], pos[2])), scale,
                        rot_deg=(rot[0], rot[1], s * rot[2]))
            materials.assign(b, skin)
            out.append(b)

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
    # `n` (rétro-compat défaut 16, comme avant) : densité de points de contrôle du
    # profil de corne. Les anneaux de croissance modulent le rayon PAR POINT sur une
    # NURBS cubique qui LISSE fortement un profil trop clairsemé (un anneau isolé sur
    # 1 seul point voisin de valeurs plates est quasi entièrement absorbé) -> avec
    # `rings`, on veut plus de points pour que chaque anneau couvre 3-4 points de
    # contrôle et reste visible après lissage.
    n_horn = hp.get('n', 16)
    raw = apply_law(hp.get('vocab', 'growth.horn_spiral'),
                    n=n_horn, a=hp.get('a', 0.10), b=hp.get('b', 0.30),
                    turns=hp.get('turns', 0.6), rise=hp.get('rise', 0.55))
    base_radii = laws.power_taper(n_horn, hp.get('r0', 0.075), 1.15, 0.008)
    # relief kératine générique (rétro-compat : neutre si `rings`/`curl`/`root_len`
    # absents de la spec) : anneaux de croissance + légère torsion de pointe + base
    # élargie fondue dans le crâne (prolonge la base vers l'intérieur, cf. doctrine
    # « mound enfoncé aux 2/3 » déjà utilisée pour les naseaux) au lieu d'un cône nu
    # planté sur la surface.
    raw, base_radii = _apply_horn_growth(
        raw, base_radii, ring_p=hp.get('rings'),
        curl=hp.get('curl', 0.0), curl_power=hp.get('curl_power', 1.6),
        root_len=hp.get('root_len', 0.0), root_bulge=hp.get('root_bulge', 1.0))
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
            # résolution réduite (budget sommets) : `n_horn` points de contrôle portent
            # déjà le détail (anneaux), la résolution NURBS/bevel par défaut (pensée
            # pour des tubes à peu de points, ex. dents/crêtes) est inutilement dense.
            h = ops.tube(f'horn_{tag}{k}', pts, radii, resolution_u=6, bevel_resolution=6)
            materials.assign(h, bone_m)
            out.append(h)
    # petites cornes d'arcade + pointes de joue (ancrées sur l'os, base large) ;
    # feature_scale suit l'agrandissement du crâne (positions ET tailles locales).
    # `secondary` (sous-dict de `horns`, rétro-compat neutre si absent) : mêmes
    # anneaux/courbure/base fondue que les cornes maîtresses mais plus discrets —
    # remplace le cône `ops.spike` planté par une petite pointe kératineuse profilée.
    hk = part.get('feature_scale', 1.0)
    sec = hp.get('secondary', {})
    sec_ring = sec.get('rings')
    sec_curl = sec.get('curl', 0.0)
    sec_root_len = sec.get('root_len', 0.0) * hk
    sec_root_bulge = sec.get('root_bulge', 1.0)
    sec_n = sec.get('n', 6)
    for s, tag in ((1, 'l'), (-1, 'r')):
        b = _kera_spike(f'horn_brow_{tag}', W((s * 0.22 * hk, 0.38 * hk, 0.26 * hk)),
                        0.14 * hk, 0.038 * hk, (pitch - 35, 0, s * 15), bone_m,
                        ring_p=sec_ring, curl=sec_curl, root_len=sec_root_len,
                        root_bulge=sec_root_bulge, n=sec_n)
        out.append(b)
        c = _kera_spike(f'horn_cheek_{tag}', W((s * 0.30 * hk, 0.12 * hk, -0.02 * hk)),
                        0.16 * hk, 0.048 * hk, (pitch + 95, 0, s * 55), bone_m,
                        ring_p=sec_ring, curl=sec_curl, root_len=sec_root_len,
                        root_bulge=sec_root_bulge, n=sec_n)
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
    """Aile-planche à voile : bras COURT et anguleux (mât) + doigts osseux longs en
    éventail (lattes de renfort), membrane DOMINANTE à volume dégradé — épaisse le long
    des os (racine), fine au bord libre — avec nervures/lattes couchées sur la surface
    entre les doigts, affaissement caténaire. Tout est piloté par la spec (`arm_radii`,
    `arm_order`, `thickness_root/edge`, `battens_per_panel`, `finger_r0/rmin`...)."""
    out = []
    sides = [1, -1] if part.get('side', 'both') == 'both' else [1]
    base_sag = part.get('sag', 0.55)
    nt = part.get('samples', 9)
    sub = part.get('columns_between', 4)
    arm_radii = part.get('arm_radii', [0.22, 0.16, 0.12])
    arm_order = part.get('arm_order', 2)  # 2 = segments droits -> coude anguleux (réf)
    th_root = part.get('thickness_root', 0.06)
    th_edge = part.get('thickness_edge', 0.012)
    bp = part.get('battens_per_panel', 0)
    batten_r0 = part.get('batten_r0', 0.05)
    batten_rmin = part.get('batten_rmin', 0.008)
    batten_lift = part.get('batten_lift', 0.012)
    # batten_start (défaut 0, rétro-compat) : fraction de la corde (racine->bord
    # libre) où démarrent les lattes -> détachées du poignet/bras, elles lisent
    # comme des veines de membrane plutôt que des tiges qui rayonnent depuis l'os.
    batten_start = max(0.0, min(0.95, part.get('batten_start', 0.0)))
    bone_mat_key = part.get('bone_mat', 'scales')
    # camber (v3, anti-origami) : bombé chordwise (racine->bord libre, via `t`) qui
    # s'ajoute au sag existant (bombé envergure, via `u`) -> double courbure au lieu
    # d'une surface réglée plate facettée. festoon : bord de fuite légèrement festonné
    # entre les doigts (tiré vers le poignet au milieu de chaque panneau, nul aux
    # doigts) -> silhouette membraneuse au lieu d'un polygone droit entre les pointes.
    base_camber = part.get('camber', 0.0)
    base_festoon = part.get('festoon', 0.0)
    finger_lift = part.get('finger_lift', batten_lift)
    # finger_bow (anti-parapluie) : les doigts (et les colonnes de membrane collées
    # dessus) ne sont plus des rayons rectilignes W->tip mais des arcs -> flèche
    # perpendiculaire à la direction du doigt, nulle aux 2 bouts (poignet/pointe),
    # maximale à mi-longueur, dans le plan horizontal de la membrane, du côté du
    # bord de fuite (repéré via `anchor`, générique -> aucune valeur dragon en dur).
    base_finger_bow = part.get('finger_bow', 0.0)
    finger_taper = part.get('finger_taper', 1.1)
    # panel_billow : bombé/creux charnu par panneau (entre 2 doigts), fonction du
    # u_local du panneau (0 aux doigts, max au milieu) et du t le long de la corde
    # -> remplace le plan réglé par une membrane qui gonfle/s'affaisse localement.
    base_panel_billow = part.get('panel_billow', 0.0)
    # knuckles_per_finger (T18, défaut 0 -> rétro-compat) : articulations le long de
    # chaque doigt — renflements du rayon du tube à N positions régulières entre le
    # poignet/knuckle et la pointe, comme des phalanges. Générique : dérivé de `fr`
    # (rayon déjà calculé par doigt), aucune valeur dragon en dur.
    knuckles_per_finger = int(part.get('knuckles_per_finger', 0))
    knuckle_bulge = part.get('knuckle_bulge', 0.4)
    knuckle_width = max(0.01, part.get('knuckle_width', 0.07))

    def apply_knuckles(radii):
        if knuckles_per_finger <= 0:
            return radii
        n = len(radii)
        out = list(radii)
        for k in range(1, knuckles_per_finger + 1):
            frac = k / (knuckles_per_finger + 1)
            for i in range(n):
                t = i / (n - 1) if n > 1 else 0.0
                d = (t - frac) / knuckle_width
                out[i] *= 1.0 + knuckle_bulge * math.exp(-0.5 * d * d)
        return out

    # wclaw_len/wclaw_r/wclaw_rot (T18, rétro-compat sur les défauts historiques) :
    # dimensionne/oriente la griffe de bout de doigt depuis la spec au lieu d'une
    # valeur figée dans le code.
    wclaw_len = part.get('wclaw_len', 0.22)
    wclaw_r = part.get('wclaw_r', 0.05)
    wclaw_rot = tuple(part.get('wclaw_rot', (150, 0, 0)))
    # claw_mat (défaut = bone_mat, rétro-compat via 'bone' historique quand bone_mat
    # vaut 'scales' -> _mat retombe sur le comportement d'avant si non précisé) :
    # les griffes de doigt/alula suivent le matériau OS de l'aile (dédié, n'affecte
    # pas les griffes de patte/dorsales qui restent câblées sur 'bone').
    claw_mat_key = part.get('claw_mat', bone_mat_key)
    for s in sides:
        tag = 'L' if s > 0 else 'R'
        # pose (T17 CR2, pose dynamique) : override PAR CÔTÉ, appliqué APRÈS le
        # miroir -> battement asymétrique générique (virage banqué : une aile haute
        # tendue, l'autre basse en appui) sans dupliquer le builder. `shoulder`/
        # `anchor`/`root_curve` restent FIXES (attache torse/hanche, doctrine
        # "nageoire") : seuls le bras (coude/poignet, `elbow_dz`/`wrist_dz`) et les
        # pointes (`tips_dz`/`tips_dy`) bougent, plus des multiplicateurs de relief
        # (`sag_mult`/`camber_mult`/`panel_billow_mult`/`finger_bow_mult`/
        # `festoon_mult`) -> la membrane se redrape depuis une racine ancrée, pas de
        # décollement. Rétro-compat totale : sans `pose` dans la spec, `pov={}` ->
        # tous les multiplicateurs valent 1.0 et les deltas 0.0, comportement inchangé.
        pov = (part.get('pose') or {}).get(tag, {})
        sag = base_sag * pov.get('sag_mult', 1.0)
        camber = base_camber * pov.get('camber_mult', 1.0)
        panel_billow = base_panel_billow * pov.get('panel_billow_mult', 1.0)
        finger_bow = base_finger_bow * pov.get('finger_bow_mult', 1.0)
        festoon = base_festoon * pov.get('festoon_mult', 1.0)
        sh = (s * part['shoulder'][0], part['shoulder'][1], part['shoulder'][2])
        el = (s * part['elbow'][0], part['elbow'][1], part['elbow'][2] + pov.get('elbow_dz', 0.0))
        wr = (s * part['wrist'][0], part['wrist'][1], part['wrist'][2] + pov.get('wrist_dz', 0.0))
        # anatomie du bras (épaule/biceps + avant-bras, coude en articulation nette,
        # cf. `_anatomical_tube`) : rétro-compat totale, tube NURBS d'origine si
        # `muscles`/`joints`/`folds` absents de la spec (comportement inchangé).
        if part.get('muscles') or part.get('joints') or part.get('folds'):
            arm = _anatomical_tube(f'arm_{tag}', [sh, el, wr], arm_radii,
                                   muscles=part.get('muscles'), joints=part.get('joints'),
                                   folds=part.get('folds'), mirror_sign=s)
        else:
            arm = ops.tube(f'arm_{tag}', [sh, el, wr], arm_radii, order=arm_order)
        materials.assign(arm, _mat(mats, bone_mat_key))
        out.append(arm)
        rays = [tuple((s * p[0], p[1], p[2])) for p in part['tips']]
        tips_dz = pov.get('tips_dz')
        tips_dy = pov.get('tips_dy')
        if tips_dz or tips_dy:
            rays = [(r[0], r[1] + (tips_dy[i] if tips_dy and i < len(tips_dy) else 0.0),
                    r[2] + (tips_dz[i] if tips_dz and i < len(tips_dz) else 0.0))
                    for i, r in enumerate(rays)]
        anchor = (s * part['anchor'][0], part['anchor'][1], part['anchor'][2])
        W = Vector(wr)

        # direction de flèche (bow) par doigt : perpendiculaire horizontale à W->tip,
        # signe choisi du côté du bord de fuite (vers `anchor`) -> même sens pour
        # tous les doigts, éventail cohérent (pas de valeur dragon en dur).
        finger_dirs = []
        for tip in rays:
            d = Vector(tip) - W
            d.z = 0.0
            dn = d.normalized() if d.length > 1e-6 else Vector((1.0, 0.0, 0.0))
            finger_dirs.append(Vector((-dn.y, dn.x, 0.0)))
        ref = Vector(anchor) - W
        ref.z = 0.0
        if ref.length > 1e-6:
            for i, perp in enumerate(finger_dirs):
                if perp.dot(ref) < 0:
                    finger_dirs[i] = -perp

        # knuckle_spread (défaut 0, rétro-compat) : masse carpienne — les doigts
        # n'émergent plus tous du même point W (éclatement en rayons filaires) mais
        # d'origines échelonnées le long d'une courte courbe carpienne, prolongement
        # de la direction coude->poignet. Le doigt du bord d'attaque (rays[0]) part
        # le plus loin, celui du bord de fuite (dernier) le plus tôt -> comme une
        # main, transition continue au lieu d'un point d'éclatement unique. Aucune
        # constante dragon : direction et ordre dérivés de `elbow`/`wrist`/`tips`.
        knuckle_spread = part.get('knuckle_spread', 0.0)
        n_fingers = len(rays)
        dc = W - Vector(el)
        dir_carpe = dc.normalized() if dc.length > 1e-6 else Vector((1.0, 0.0, 0.0))

        def finger_frac(j):
            return (n_fingers - 1 - j) / (n_fingers - 1) if n_fingers > 1 else 0.0

        knuckles = [W + dir_carpe * (knuckle_spread * finger_frac(j)) for j in range(n_fingers)]

        if knuckle_spread > 0 and n_fingers > 0:
            hand_r0 = arm_radii[-1] * 1.05
            hand_r1 = max(part.get('finger_r0', 0.085) * 0.9, arm_radii[-1] * 0.5)
            far = knuckles[0]
            hand_pts = [W, W.lerp(far, 0.55), far]
            hand_radii = [hand_r0, (hand_r0 + hand_r1) * 0.5, hand_r1]
            hand = ops.tube(f'hand_{tag}', [tuple(p) for p in hand_pts], hand_radii)
            materials.assign(hand, _mat(mats, bone_mat_key))
            out.append(hand)

        def col_pts(root_pt, e, u, bow_perp=None, t0=0.0):
            pts = []
            for i in range(nt):
                tt = i / (nt - 1)
                t = t0 + (1.0 - t0) * tt
                v = root_pt.lerp(e, t)
                v.z -= sag * math.sin(math.pi * u) * t
                v.z += camber * math.sin(math.pi * t)
                v.z -= panel_billow * math.sin(math.pi * u) * math.sin(math.pi * t)
                if bow_perp is not None and finger_bow:
                    v += bow_perp * (finger_bow * math.sin(math.pi * t))
                pts.append(v)
            return pts

        def edge_pt(a, b, u, fest, chord_scale=1.0):
            """Point de bord (bord libre/de fuite) entre 2 doigts, tiré vers le
            poignet W au milieu du panneau si `fest` (festonnage), nul aux doigts
            (u=0/1) -> pas de valeur dragon en dur, juste une fraction de la corde.
            `chord_scale` normalise la profondeur du feston par la largeur locale du
            panneau (moyenne des panneaux) pour rester homogène entre panneaux
            étroits et larges."""
            e = a.lerp(b, u)
            if fest:
                dirv = e - W
                if dirv.length > 1e-6:
                    e = e - dirv.normalized() * (fest * chord_scale * math.sin(math.pi * u))
            return e

        ends = rays + [anchor]
        # largeur moyenne des panneaux festonnés (doigt->doigt, hors panneau d'ancrage
        # à la hanche) -> référence pour `chord_scale`.
        fest_widths = [(Vector(ends[j + 1]) - Vector(ends[j])).length
                       for j in range(len(ends) - 2)]
        ref_width = (sum(fest_widths) / len(fest_widths)) if fest_widths else 1.0
        col_defs = []
        col_bow = []
        col_knuckle = []  # décalage de racine par colonne (aligne la bande de membrane
        # d'un doigt sur son knuckle échelonné, cf. `knuckle_spread`) -> nul partout
        # sauf sur la colonne du doigt lui-même (k==0), sinon la membrane resterait
        # ancrée à W pendant que le doigt (bourrelet) démarre plus loin -> décollement.
        seg_bounds = []  # (index de départ, nb de colonnes) par segment j -> réutilisé par les lattes
        for j in range(len(ends) - 1):
            a, b = Vector(ends[j]), Vector(ends[j + 1])
            steps = sub if j < len(ends) - 2 else sub + 2
            seg_bounds.append((len(col_defs), steps))
            fest = festoon if j < len(ends) - 2 else 0.0  # pas de feston sur le panneau d'ancrage (hanche)
            width = (b - a).length
            chord_scale = (width / ref_width) if (fest and ref_width > 1e-6) else 1.0
            for k in range(steps):
                u = k / steps
                col_defs.append((edge_pt(a, b, u, fest, chord_scale), u))
                is_finger_root = k == 0 and j < len(rays)
                col_bow.append(finger_dirs[j] if is_finger_root else None)
                col_knuckle.append((knuckles[j] - W) if is_finger_root else Vector((0.0, 0.0, 0.0)))
        col_defs.append((Vector(anchor), 1.0))
        col_bow.append(None)
        col_knuckle.append(Vector((0.0, 0.0, 0.0)))

        # root_curve (aile « nageoire », doctrine axe 2 attachment_curve) : la racine
        # de la membrane suit une polyligne le long du flanc (épaule->hanche) au lieu
        # de converger au seul point du poignet W -> la membrane rejoint le corps sur
        # toute son envergure, comme une nageoire, au lieu d'un lien unique. `gu`
        # (fraction globale 0..1 le long de tout le contour bord d'attaque/libre) sert
        # de paramètre commun colonnes+lattes. Rétro-compat : sans `root_curve` dans
        # la spec, root_pt = W pour toutes les colonnes (comportement identique à avant).
        rc = part.get('root_curve')
        total = len(col_defs)
        denom = max(1, total - 1)
        if rc:
            off = abs(part.get('root_offset', 0.02))  # décalage vers l'intérieur (flanc)
            root_world = [(s * (x - off), y, z) for x, y, z in rc]

            def flank_root_at(gu):
                return Vector(laws.sample_path(root_world, gu))
        else:
            def flank_root_at(gu):
                return W

        # root_follow_arm (défaut 0, fraction 0..1, rétro-compat) : au lieu d'une
        # racine de membrane entièrement plaquée au flanc (root_curve) alors que le
        # bras passe au-dessus -> lecture "nageoire collée", décalée en z -> la
        # partie AVANT de la racine (gu proche de 0, adjacente au poignet/1er doigt)
        # suit le dessous du bras (épaule->coude->poignet, décalé de -z de son rayon
        # local) : la membrane s'accroche SOUS l'os. S'estompe vers root_curve
        # (flanc) à mi-parcours de la racine (`front_extent`) ; la partie arrière
        # (vers l'ancrage/hanche) reste inchangée. camber/panel_billow/sag valent
        # déjà 0 en t=0 (racine, sin(pi*0)=0) donc n'ont pas besoin d'amortissement
        # séparé : la racine suit exactement `root_at`.
        root_follow = max(0.0, min(1.0, part.get('root_follow_arm', 0.0)))
        arm_poly = [tuple(sh), tuple(el), tuple(wr)]
        arm_rad_pts = [(r, 0.0, 0.0) for r in arm_radii]

        def arm_root_at(t):
            p = Vector(laws.sample_path(arm_poly, t))
            r = laws.sample_path(arm_rad_pts, t)[0]
            return Vector((p.x, p.y, p.z - r))

        if root_follow > 0:
            front_extent = 0.5

            def root_at(gu):
                flank = flank_root_at(gu)
                if gu >= front_extent:
                    return flank
                w = root_follow * (1.0 - gu / front_extent)
                arm_pt = arm_root_at(1.0 - gu / front_extent)
                return flank.lerp(arm_pt, w)
        else:
            root_at = flank_root_at

        def global_u(j, u_local):
            cum_start, steps = seg_bounds[j]
            return (cum_start + u_local * steps) / denom

        cols = [[tuple(v) for v in col_pts(root_at(gi / denom) + col_knuckle[gi], e, u, col_bow[gi])]
               for gi, (e, u) in enumerate(col_defs)]
        # épaisseur dégradée par rangée : racine (i=0, le long des os) épaisse, bord
        # libre (dernière rangée) fin -> remplace le Solidify constant, donne le
        # volume "planche à voile" au lieu d'une membrane plate.
        thickness_rows = [th_root + (th_edge - th_root) * (i / (nt - 1)) ** 0.7
                          for i in range(nt)]
        mem = ops.grid_surface(f'membrane_{tag}', cols, thickness=thickness_rows)
        materials.assign(mem, _mat(mats, part.get('mat', 'membrane')))
        out.append(mem)
        # lattes (battens) : nervures fines couchées sur la membrane entre les doigts,
        # de la racine au bord libre — mêmes proportions qu'une voile lattée.
        if bp:
            batten_radii = laws.power_taper(nt, batten_r0, 1.2, batten_rmin)
            for j in range(len(ends) - 1):
                a, b = Vector(ends[j]), Vector(ends[j + 1])
                fest = festoon if j < len(ends) - 2 else 0.0
                width = (b - a).length
                chord_scale = (width / ref_width) if (fest and ref_width > 1e-6) else 1.0
                for bi in range(bp):
                    u = (bi + 1) / (bp + 1)
                    gu = global_u(j, u)
                    bpts = [(v.x, v.y, v.z + batten_lift)
                            for v in col_pts(root_at(gu), edge_pt(a, b, u, fest, chord_scale), u,
                                             t0=batten_start)]
                    batt = ops.tube(f'batten_{tag}{j}_{bi}', bpts, batten_radii)
                    materials.assign(batt, _mat(mats, bone_mat_key))
                    out.append(batt)
        # veines secondaires (vein_branches, défaut 0 → rétro-compat) : 2e GÉNÉRATION
        # de nervures, fines, qui partent de chaque doigt (pas de la racine) et
        # rayonnent en biais vers le bord de fuite du panneau voisin — anatomie de
        # membrane (cf. réf. drogon_wing_membrane : nervures ramifiées en Y depuis les
        # doigts), par opposition aux lattes primaires qui sont rectilignes racine->
        # bord. Suivent le même relief (sag/camber/panel_billow) que les colonnes de
        # membrane -> restent COLLÉES à la surface plutôt que de flotter au-dessus ;
        # rayon ~1/3 d'une latte (`vein_branch_r0`), tube très bas poly (ornemental).
        vein_branches = part.get('vein_branches', 0)
        if vein_branches:
            vein_r0 = part.get('vein_branch_r0', batten_r0 / 3.0)
            vein_rmin = part.get('vein_branch_rmin', vein_r0 * 0.3)

            def finger_pt(j, t):
                v = knuckles[j].lerp(Vector(rays[j]), t)
                if finger_bow:
                    v = v + finger_dirs[j] * (finger_bow * math.sin(math.pi * t))
                return Vector((v.x, v.y, v.z + finger_lift))

            def panel_pt(j, u, t):
                a, b = Vector(ends[j]), Vector(ends[j + 1])
                fest = festoon if j < len(ends) - 2 else 0.0
                width = (b - a).length
                chord_scale = (width / ref_width) if (fest and ref_width > 1e-6) else 1.0
                e = edge_pt(a, b, u, fest, chord_scale)
                root = root_at(global_u(j, u))
                v = root.lerp(e, t)
                v.z -= sag * math.sin(math.pi * u) * t
                v.z += camber * math.sin(math.pi * t)
                v.z -= panel_billow * math.sin(math.pi * u) * math.sin(math.pi * t)
                return v

            for j in range(len(ends) - 1):
                for bi in range(vein_branches):
                    frac = (bi + 1) / (vein_branches + 1)
                    t_start = 0.18 + 0.12 * bi   # démarre au tiers proximal du doigt
                    t_end = 0.92 - 0.08 * bi     # s'approche du bord libre sans l'atteindre
                    u_end = 0.22 + 0.5 * frac    # s'écarte du doigt vers le panneau voisin
                    p0 = finger_pt(j, t_start)
                    p1 = panel_pt(j, u_end, t_end)
                    pmid = p0.lerp(p1, 0.5)
                    vr = laws.power_taper(3, vein_r0, 1.1, vein_rmin)
                    vtube = ops.tube(f'vein_{tag}{j}_{bi}', [tuple(p0), tuple(pmid), tuple(p1)],
                                     vr, resolution_u=4, bevel_resolution=3)
                    materials.assign(vtube, _mat(mats, bone_mat_key))
                    out.append(vtube)
        # doigts osseux : bourrelets SAILLANTS posés SUR la membrane (relief), pas des
        # tiges flottantes séparées -> soulevés de `finger_lift` le long de z (même
        # convention que les lattes) pour lire comme une arête en relief sur la surface.
        # Arqués (finger_bow) en éventail au lieu de rayons rectilignes W->tip.
        fr = apply_knuckles(laws.power_taper(nt, part.get('finger_r0', 0.085), finger_taper,
                              part.get('finger_rmin', 0.015)))
        for j, tip in enumerate(rays):
            perp = finger_dirs[j]
            knuckle = knuckles[j]
            fpts = []
            for i in range(nt):
                t = i / (nt - 1)
                v = knuckle.lerp(Vector(tip), t)
                if finger_bow:
                    v = v + perp * (finger_bow * math.sin(math.pi * t))
                fpts.append((v.x, v.y, v.z + finger_lift))
            f = ops.tube(f'finger_{tag}{j}', fpts, fr)
            materials.assign(f, _mat(mats, bone_mat_key))
            out.append(f)
            claw = ops.spike(f'wclaw_{tag}{j}', (tip[0], tip[1], tip[2] + finger_lift),
                             wclaw_len, wclaw_r, wclaw_rot)
            materials.assign(claw, _mat(mats, claw_mat_key))
            out.append(claw)

        # alula (T18, défaut None -> rétro-compat) : petit "pouce" court partant du
        # poignet vers l'avant/haut (repère générique : côté opposé au bord de fuite,
        # cf. `finger_dirs`/`ref` déjà calculés plus haut), avec sa griffe et sa micro-
        # membrane triangulaire — réutilise EXACTEMENT la machinerie fingers/membrane
        # (col_pts, power_taper, ops.tube/spike/grid_surface), aucune géométrie neuve.
        alula = part.get('alula')
        if alula:
            a_tip_spec = alula['tip']
            a_tip = (s * a_tip_spec[0], a_tip_spec[1], a_tip_spec[2])
            a_r0 = alula.get('r0', part.get('finger_r0', 0.085) * 0.45)
            a_rmin = alula.get('rmin', a_r0 * 0.3)
            a_claw = alula.get('claw', 0.12)
            a_radii = laws.power_taper(nt, a_r0, finger_taper, a_rmin)
            a_pts = [(v.x, v.y, v.z + finger_lift)
                     for v in [W.lerp(Vector(a_tip), i / (nt - 1)) for i in range(nt)]]
            afin = ops.tube(f'alula_{tag}', a_pts, a_radii)
            materials.assign(afin, _mat(mats, bone_mat_key))
            out.append(afin)
            aclaw = ops.spike(f'aclaw_{tag}', (a_tip[0], a_tip[1], a_tip[2] + finger_lift),
                              a_claw, a_claw * 0.4, wclaw_rot)
            materials.assign(aclaw, _mat(mats, claw_mat_key))
            out.append(aclaw)
            # micro-membrane triangulaire : colonne racine (le long de l'avant-bras,
            # entre coude et poignet, sur sa portion proche du poignet) + colonne du
            # doigt (poignet -> pointe alula) -> 2 colonnes, même fonction `col_pts`
            # que la membrane principale (sag/camber nuls car u=0/1 -> juste le camber).
            arm_base = Vector(el).lerp(W, alula.get('root_frac', 0.65))
            arm_col = [tuple(v) for v in col_pts(arm_base, W, 0.0)]
            tip_col = [tuple(v) for v in col_pts(W, Vector(a_tip), 1.0)]
            a_mem = ops.grid_surface(f'alula_mem_{tag}', [arm_col, tip_col],
                                     thickness=[t * 0.55 for t in thickness_rows])
            materials.assign(a_mem, _mat(mats, part.get('mat', 'membrane')))
            out.append(a_mem)
    return out


def _frame_init(tangent):
    """Premier repère orthonormal (right/up) perpendiculaire à `tangent`, à partir
    d'une référence monde stable (Z, ou Y si `tangent` est quasi vertical)."""
    ref = Vector((0.0, 0.0, 1.0))
    if abs(tangent.dot(ref)) > 0.9:
        ref = Vector((0.0, 1.0, 0.0))
    right = tangent.cross(ref)
    if right.length < 1e-6:
        right = Vector((1.0, 0.0, 0.0))
    right.normalize()
    up = tangent.cross(right).normalized()
    return right, up


def _frame_step(prev_tangent, prev_right, tangent):
    """Transport du repère (right/up) d'un segment au suivant par rotation MINIMALE
    (rotation-minimizing frame, méthode à réflexion simple) : évite la torsion
    visible qu'un recalcul depuis une référence monde fixe provoquerait à chaque
    changement d'angle notable (coude, cheville...)."""
    axis = prev_tangent.cross(tangent)
    sina = axis.length
    cosa = max(-1.0, min(1.0, prev_tangent.dot(tangent)))
    if sina < 1e-8:
        right = Vector(prev_right)
    else:
        axis = axis / sina
        angle = math.atan2(sina, cosa)
        right = Quaternion(axis, angle) @ prev_right
    right = right - tangent * right.dot(tangent)
    if right.length < 1e-6:
        right, _ = _frame_init(tangent)
    else:
        right.normalize()
    up = tangent.cross(right).normalized()
    return right, up


def _anatomical_tube(name, pts, radii, muscles=None, joints=None, folds=None,
                     n_ring=10, seg_samples=10, subsurf_levels=1, mirror_sign=1.0):
    """Loft anatomique GÉNÉRIQUE pour un membre/bras (`limb`/`wing`) : chaîne de
    sections ELLIPTIQUES le long de la polyligne de contrôle `pts`/`radii` (comme
    `ops.tube`, section ronde à rayon interpolé linéairement, si `muscles`/`joints`/
    `folds` sont absents -> comportement équivalent, juste loft mesh au lieu de
    courbe NURBS+bevel). Trois modulations pilotées PAR SPEC, aucune valeur dragon :

    `muscles` : [{seg, t0, t1, bulge, squash, peak, twist}] — masse fusiforme entre
    deux points de contrôle (`seg` = index du 1er point du segment), enveloppe
    `growth.muscle_bulge` (pic asymétrique vers `peak`, défaut 0.35 = haut du
    segment). `bulge` gonfle le rayon "large" (axe local `right`), `squash` (<1)
    aplatit l'axe local `up` en proportion -> section elliptique, pas un ballon rond
    ("effet saucisse" évité). `twist` (deg) tourne le repère localement (relief).

    `joints` : [{at, r, w, sharp}] — renflement osseux étroit au point de contrôle
    `at`, enveloppe `growth.joint_bump` (gaussienne resserrée par `sharp`) — casse la
    silhouette net (contrairement au bulge musculaire, large et progressif).

    `folds` : [{at, n, depth, width, side, min_angle_deg}] — plis de compression
    (`growth.fold_rings`) côté INTÉRIEUR (concave) du pli formé aux 2 segments
    adjacents à `at`, ignorés si l'angle entre segments est presque droit (< 15° par
    défaut, pas de pli sur un membre quasi tendu). Le côté intérieur est dérivé de la
    géométrie (direction sortante - direction entrante) sauf si `side` est fourni
    explicitement (repère local, mirroré par `mirror_sign`)."""
    muscles = muscles or []
    joints = joints or []
    folds = folds or []
    pv = [Vector(p) for p in pts]
    n_seg = len(pv) - 1

    def seg_dir(i):
        d = pv[i + 1] - pv[i]
        return d.normalized() if d.length > 1e-9 else Vector((0, 0, -1))

    fold_by_at = {}
    for f in folds:
        at = f.get('at')
        if at is None or at <= 0 or at >= len(pv) - 1:
            continue
        din, dout = seg_dir(at - 1), seg_dir(at)
        cosang = max(-1.0, min(1.0, din.dot(dout)))
        if math.degrees(math.acos(cosang)) < f.get('min_angle_deg', 15.0):
            continue
        if 'side' in f:
            sx, sy, sz = f['side']
            side_v = Vector((mirror_sign * sx, sy, sz))
        else:
            side_v = dout - din
        if side_v.length < 1e-6:
            continue
        side_v.normalize()
        fold_by_at[at] = dict(side=side_v, n=f.get('n', 3), depth=f.get('depth', 0.05),
                              width=f.get('width', 0.06))

    joint_by_at = {j['at']: j for j in joints if j.get('at') is not None and 0 <= j['at'] < len(pv)}
    muscles_by_seg = {}
    for m in muscles:
        muscles_by_seg.setdefault(m.get('seg', 0), []).append(m)

    rings = []
    right = up = None
    prev_tan = None
    for si in range(n_seg):
        a, b = pv[si], pv[si + 1]
        ra, rb = radii[si], radii[si + 1]
        tan = seg_dir(si)
        if right is None:
            right, up = _frame_init(tan)
        else:
            right, up = _frame_step(prev_tan, right, tan)
        prev_tan = tan
        m_list = muscles_by_seg.get(si, [])
        n_s = seg_samples if si < n_seg - 1 else seg_samples + 1
        for k in range(n_s):
            tl = min(1.0, k / seg_samples)
            center = a.lerp(b, tl)
            r = ra + (rb - ra) * tl
            rx = rz = r
            twist_deg = 0.0
            for m in m_list:
                t0, t1 = m.get('t0', 0.1), m.get('t1', 0.8)
                if t1 <= t0 or not (t0 <= tl <= t1):
                    continue
                u = (tl - t0) / (t1 - t0)
                env = apply_law('growth.muscle_bulge', u=u, peak=m.get('peak', 0.35),
                                power=m.get('power', 2.0))
                bulge = m.get('bulge', 0.3)
                sq = m.get('squash', 0.7)
                rx *= 1.0 + bulge * env
                rz *= 1.0 + bulge * env * sq
                twist_deg += m.get('twist', 0.0) * env
            for at, jd in joint_by_at.items():
                if at == si:
                    d = tl
                elif at == si + 1:
                    d = tl - 1.0
                else:
                    continue
                env = apply_law('growth.joint_bump', d=d, w=jd.get('w', 0.12),
                                sharp=jd.get('sharp', 2.0))
                rr = jd.get('r', 1.25)
                mult = 1.0 + (rr - 1.0) * env
                rx *= mult
                rz *= mult
            right_r, up_r = right, up
            if twist_deg:
                q = Quaternion(tan, math.radians(twist_deg))
                right_r, up_r = q @ right, q @ up
            ring_pts = []
            for j in range(n_ring):
                ang = 2 * math.pi * j / n_ring
                c, sn = math.cos(ang), math.sin(ang)
                local = right_r * (rx * c) + up_r * (rz * sn)
                indent = 0.0
                for at, fd in fold_by_at.items():
                    if at == si:
                        d = tl
                    elif at == si + 1:
                        d = tl - 1.0
                    else:
                        continue
                    dirn = right_r * c + up_r * sn
                    w = max(0.0, dirn.dot(fd['side']))
                    if w <= 0.0:
                        continue
                    indent += w * apply_law('growth.fold_rings', d=d, n=fd['n'],
                                            width=fd['width'], depth=fd['depth'])
                if indent:
                    local *= max(0.15, 1.0 - indent / max(r, 1e-4))
                ring_pts.append(tuple(center + local))
            rings.append(ring_pts)
    ob = ops.ring_loft(name, rings, subsurf_levels=subsurf_levels)
    return ob


@builder('limb')
def limb(part, mats):
    """Patte : tube conique articulé + pied à orteils griffus.
    Bug fixé (boucle 12) : le pied (`foot`) était placé à des Z ABSOLUS (proches du
    sol) au lieu d'être relatif à sa propre position -> pattes invisibles/écrasées
    dès que le pied n'est pas près de z=0 (pose de vol repliée, jambe courte, etc.).
    Désormais tout est RELATIF à `foot.loc` et orienté le long de l'axe du pied
    (direction du dernier segment de la patte, généraliste — aucune valeur dragon en
    dur ; `foot.dir` permet de forcer l'axe si besoin)."""
    out = []
    sides = [1, -1] if part.get('side', 'both') == 'both' else [1]
    for s in sides:
        tag = 'L' if s > 0 else 'R'
        pts = [(s * p[0], p[1], p[2]) for p in part['pts']]
        radii = part.get('radii') or laws.power_taper(len(pts), part.get('r0', 0.3), 1.0, 0.1)
        # anatomie (muscles fusiformes/articulations/plis, cf. `_anatomical_tube`) :
        # rétro-compat totale, un tube rond à rayon interpolé linéairement (comportement
        # historique) si `muscles`/`joints`/`folds` sont absents de la spec.
        if part.get('muscles') or part.get('joints') or part.get('folds'):
            leg = _anatomical_tube(f"{part.get('id', 'leg')}_{tag}", pts, radii,
                                   muscles=part.get('muscles'), joints=part.get('joints'),
                                   folds=part.get('folds'), mirror_sign=s)
        else:
            leg = ops.tube(f"{part.get('id', 'leg')}_{tag}", pts, radii)
        materials.assign(leg, _mat(mats, part.get('mat', 'scales')))
        out.append(leg)
        if part.get('foot'):
            f = part['foot']
            ax, ay, az = s * f['loc'][0], f['loc'][1], f['loc'][2]
            # axe du pied (plan horizontal local) : `foot.dir` explicite (repère non
            # mirroré, x=côté) sinon dérivé du dernier segment de la patte (déjà
            # mirroré dans `pts`) -> le pied prolonge naturellement la cheville.
            if 'dir' in f:
                fdx, fdy = s * f['dir'][0], f['dir'][1]
            else:
                fdx, fdy = pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1]
            fn = math.hypot(fdx, fdy) or 1.0
            fdx, fdy = fdx / fn, fdy / fn
            perp_x, perp_y = -fdy, fdx  # normale horizontale locale -> éventail des orteils
            pad_size = tuple(f.get('pad_size', (0.15, 0.19, 0.10)))
            pad = ops.blob(f'footpad_{tag}', (ax, ay, az + pad_size[2] * 0.2), pad_size)
            materials.assign(pad, _mat(mats, part.get('mat', 'scales')))
            out.append(pad)
            length = f.get('length', 0.4)
            r0 = f.get('toe_r0', 0.105)
            claw_len = f.get('claw_len', 0.14)
            for k, ang in enumerate(f.get('toe_angles', (-26, 0, 26))):
                ra = math.radians(ang)
                ddx = fdx * math.cos(ra) + perp_x * math.sin(ra)
                ddy = fdy * math.cos(ra) + perp_y * math.sin(ra)
                p0 = (ax, ay - fdy * length * 0.1, az + pad_size[2] * 0.35)
                p1 = (ax + ddx * length * 0.5, ay + ddy * length * 0.5, az - length * 0.12)
                p2 = (ax + ddx * length, ay + ddy * length, az - length * 0.30)
                toe = ops.tube(f'toe_{tag}{k}', [p0, p1, p2],
                               [r0, r0 * 0.72, r0 * 0.40])
                materials.assign(toe, _mat(mats, part.get('mat', 'scales')))
                out.append(toe)
                claw = ops.tube(f'claw_{tag}{k}',
                                [p2,
                                 (p2[0] + ddx * claw_len * 0.5, p2[1] + ddy * claw_len * 0.5, p2[2] - claw_len * 0.35),
                                 (p2[0] + ddx * claw_len, p2[1] + ddy * claw_len, p2[2] - claw_len * 0.7)],
                                [r0 * 0.33, r0 * 0.19, r0 * 0.04])
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


def _apply_fuse_groups(spec, groups):
    """Concept générique `fuse_groups` (doctrine v1 axe 1) : remplace, pour un
    sous-ensemble de parts, les objets par leur fusion SDF continue (bx.fuse.sdf_fuse)
    — torse+bras d'aile fondus en une seule masse organique au lieu d'objets qui se
    touchent en un point. `spec['fuse_groups']` = liste de
    `{id, parts:[...], objects_like:[...], exclude_like:[...], voxel, fillet, mat}` :
      - `parts` : parts dont les objets sont candidats à la fusion.
      - `objects_like` (optionnel) : motifs de nom supplémentaires — tire en plus
        n'importe quel objet d'AUTRES groupes (utile pour ajouter une pièce sans
        lister toute sa part, ex. juste les racines de pattes plus tard).
      - `exclude_like` : motifs de nom à exclure des candidats (membrane/doigts/
        lattes/griffes/piques qui doivent rester des objets séparés posés dessus).
    Le mesh fusionné remplace en place le groupe de la PREMIÈRE part listée ; les
    autres parts listées gardent seulement ce qui n'a pas été consommé (ex. `wing`
    garde membrane/doigts/lattes après que ses `arm_` aient fusionné avec le corps).
    `armor`/`displace` qui ciblent ces ids par nom n'ont rien à changer : ils
    retrouvent la surface fusionnée sous le même id de groupe."""
    fgs = spec.get('fuse_groups', [])
    if not fgs:
        return
    from . import fuse as _fuse
    for fg in fgs:
        parts = fg.get('parts', [])
        include = fg.get('objects_like', [])
        exclude = fg.get('exclude_like', [])
        # bake CURVE->MESH en place AVANT de collecter (Mesh to SDF Grid exige un
        # mesh réel) — même pattern que _apply_armor : on met `groups` à jour pour
        # que le reste du pipeline retrouve les objets bakés sous le même id.
        for pid in parts:
            groups[pid] = [core.realize_to_mesh(o) if o.type == 'CURVE' else o
                          for o in groups.get(pid, [])]
        if include:
            for gid, glist in groups.items():
                groups[gid] = [core.realize_to_mesh(o)
                               if o.type == 'CURVE' and any(x in o.name for x in include) else o
                               for o in glist]
        seen, objs = set(), []
        for pid in parts:
            for o in groups.get(pid, []):
                if o.type != 'MESH' or o.name in seen:
                    continue
                if any(x in o.name for x in exclude):
                    continue
                seen.add(o.name)
                objs.append(o)
        if include:
            for glist in groups.values():
                for o in glist:
                    if o.name in seen or o.type != 'MESH':
                        continue
                    if any(x in o.name for x in include) and not any(x in o.name for x in exclude):
                        seen.add(o.name)
                        objs.append(o)
        if len(objs) < 2:
            continue
        # id() (pas .name) : sdf_fuse() SUPPRIME les objets consommés sauf le premier
        # (réutilisé/renommé) -> lire un attribut RNA dessus après coup lève
        # ReferenceError ; id() ne touche pas au struct Blender, safe post-suppression.
        consumed_ids = {id(o) for o in objs}
        primary = parts[0] if parts else fg.get('id', 'fused')
        # nommé d'après la part PRIMAIRE (pas fg['id']) : feedback.classify_object
        # (inspect/validate/sheet4) reconnaît une pièce par préfixe de nom = id de
        # part -> le mesh fusionné doit porter ce nom pour rester classé "body" et
        # non tomber dans "other".
        fused = _fuse.sdf_fuse(objs, voxel=fg.get('voxel', 0.05),
                               fillet=fg.get('fillet', 0.25),
                               name=primary)
        if fg.get('mat'):
            # BUG corrigé (boucle 16) : sdf_fuse() (Mesh to SDF Grid -> Grid to Mesh)
            # ne préserve pas les assignations de matériau de la géométrie source, mais
            # LAISSE un slot 0 vide (None) sur le mesh évalué -> `materials.assign`
            # (qui APPEND) empilait le vrai matériau en slot 1 pendant que 100% des
            # faces pointaient encore sur le slot 0 (None) = rendu au matériau PAR
            # DÉFAUT de Blender (gris plastique plat, SANS bump/patine) sur toute la
            # peau NUE du corps fusionné entre les plaques d'armure instanciées —
            # exactement le défaut « surface lisse sous les écailles » signalé en
            # feedback. `clear()` avant `append()` : le nouveau matériau retombe en
            # slot 0, déjà référencé par toutes les faces.
            fused.data.materials.clear()
            materials.assign(fused, spec.get('_mats', {}).get(fg['mat']))
        # purge partout (pas seulement `parts`) : `objects_like` peut avoir tiré des
        # objets d'un groupe non listé (ex. futures racines de patte).
        for gid in list(groups.keys()):
            groups[gid] = [o for o in groups[gid] if id(o) not in consumed_ids]
        groups[primary] = [fused] + groups.get(primary, [])


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
                mask=e.get('mask'), mask_radial=e.get('mask_radial'),
                mask_near=e.get('mask_near'), mask_near_avoid=e.get('mask_near_avoid'),
                scale_grad=e.get('scale_grad'),
                distance_min=e.get('distance_min', 0.0),
                index_grad=e.get('index_grad'),
                index_noise=tuple(e.get('index_noise', (3.0, 1.4))),
                rot_jitter=e.get('rot_jitter', 0.0),
                scale_noise=tuple(e['scale_noise']) if e.get('scale_noise') else None,
                realize=realize,
                store_seed=e.get('store_seed', not realize),
                name=f'armor_{idx}_{ob.name}')


def _apply_bake_uv(spec, groups):
    """UV auto (bx.bake) sur le LOW-poly des groupes `spec['bake']` — DOIT tourner à
    CHAQUE construction de scène (forge/bake/validate/...), pas seulement la commande
    `bake` : le mesh fusionné est déterministe pour une spec donnée (même topologie à
    chaque `build()`), donc rejouer exactement le même smart_project/pack_islands
    reproduit la MÊME UV sans rien persister sur disque — condition nécessaire pour que
    les maps bakées (chemins branchés dans `materials.py`) restent alignées au rendu.
    Rétro-compat totale : pas de `spec['bake']` -> aucun appel, comportement inchangé."""
    entries = spec.get('bake', [])
    if not entries:
        return
    from . import bake as _bake
    for g in entries:
        exclude = g.get('exclude_like', [])
        seen, objs = set(), []
        for pid in g.get('parts', []):
            for o in groups.get(pid, []):
                if o.type != 'MESH' or o.name in seen or any(x in o.name for x in exclude):
                    continue
                seen.add(o.name)
                objs.append(o)
        for ob in objs:
            _bake.uv_unwrap(ob, margin_px=g.get('margin_px', 4),
                            resolution=g.get('maps', {}).get('normal', 2048))


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
    _apply_fuse_groups(spec, groups)
    _apply_displace(spec, groups)
    _apply_armor(spec, groups)
    _apply_bake_uv(spec, groups)
    sc = spec.get('scene', {})
    core.world(**sc.get('world', {}))
    core.sun(**sc.get('sun', {}))
    for al in sc.get('area_lights', []):
        core.area_light(**al)
    core.camera(**sc.get('camera', {'loc': (9, -11, 3.5), 'target': (0, 0, 2), 'lens': 40}))
    return count
