"""bx.organic — générateurs de parties anatomiques pilotés par spec JSON + lois GVL.
Chaque builder consomme un dict compact et retourne des objets Blender. Généraliste :
un dragon, un arbre ou un poisson ne diffèrent que par leur spec."""
import itertools
import math

import bmesh
import bpy
from mathutils import Euler, Quaternion, Vector
from mathutils.bvhtree import BVHTree

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


def _dorsal_spikes(pts, radii, sp, mats, prefix='dorsal'):
    """Crête dorsale : piques instanciés le long d'une polyligne pts/radii (même
    format qu'`ops.tube` -- radii scalaire OU [rx,ry]). Factorisé (boucle 23
    round 2, feedback « le mécanisme spikes existe, adapte-le plutôt que
    recréer ») : `spine` ET `skin_body` appellent la MÊME fonction, aucune copie.
    `rows` (défaut 2, rétro-compat = les 2 rangées +/- historiques) : nombre de
    rangées, alternées côté +/- par paire (row 0=+ 1=- 2=+ 3=-...), chaque paire
    suivante légèrement réduite (`row_falloff`) -- permet >2 rangées si besoin
    sans dupliquer le mécanisme.
    `shape` (défaut 'blade' = profil long/fin historique ; 'fin' = boucle 23
    round 2, feedback « aiguilles pas ailerons » -- triangle COURT/LARGE au bord
    ARRONDI type petit aileron de requin) : bascule juste les défauts
    base_frac/mid_frac/tip_frac_h/flat/h0 vers un profil trapu et épais, MÊME
    géométrie 3 points + `ops.tube(flat=...)` que le profil historique, aucune
    primitive neuve. `tip_frac_h` (fraction de `h`, prioritaire sur `tip_r` si
    présent) donne une pointe ÉMOUSSÉE proportionnelle à la taille du pique
    (au lieu d'un `tip_r` absolu qui reste fin même sur un grand aileron).
    `tail_taper` (0..1, défaut 0 = rétro-compat, boucle 23 round 3) : décroissance
    linéaire explicite de `h` le long de la crête (i0->i1, donc vers la queue),
    en plus de l'enveloppe `env` existante -- utile car le pic de `env` tombe
    souvent proche de la fin de la plage utilisée (`end_frac`), donnant un peigne
    de taille quasi uniforme sans ce paramètre."""
    n = sp.get('n', 20)
    path = laws.lerp_path([tuple(p) for p in pts], n)
    rr = _norm_radii(radii)
    rads = laws.lerp_path([(rx, ry, 0.0) for rx, ry in rr], n)
    i0 = sp.get('skip', 2)
    # end_frac (défaut 1.0 = rétro-compat, court jusqu'au bout) : arrête la crête
    # avant la fin de la polyligne -- utile sur une queue qui s'enroule vers
    # l'avant (le bout croise le corps/les pattes, la crête n'a pas à suivre).
    i1 = max(i0 + 1, int(sp.get('end_frac', 1.0) * (n - 1)))
    shape = sp.get('shape', 'blade')
    is_fin = shape == 'fin'
    # base/pointe et anneaux de croissance (feedback boucle 18 pt5 : piques
    # dorsales qui lisent comme de la fourrure/des plumes) : `base_frac`/`tip_r`
    # (rétro-compat, défauts = valeurs historiques 0.22/0.008) élargissent la base
    # d'implantation ; `rings` (absent par défaut = comportement inchangé) réutilise
    # `laws.growth_rings` (déjà utilisée par les cornes) sur le profil à 3 points
    # pour casser la lame lisse et translucide par un renflement médian discret.
    base_frac = sp.get('base_frac', 0.45 if is_fin else 0.22)
    mid_frac = sp.get('mid_frac', 0.34 if is_fin else 0.12)
    tip_r = sp.get('tip_r', 0.008)
    tip_frac_h = sp.get('tip_frac_h', 0.30 if is_fin else None)
    flat_default = 0.22 if is_fin else None
    flat = sp.get('flat', flat_default)
    h0 = sp.get('h0', 0.32 if is_fin else 0.65)
    rows = max(1, int(sp.get('rows', 2)))
    rp = sp.get('rings')
    # tail_taper (0..1, défaut 0 = rétro-compat) : boucle 23 round 3, feedback
    # « décroissance de taille plus marquée vers la queue » -- `env` (sin(pi*t))
    # ne redescend presque pas dans la portion utile de la crête (le pic tombe
    # souvent proche de la fin de plage utilisée, cf. `end_frac`), donc les piques
    # lisent comme un peigne uniforme. `tail_taper` ajoute une décroissance
    # LINÉAIRE explicite le long de l'index de la crête (i0->i1, donc vers la
    # queue) par-dessus l'enveloppe existante -- 0 = comportement inchangé.
    tail_taper = max(0.0, min(1.0, sp.get('tail_taper', 0.0)))
    span = max(1, i1 - i0 - 1)
    out = []
    for i in range(i0, i1):
        p, (rx, ry, _rz) = path[i], rads[i]
        r = (rx + ry) * 0.5
        nxt = path[i + 1]
        dy, dz = nxt[1] - p[1], nxt[2] - p[2]
        d = math.hypot(dy, dz) or 1e-3
        uy, uz = dy / d, dz / d          # tangente avant
        vy, vz = -uz, uy                 # normale « dessus », perpendiculaire à la tangente
        if vz < 0:                       # toujours du côté "dessus" (z+), pas "dessous"
            vy, vz = -vy, -vz
        # up_bias (round 2 boucle 23, bug mesuré : sur `skin_body`, la colonne monte/
        # descend BEAUCOUP plus qu'une `spine` classique -- au poitrail bombé, la
        # tangente devient presque verticale -> la perpendiculaire pure devient
        # presque HORIZONTALE, les piques se couchent à plat au lieu de se dresser
        # (mesuré : bbox du groupe ne dépassait quasi pas la coque). On mélange donc
        # la perpendiculaire "suit la courbure" avec un vrai "vers le haut" (z+) fixe
        # -- défaut 0.0 = RÉTRO-COMPAT totale (comportement historique `spine`
        # inchangé) ; `skin_body`/krokmou passe une valeur >0 explicitement.
        up_bias = sp.get('up_bias', 0.0)
        vy = vy * (1.0 - up_bias)
        vz = vz * (1.0 - up_bias) + up_bias
        vn = math.hypot(vy, vz) or 1e-3
        vy, vz = vy / vn, vz / vn
        t = i / (n - 1)
        env = math.sin(math.pi * t) ** 0.6 * min(1.0, r * 2.0 + 0.3)
        if t > 0.72:  # pas de fondu vers 0 côté tête : fusion avec la couronne de cornes
            fade = (t - 0.72) / 0.28
            env = max(env, 0.62 * (1 - fade) + 0.42 * fade)
        for row in range(rows):
            sx = 1.0 if row % 2 == 0 else -1.0
            pair = row // 2
            row_falloff = 1.0 - 0.22 * pair
            jit = 1.0 + 0.30 * math.sin(i * 7.3 + row * 2.6)
            taper = 1.0 - tail_taper * ((i - i0) / span)
            h = max(0.05, h0 * env * jit * row_falloff * taper * (1.0 if row < 2 else 0.85))
            bx = p[0] + sx * (0.07 + 0.05 * pair) * rx
            by, bz = p[1], p[2] + ry * 0.92
            s_pts = [(bx, by, bz),
                     (bx, by + vy * h * 0.55 - uy * h * 0.16, bz + vz * h * 0.55 - uz * h * 0.16),
                     (bx, by + vy * h * 0.92 - uy * h * 0.50, bz + vz * h * 0.92 - uz * h * 0.50)]
            tip_rad = h * tip_frac_h if tip_frac_h is not None else tip_r
            s_radii = [h * base_frac, h * mid_frac, tip_rad]
            if rp and rp.get('depth', 0.0):
                mod = laws.growth_rings(3, depth=rp.get('depth', 0.12),
                                        freq=rp.get('freq', 3.0), sharp=rp.get('sharp', 2.0))
                s_radii = [rr_ * m for rr_, m in zip(s_radii, mod)]
            # flat (P1 boucle 22, feedback « épines = cônes ronds -> profils plats
            # type écaille ») : défaut None = rétro-compat (section ronde
            # inchangée) ; réutilise `ops.tube(flat=...)` (même mécanisme que les
            # cornes-lames plus bas) pour une pointe en plaque fine.
            s = ops.tube(f'{prefix}_{i}_{row}', s_pts, s_radii, flat=flat)
            materials.assign(s, _mat(mats, sp.get('mat', 'bone')))
            out.append(s)
    return out


@builder('spine')
def spine(part, mats):
    """Corps principal : tube conique + crête dorsale double rangée, pointes courbées vers l'arrière."""
    pts = [tuple(p) for p in part['pts']]
    radii = part['radii']
    # smooth (boucle 22, thème « souder pas poser » — feedback P0 « queue à coudes
    # vifs entre points de contrôle ») : défaut 0 = rétro-compat totale (polyligne de
    # contrôle brute, comportement inchangé). >1 = densifie `pts`/`radii` par
    # interpolation Catmull-Rom (`growth.spine_smooth`, PASSE par les points d'origine,
    # contrairement à `laws.lerp_path` qui reste linéaire) AVANT de construire le tube
    # -> une NURBS avec beaucoup plus de points de contrôle rapprochés colle à une
    # courbe C1 fluide au lieu des quelques coudes anguleux d'origine. Générique :
    # marche pour n'importe quelle spine (corps, queue, cou...), aucune valeur figée.
    sm = part.get('smooth', 0)
    if sm and sm > 1:
        pts = apply_law('growth.spine_smooth', pts=pts, samples=sm)
        radii = [r[0] for r in apply_law('growth.spine_smooth',
                                         pts=[(r,) for r in radii], samples=sm)]
    body = ops.tube(part.get('id', 'spine'), pts, radii)
    materials.assign(body, _mat(mats, part.get('mat', 'scales')))
    out = [body]
    sp = part.get('spikes')
    if sp:
        out.extend(_dorsal_spikes(pts, radii, sp, mats, prefix='dorsal'))
    return out


def _norm_radii(radii):
    """Uniformise une liste de rayons (`spine`/`skin_body`) en paires (rx, ry) —
    un scalaire donne une section ronde (rx=ry), une paire [rx, ry] une section
    aplatie. Partagé par `skin_body` (corps ET membres)."""
    return [tuple(r) if isinstance(r, (list, tuple)) else (r, r) for r in radii]


def _densify_chain(pts, radii, samples, min_len_ratio=1.15):
    """Densifie une polyligne de contrôle + ses rayons par Catmull-Rom
    (`growth.spine_smooth`) AVANT construction du squelette SKIN — passe par les
    points d'origine avec tangente continue, contrairement à une simple
    ré-interpolation linéaire (`laws.lerp_path`) : aucune cassure d'angle, même
    sur un tracé à peu de points de contrôle (queue, membres). `samples<=1` =
    rétro-compat totale (pas de densification).
    DÉCIMATION ADAPTATIVE (boucle 23, bug mesuré) : le modifier SKIN a besoin
    d'arêtes plus LONGUES que le rayon local -- sinon les anneaux successifs se
    chevauchent, des faces se retournent, et ça se lit comme des « ailerons » en
    éventail après Subdivision Surface (mesuré sur un poitrail à grand rayon
    densifié uniformément). On génère la courbe C1 complète puis on retire les
    points intermédiaires trop rapprochés (`min_len_ratio` * rayon local) --
    garde la densité fine là où le rayon est PETIT (cou, queue : exactement ce
    qui doit rester lisse) et retombe naturellement vers l'espacement des points
    de contrôle d'origine là où le rayon est GRAND (torse -- pas de coude à
    lisser de toute façon sur un tracé à peu de points)."""
    radii = _norm_radii(radii)
    if not (samples and samples > 1 and len(pts) >= 3):
        return [tuple(p) for p in pts], radii
    pts_d = apply_law('growth.spine_smooth', pts=[tuple(p) for p in pts], samples=samples)
    rx = [v[0] for v in apply_law('growth.spine_smooth',
                                  pts=[(r[0],) for r in radii], samples=samples)]
    ry = [v[0] for v in apply_law('growth.spine_smooth',
                                  pts=[(r[1],) for r in radii], samples=samples)]
    kept_pts, kept_rx, kept_ry = [pts_d[0]], [rx[0]], [ry[0]]
    last = Vector(pts_d[0])
    for i in range(1, len(pts_d) - 1):
        p = Vector(pts_d[i])
        r_local = max(rx[i], ry[i])
        if (p - last).length >= r_local * min_len_ratio:
            kept_pts.append(pts_d[i])
            kept_rx.append(rx[i])
            kept_ry.append(ry[i])
            last = p
    kept_pts.append(pts_d[-1])
    kept_rx.append(rx[-1])
    kept_ry.append(ry[-1])
    return [tuple(p) for p in kept_pts], list(zip(kept_rx, kept_ry))


@builder('skin_body')
def skin_body(part, mats):
    """Squelette SKIN unique (boucle 23, thème « UNE SEULE PEAU », remplace le
    diagnostic « assemblage de primitives posées qui ne converge pas ») : UN SEUL
    objet continu corps + cou + queue + pattes, construit depuis un VRAI squelette
    (mesh vertices+edges, pas une NURBS) porté par un modifier SKIN — rayon PAR
    VERTEX, rx/ry séparés (`bm.verts.layers.skin`, `MeshSkinVertexLayer.radius` =
    (x, y) -> sections aplaties possibles, pas seulement rondes) — puis lissé par
    Subdivision Surface. Générique : aucune valeur créature en dur, tout vient de
    la spec ; réutilisable pour n'importe quelle créature à 4 pattes/queue/cou.

    `pts`/`radii` : colonne vertébrale COMPLÈTE, tête -> bout de queue en un seul
    tracé continu (même format que `spine` : radii scalaire OU [rx, ry] par
    point). `smooth` (défaut 0 = rétro-compat, pas de densification) : réutilise
    `laws.catmull_rom` (`_densify_chain`) pour densifier pts ET radii avant de
    bâtir le squelette -> aucune cassure d'angle, y compris sur les tracés à peu
    de points de contrôle (queue).
    `root_idx` (index dans `pts` D'ORIGINE, avant densification ; défaut = point
    de plus grand rayon moyen = torse) : le vertex SKIN correspondant est marqué
    `use_root` -- ancre la géométrie du renflement le plus massif (évite un
    étranglement au point le plus épais).
    `limbs` : liste de {id, side('both'|'L'|'R'), pts, radii, smooth}. `pts`/
    `radii` d'un membre = SA PROPRE polyligne (épaule/hanche -> cheville), x>=0
    (mirroré si side='both'). Le premier point est relié par une arête au vertex
    de spine le PLUS PROCHE (attache automatique par distance, pas de recalage
    d'index manuel si la spine bouge).
    `subsurf` (défaut 2) = niveaux de Subdivision Surface finale."""
    pid = part.get('id', 'skin_body')
    pts, radii = _densify_chain(part['pts'], part['radii'], part.get('smooth', 0))

    bm = bmesh.new()
    skin_layer = bm.verts.layers.skin.verify()
    spine_verts = []
    for p, (rx, ry) in zip(pts, radii):
        v = bm.verts.new(p)
        v[skin_layer].radius = (rx, ry)
        spine_verts.append(v)
    for i in range(len(spine_verts) - 1):
        bm.edges.new((spine_verts[i], spine_verts[i + 1]))

    orig_pts = [tuple(p) for p in part['pts']]
    orig_radii = _norm_radii(part['radii'])
    if 'root_idx' in part:
        root_pt = orig_pts[part['root_idx']]
    else:
        root_i = max(range(len(orig_radii)), key=lambda i: sum(orig_radii[i]))
        root_pt = orig_pts[root_i]
    root_v = min(spine_verts, key=lambda v: (v.co - Vector(root_pt)).length_squared)
    root_v[skin_layer].use_root = True

    for limb in part.get('limbs', []):
        side = limb.get('side', 'both')
        sides = (1, -1) if side == 'both' else ((1,) if side == 'L' else (-1,))
        lpts, lradii = _densify_chain(limb['pts'], limb['radii'], limb.get('smooth', 0))
        # attach_used (par membre, PAS partagé entre membres différents) : un membre
        # mirroré (side='both') a 2 branches dont le 1er point n'a que le signe X qui
        # change -> sans exclusion, les 2 se raccrochent au MÊME vertex de spine (le
        # plus proche est identique par symétrie x=0) -> valence 4 (spine avant/
        # arrière + 2 pattes) que le modifier SKIN blende mal (artefact "ailerons"
        # triangulaires en éventail, mesuré boucle 23). En excluant le vertex déjà
        # pris pour le 1er côté, le 2e s'accroche au vertex de spine VOISIN (la
        # colonne est densifiée, `smooth`, donc un voisin proche existe toujours) ->
        # valence <=3 par jonction, blend propre.
        attach_used = set()
        for s in sides:
            mpts = [(s * p[0], p[1], p[2]) for p in lpts]
            attach = Vector(mpts[0])
            candidates = [v for v in spine_verts if v not in attach_used] or spine_verts
            prev = min(candidates, key=lambda v: (v.co - attach).length_squared)
            attach_used.add(prev)
            for p, (rx, ry) in zip(mpts, lradii):
                v = bm.verts.new(p)
                v[skin_layer].radius = (rx, ry)
                bm.edges.new((prev, v))
                prev = v

    mesh = bpy.data.meshes.new(pid)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(pid, mesh)
    core.link(ob)
    ob.modifiers.new('skin', 'SKIN')
    core.subsurf(ob, part.get('subsurf', 2))
    materials.assign(ob, _mat(mats, part.get('mat', 'scales')))
    out = [core.shade_smooth(ob)]
    # spikes (boucle 23 round 2, feedback P1 « épines dorsales ») : réutilise
    # `_dorsal_spikes` (même mécanisme que `spine`, cf. sa docstring pour
    # `rows`/`shape`) sur la colonne D'ORIGINE (avant `_densify_chain` -- même
    # convention que `spine`, la polyligne de contrôle brute suffit à `lerp_path`
    # pour ré-échantillonner la crête, pas besoin de la version densifiée pour SKIN).
    sp = part.get('spikes')
    if sp:
        out.extend(_dorsal_spikes(part['pts'], part['radii'], sp, mats, prefix=f'{pid}_spike'))
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


def _bvh_from_mesh_obj(ob):
    """BVHTree MONDE depuis un objet MESH évalué (modifiers appliqués : subsurf du
    `ring_loft`, bevel d'un `boolean_diff` précédent...) — même schéma que
    `bx.validate._evaluated_bm`/`_tree`, réutilisé ici pour échantillonner la surface
    RÉELLE d'un mesh plutôt qu'une estimation analytique du profil."""
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), depsgraph=deps)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bm.transform(ob.matrix_world)
    if bm.faces:
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tree = BVHTree.FromBMesh(bm, epsilon=1e-6)
    return tree, bm


def _mouth_cutter(name, secs, y_span, Wf, Rdir, flex, ys_flex, z_frac, depth, edge_frac,
                  side, tree, n=14, ray_dist=2.0):
    """Cutter FIN (booléen) suivant la même paramétrisation que `_lip_bourrelet` (même
    profil `[y,w,hh]`, même convention `z_frac` = bord bas du crâne / bord haut de la
    mâchoire, cf. docstring `_lip_bourrelet`) -> path collé exactement à la ligne où
    crâne et mâchoire se touchent. Boucle 22, feedback P0 « bouche = fil posé -> fente
    CARVÉE » : au lieu d'ajouter un bourrelet PAR-DESSUS la couture, ceci CREUSE une
    gorge fine directement dans la surface le long du même tracé -> indentation
    négative réelle, pas un tube qui se contente de flotter sur le dessus.
    Round 2 (même boucle, « ne mord la surface qu'à la commissure ») : le point
    latéral n'est PLUS une estimation analytique (`w*width_frac`) qui suppose un
    profil elliptique -- l'exposant `exp` du profil superellipse déforme le bord réel
    de façon non-linéaire, donc cette estimation ne colle au mesh que par endroits
    (là où elle tombe juste par hasard). Remplacé par un RAYCAST HORIZONTAL (BVHTree,
    même mécanisme que `bx.validate`) : depuis l'axe central de la tête (x local=0,
    intérieur garanti du mesh) vers l'extérieur (`side`), jusqu'à la surface RÉELLE
    de `tree` -> le point est TOUJOURS exactement sur la coque à cette hauteur/cette
    section, plus de dépendance à la forme du profil. `edge_frac` (ex-`width_frac`,
    même clé spec, sémantique adaptée) place le point le long de ce même rayon,
    entre l'axe (0.0) et le bord réel touché (1.0) ; défaut proche de 1 = cutter
    centré presque pile sur la coque -> mord partout, pas seulement au hasard."""
    ys = [s[0] for s in secs]
    ws = [s[1] for s in secs]
    hs = [s[2] for s in secs]
    y0, y1 = y_span
    pts, radii = [], []
    dir_local = Vector((side, 0.0, 0.0))
    dir_world = (Rdir @ dir_local).normalized()
    for i in range(n):
        t = i / max(1, n - 1)
        y = y0 + t * (y1 - y0)
        w = _interp_scalar(ys, ws, y)
        hh = _interp_scalar(ys, hs, y)
        fz = _interp_scalar(ys_flex, flex, y) if flex else 0.0
        z = fz + hh * z_frac
        origin = Vector(Wf((0.0, y, z)))
        hit = tree.ray_cast(origin, dir_world, ray_dist) if tree else (None, None, None, None)
        if hit[0] is not None:
            edge = origin.lerp(hit[0], edge_frac)
        else:
            # repli générique (rayon sans impact -- section hors mesh, début/fin de
            # museau) : ancienne estimation analytique plutôt qu'un point orphelin.
            edge = Vector(Wf((side * w * edge_frac, y, z)))
        pts.append(tuple(edge))
        radii.append(depth)
    return core.realize_to_mesh(ops.tube(name, pts, radii, resolution_u=8, bevel_resolution=5))


def _tooth_offsets(n, tilt_amt, curve_amt, twist_amt, power=1.7):
    """Décalages latéraux d'un profil de dent COURBE (boucle 19 chantier C, feedback
    « dents = cônes parfaits sans irrégularité ») : `laws.curl_offset` (déjà utilisée
    pour la courbure de pointe des cornes) réutilisée pour un axe avant/arrière
    (`lean`, tilt de base historique + `curve_amt` proportionnel à la longueur pour
    un vrai crochet visible) et un axe latéral (`twist`) — tous deux croissants de
    façon NON-LINÉAIRE base->pointe (`power`>1 concentre la courbure vers la pointe,
    pas un cône droit à 2 segments quasi alignés)."""
    lean_off = laws.curl_offset(n, amount=tilt_amt + curve_amt, power=power)
    twist_off = laws.curl_offset(n, amount=twist_amt, power=power)
    return lean_off, twist_off


@builder('head')
def head(part, mats):
    """Tête loftée par sections superellipse (GVL) : crâne→museau continu, mâchoire
    inférieure articulée ouverte de `gape`°, dents courbes, yeux sous arcades,
    narines, couronne de cornes en spirale log."""
    from . import detail as _detail
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
    # profile_smooth (boucle 22, thème « souder pas poser » — feedback P0 museau
    # « section trop abrupte ») : défaut 0 = rétro-compat totale (sections de contrôle
    # brutes, comportement inchangé). >1 = densifie `upper`/`lower` (chacun un triplet
    # y/demi-largeur/demi-hauteur -> Catmull-Rom marche tel quel, dimension 3
    # quelconque) AVANT le loft -> bien plus de sections intermédiaires SUIVANT une
    # courbe C1 lisse au lieu de la simple interpolation linéaire entre quelques
    # points épars -> transition crâne->museau progressive (profil en U doux) au lieu
    # d'un aplat/élargissement qui casse net entre 2 points de contrôle voisins.
    psm = part.get('profile_smooth', 0)
    if psm and psm > 1:
        upper = apply_law('growth.spine_smooth', pts=[tuple(p) for p in upper], samples=psm)
        lower = apply_law('growth.spine_smooth', pts=[tuple(p) for p in lower], samples=psm)
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
    # socket_bevel (boucle 22, feedback P0 « orbite = trou découpé net -> dépression
    # OVOÏDE à bords ADOUCIS ») : défaut 0.0 = rétro-compat (arête de coupe vive
    # inchangée). >0 = adoucit l'arête vive du booléen (`ops.boolean_diff bevel_width`,
    # Bevel limité par angle, n'affecte pas les arêtes déjà douces de la calotte) ->
    # la cavité se lit comme un creux naturel qui referme progressivement vers le
    # rebord plutôt qu'un trou découpé net.
    socket_bevel = eyep.get('socket_bevel', 0.0)
    for s, tag in ((1, 'l'), (-1, 'r')):
        cutter = ops.blob(f'eye_cutter_{tag}', W((s * ex * 0.92, ey, ez)),
                          (esr * 1.30, esr * 0.82, esr * 0.98))
        sk = ops.boolean_diff(sk, cutter, name='skull', bevel_width=socket_bevel)
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

    # mouth_carve (boucle 22, feedback P0 « bouche = fil posé -> fente CARVÉE suivant
    # le profil en U du museau ») : défaut None = rétro-compat totale (pas de carve,
    # comportement inchangé). Creuse une gorge fine dans le crâne (bord bas, cf.
    # `_mouth_cutter`) le long de la ligne de bouche — moitié mâchoire faite plus bas,
    # une fois `jw` construite (même mécanisme, bord haut).
    mc = part.get('mouth_carve')
    if mc:
        mc_depth = mc.get('depth', 0.014)
        mc_width = mc.get('width_frac', 0.85)
        mc_n = mc.get('n', 14)
        mc_pad0 = mc.get('pad_start', 0.05)
        mc_pad1 = mc.get('pad_end', 0.03)
        mc_zu = mc.get('z_frac_upper', -0.18)
        mc_y0u = max(ys_u[0], part.get('tooth_span_upper', (0.42, 1.07))[0] - mc_pad0)
        mc_y1u = min(ys_u[-1], part.get('tooth_span_upper', (0.42, 1.07))[1] + mc_pad1)
        # BVH de la coque RÉELLE du crâne (état courant, après orbites/naseaux, AVANT
        # la carve) : les 2 côtés (l/r) mordent la même coque d'origine, symétrique et
        # sans influence l'un sur l'autre -- un seul arbre pour les deux évite de
        # ré-évaluer le depsgraph 2x.
        sk_tree, sk_bm = _bvh_from_mesh_obj(sk)
        for s, tag in ((1, 'l'), (-1, 'r')):
            cut_u = _mouth_cutter(f'mouth_cut_u_{tag}', upper, (mc_y0u, mc_y1u), W, Rp,
                                  upper_flex, ys_u, mc_zu, mc_depth, mc_width, s, sk_tree, n=mc_n)
            sk = ops.boolean_diff(sk, cut_u, name='skull', bevel_width=mc.get('bevel', 0.0))
            materials.assign(sk, skin)
        sk_bm.free()
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
    if mc:
        mc_zl = mc.get('z_frac_lower', 0.15)
        mc_y0l = max(ys_l[0], part.get('tooth_span_lower', (0.35, 0.99))[0] - mc_pad0)
        mc_y1l = min(ys_l[-1], part.get('tooth_span_lower', (0.35, 0.99))[1] + mc_pad1)
        jw_tree, jw_bm = _bvh_from_mesh_obj(jw)
        Rjaw = Rp @ Rj
        for s, tag in ((1, 'l'), (-1, 'r')):
            cut_l = _mouth_cutter(f'mouth_cut_l_{tag}', lower, (mc_y0l, mc_y1l), WJ, Rjaw,
                                  lower_flex, ys_l, mc_zl, mc_depth, mc_width, s, jw_tree, n=mc_n)
            jw = ops.boolean_diff(jw, cut_l, name='jaw', bevel_width=mc.get('bevel', 0.0))
            materials.assign(jw, skin)
        jw_bm.free()
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
    # gencive : bourrelet CONTINU (pas des blobs isolés par dent, feedback boucle 19
    # chantier C) -- `gum_mat` (matériau chair humide dédié `materials.gum`, replié sur
    # la peau si absent de la spec) + `gum_ridge` (sous-dict optionnel, mêmes clés que
    # `lip_profile`) pilote le bourrelet posé après les deux rangées de dents.
    gum_mat = _mat(mats, part.get('gum_mat', 'gum')) or skin
    gr_spec = part.get('gum_ridge', {})
    su = part.get('tooth_span_upper', (0.42, 1.07))
    nu = part.get('teeth_upper', 6)
    fu_idx = set(part.get('fang_idx_upper', ()))
    fu_scale = part.get('fang_scale_upper', 1.0)
    fu_girth = part.get('fang_girth_upper', 1.3)
    lu_ref = ts * (0.07 + 0.012 * (nu - 1) * 0.5)
    # dent ébréchée/usée PAR SEED (feedback : « cônes parfaits sans irrégularité ») :
    # un index NON-croc choisi déterministe depuis `tooth_seed` -> pointe TRONQUÉE
    # (pas effilée) + légèrement raccourcie, lit comme une dent cassée/usée à l'usage.
    chip_u = 1 + int(abs(math.sin(tooth_seed * 1.7 + 0.4)) * max(0, nu - 2)) if nu > 2 else -1
    for i in range(nu):
        y = su[0] + i * (su[1] - su[0]) / max(1, nu - 1)
        w = interp_w(upper, y) * 0.78
        fz = _interp_scalar(ys_u, upper_flex, y)
        is_fang = i in fu_idx
        is_chip = (i == chip_u) and not is_fang
        for s, tag in ((1, 'l'), (-1, 'r')):
            # asymétrie gauche/droite (feedback : dents parfaitement symétriques en
            # miroir) : déphasage PAR CÔTÉ sur toutes les sinusoïdes de variance —
            # la dent droite n'est plus le clone-miroir exact de la gauche.
            ph = tooth_seed + (0.0 if tag == 'l' else 2.35)
            jit_l = 1 + 0.20 * math.sin(i * 9.1 + ph) + 0.06 * math.sin(i * 3.3 + 0.6 + ph)
            l = (0.07 + 0.012 * i) * ts * jit_l
            if is_fang:
                l *= fu_scale
            rscale = max(0.55, min(1.9, (l / max(lu_ref, 1e-4)) ** 0.5))
            if is_fang:
                rscale *= fu_girth
            jit_r = 1 + 0.08 * math.sin(i * 6.1 + 1.1 + ph)
            r_root, r_tip = 0.021 * ts * rscale * jit_r, 0.0032 * ts
            if is_chip:
                l *= 0.78
                r_tip = r_root * 0.42
            lean = 0.55 + 0.85 * math.sin(i * 3.7 + 1.1 + ph)
            twist = 0.05 * w * math.sin(i * 5.9 + 2.3 + ph)
            # courbure PROPORTIONNELLE à la longueur (crochet léger visible à
            # l'échelle du shot tête, pas un décalage constant noyé dans le bruit) :
            # `curve_amt` s'ajoute au tilt de base `lean*0.03` (historique).
            curve_amt = l * (0.22 + 0.16 * math.sin(i * 4.3 + 2.0 + ph))
            n_pts = 4
            lean_off, twist_off = _tooth_offsets(n_pts, lean * 0.03, curve_amt, twist)
            x = s * w
            pts_t = [W((x * (1.0 - 0.08 * (k / (n_pts - 1))) + s * twist_off[k],
                       y + lean_off[k], fz - 0.005 - l * (k / (n_pts - 1))))
                     for k in range(n_pts)]
            radii_t = laws.power_taper(n_pts, r_root, 1.35, r_tip)
            t = ops.tube(f'tooth_u{tag}{i}', pts_t, radii_t, resolution_u=8, bevel_resolution=6)
            materials.assign(t, tooth_m)
            out.append(t)
    sl = part.get('tooth_span_lower', (0.35, 0.99))
    nl = part.get('teeth_lower', 5)
    fl_idx = set(part.get('fang_idx_lower', ()))
    fl_scale = part.get('fang_scale_lower', 1.0)
    fl_girth = part.get('fang_girth_lower', 1.3)
    ll_ref = ts * (0.06 + 0.010 * (nl - 1) * 0.5)
    chip_l = 1 + int(abs(math.sin(tooth_seed * 2.3 + 1.9)) * max(0, nl - 2)) if nl > 2 else -1
    for i in range(nl):
        y = sl[0] + i * (sl[1] - sl[0]) / max(1, nl - 1)
        w = interp_w(lower, y) * 0.75
        fz = _interp_scalar(ys_l, lower_flex, y)
        is_fang = i in fl_idx
        is_chip = (i == chip_l) and not is_fang
        for s, tag in ((1, 'l'), (-1, 'r')):
            ph = tooth_seed + (0.0 if tag == 'l' else 2.35)
            jit_l = 1 + 0.20 * math.sin(i * 7.7 + 1.3 + ph) + 0.06 * math.sin(i * 3.1 + 0.2 + ph)
            l = (0.06 + 0.010 * i) * ts * jit_l
            if is_fang:
                l *= fl_scale
            rscale = max(0.55, min(1.9, (l / max(ll_ref, 1e-4)) ** 0.5))
            if is_fang:
                rscale *= fl_girth
            jit_r = 1 + 0.08 * math.sin(i * 5.3 + 0.4 + ph)
            r_root, r_tip = 0.019 * ts * rscale * jit_r, 0.0032 * ts
            if is_chip:
                l *= 0.78
                r_tip = r_root * 0.42
            lean = 0.55 + 0.85 * math.sin(i * 4.1 + 2.6 + ph)
            twist = 0.05 * w * math.sin(i * 6.7 + 0.4 + ph)
            curve_amt = l * (0.22 + 0.16 * math.sin(i * 4.9 + 0.5 + ph))
            n_pts = 4
            lean_off, twist_off = _tooth_offsets(n_pts, lean * 0.03, curve_amt, twist)
            x = s * w
            pts_t = [WJ((x * (1.0 - 0.08 * (k / (n_pts - 1))) + s * twist_off[k],
                        y + lean_off[k], fz + 0.005 + l * (k / (n_pts - 1))))
                     for k in range(n_pts)]
            radii_t = laws.power_taper(n_pts, r_root, 1.35, r_tip)
            t = ops.tube(f'tooth_l{tag}{i}', pts_t, radii_t, resolution_u=8, bevel_resolution=6)
            materials.assign(t, tooth_m)
            out.append(t)
    # bourrelet de gencive CONTINU en base des deux rangées (remplace les anciens
    # blobs isolés par dent) : même mécanisme que `lip_profile` (`_lip_bourrelet`,
    # suit la largeur/courbure du profil crâne/mâchoire), positionné PRÈS de la
    # ligne d'attache des dents (`z_frac` proche de 0, pas le bord externe de lèvre)
    # -> lit comme un bourrelet continu qui ancre chaque dent plutôt qu'un pointillé
    # d'ellipsoïdes séparés.
    gru = (max(ys_u[0], su[0] - 0.02), min(ys_u[-1], su[1] + 0.02))
    grl = (max(ys_l[0], sl[0] - 0.02), min(ys_l[-1], sl[1] + 0.02))
    _lip_bourrelet('gum_u', upper, gru, W, gum_mat, out, n=gr_spec.get('n', 16),
                   thickness=gr_spec.get('thickness_upper', 0.026) * ts,
                   w_frac=gr_spec.get('w_frac_upper', 0.80), z_frac=gr_spec.get('z_frac_upper', -0.10),
                   flex=upper_flex, ys_flex=ys_u, noise_scale=gr_spec.get('noise_scale', 0.11),
                   noise_strength=gr_spec.get('noise_strength', 0.32), seed=2.4)
    _lip_bourrelet('gum_l', lower, grl, WJ, gum_mat, out, n=gr_spec.get('n', 16),
                   thickness=gr_spec.get('thickness_lower', 0.024) * ts,
                   w_frac=gr_spec.get('w_frac_lower', 0.77), z_frac=gr_spec.get('z_frac_lower', 0.10),
                   flex=lower_flex, ys_flex=ys_l, noise_scale=gr_spec.get('noise_scale', 0.11),
                   noise_strength=gr_spec.get('noise_strength', 0.32), seed=3.9)

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
    # lid_upper_rot (boucle 21, feedback P0a « arcade sourcilière = plaque rigide,
    # pas une courbe fluide type paupière ») : rétro-compat totale (défaut = ancienne
    # rotation figée (0,0,10)) -- une bascule X légère permet d'incliner le capuchon
    # de paupière pour qu'il ÉPOUSE la calotte du globe (recessé, cf. `eye.globe_r`/
    # `socket_r`) au lieu de rester un plan plaqué à plat dessus.
    lur = eyep.get('lid_upper_rot', (0, 0, 10))
    # globe_recess (boucle 22 round 2, feedback P0 « globe = sphère POSÉE devant
    # l'orbite », répété ×2) : le globe était placé à la MÊME profondeur X que le
    # rebord de l'orbite (`ex` plein) alors que le cutter de cavité est centré plus
    # en RETRAIT (`ex*0.92`) -- le globe finissait donc plus en avant que le creux
    # censé l'accueillir, d'où la lecture "bille posée devant un trou" au lieu
    # d'un oeil enchâssé. Défaut 0.0 = rétro-compat totale (position inchangée).
    # >0 recule le CENTRE du globe (unités locales tête, pas une fraction de
    # `globe_r` -- cohérent avec les autres offsets de `eye`, ex. `socket_bevel`)
    # vers l'intérieur du crâne, sans toucher `globe_r` (l'oeil reste ÉNORME,
    # seul son enfoncement change) ni la cavité/paupières (toujours ancrées sur
    # `ex` plein -> leur rebord continue d'entourer le globe désormais plus reculé).
    grecess = eyep.get('globe_recess', 0.0)
    for s, tag in ((1, 'l'), (-1, 'r')):
        # orientation du globe (feedback boucle 19 chantier C, « iris/pupille non
        # perçus ») : BUG diagnostiqué -- `ops.blob` sans `rot_deg` laisse l'axe
        # local du globe (qui porte le gradient iris/pupille, cf. docstring
        # `materials.eye_globe` : X local = axe de regard) aligné sur les axes
        # MONDE, PAS sur la direction réelle du regard une fois la tête tournée
        # (`pitch`/`yaw`, `Rp`) -- la pupille/l'iris se retrouvaient hors-champ,
        # seule la zone sclère/anneau externe restait visible sous la caméra (lisait
        # comme une bille de verre opaque). Fix générique : on tourne le globe pour
        # que son axe local +X pointe vers l'extérieur de l'orbite dans le repère
        # MONDE de la tête (`Rp @ eye.look_dir`, +Z gardé approx. vertical -> la
        # fente de pupille reste verticale). `look_dir` (repère local tête, x=côté
        # y=avant z=haut ; défaut = grossièrement la direction caméra habituelle
        # d'un plan 3/4 -- PAS une valeur dragon figée, réglable depuis la spec
        # pour aligner le regard sur la caméra RÉELLE de la scène, cf. `scene.hero`/
        # `scene.shots` : la tolérance angulaire de la fente est étroite,
        # `pupil_width` amplifie tout écart hors axe) : marche pour n'importe
        # quelle tête pitchée/yawée, ce n'est que la direction locale qui change.
        ld = eyep.get('look_dir', (0.7, 0.45, 0.45))
        look_dir = Rp @ Vector((s * ld[0], ld[1], ld[2]))
        if look_dir.length < 1e-6:
            look_dir = Vector((s, 0.0, 0.0))
        eye_quat = look_dir.normalized().to_track_quat('X', 'Z')
        eye_rot = tuple(math.degrees(a) for a in eye_quat.to_euler())
        g = ops.blob(f'eye_{tag}', W((s * (ex - grecess), ey - 0.006, ez)), (egr, egr, egr), rot_deg=eye_rot)
        materials.assign(g, eye_m)
        out.append(g)
        lu = ops.blob(f'lid_up_{tag}', W((s * ex * 0.72, ey + 0.02, ez + esr * luz)),
                      (esr * lus[0], esr * lus[1], esr * lus[2]),
                      rot_deg=(lur[0], lur[1], s * lur[2]))
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
        # flat/twist (boucle 22, feedback P0 arcade « plaque enveloppante » — même
        # mécanisme générique que les cornes-lames/épines dorsales, défauts None/0.0 =
        # rétro-compat, section ronde inchangée) : une crête peut désormais être une
        # PLAQUE aplatie (arcade sourcilière large côté externe -> fine vers le front)
        # au lieu d'un simple bourrelet rond.
        flat = r.get('flat')
        twist = r.get('twist', 0.0)
        n_r = len(pts)
        tilts = [twist * i / (n_r - 1) for i in range(n_r)] if twist and n_r > 1 else None
        for s, tag in sides:
            wp = [Wf((s * x, y, z)) for x, y, z in pts]
            t = ops.tube(f"ridge_{r.get('id', 'r')}_{tag}", wp, radii, flat=flat,
                        tilts=[a * s for a in tilts] if tilts else None)
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
    # `bone_axis` (rétro-compat : None si absent de la spec -> matériau `bone_m`
    # inchangé) : variante anisotrope du matériau corne (stries LONGITUDINALES via
    # l'attribut `axis_uv`, cf. `materials.horn axis_uv` et `detail.write_axis_uv`)
    # -- corrige le bug diagnostiqué boucle 19 chantier C : le Wave `bone_m` marche
    # en coordonnées OBJECT, valides seulement si l'axe local Z EST l'axe de la
    # corne ; ici les tubes-courbes ont un transform identité (points déjà en
    # MONDE) -> l'axe Z « Object » est en fait l'axe Z MONDE, qui ne coïncide avec
    # l'axe de la corne QUE si elle pointe pile vers le haut -- une corne balayée
    # vers l'arrière voit ses stries couper de travers au lieu de courir le long
    # de sa longueur.
    bone_axis_m = _mat(mats, hp.get('axis_mat', 'bone_axis'))
    horn_seed = hp.get('seed', 0.0)
    # anneaux de croissance ACCENTUÉS (feedback : « cônes lisses sans texture os/
    # corne rayée ») + irrégularité PAR CORNE (feedback : « cônes parfaits sans
    # irrégularité ») : `_apply_horn_growth` est maintenant appelé PAR INDEX `k`
    # (au lieu d'une seule fois pour toute la couronne) avec une courbure/anneaux
    # légèrement dépendants de `k` (et de `horn_seed`, qui rejoue une autre
    # combinaison sans changer le nombre/l'arrangement des cornes) -> chaque corne
    # a un profil légèrement différent au lieu d'être un simple clone mis à
    # l'échelle de ses voisines. `tip_wear` (0..1, défaut 0 = rétro-compat) émousse
    # la pointe d'UNE corne sur 3 (usure d'implantation crédible, pas toutes
    # identiques).
    tip_wear = hp.get('tip_wear', 0.0)
    # ancrages : lerp base_from -> base_to (repère local tête, x=côté y=avant z=haut)
    # + éventail yaw0..yaw0+yaw_spread. « 2 maîtresses arrière » = master_w étroit,
    # size_bump fort, pitch très négatif (couchées vers la nuque), yaw_spread faible.
    bf = hp.get('base_from', (0.08, 0.10, 0.35))
    bt = hp.get('base_to', (0.27, -0.24, 0.19))
    # blade (boucle 22, feedback P0 « cornes = cônes qui finissent en pointe fine ->
    # PLAQUES élancées, base large/plate, légère torsion ») : sous-dict optionnel,
    # défaut None = rétro-compat totale (cône rond à pointe fine, comportement
    # inchangé). `flat` (0<flat<1, section aplatie via `ops.tube(flat=...)`, même
    # mécanisme que les épines dorsales P1) ; `tip_frac` (fraction de `r0` = rayon
    # PLANCHER à la pointe au lieu de ~0 -> bout émoussé, pas une aiguille) ;
    # `twist` (degrés, torsion totale base->pointe via `p.tilt` par point, `ops.tube
    # tilts=...`) -> lame plate légèrement vrillée plutôt qu'un pic conique.
    blade = hp.get('blade')
    blade_flat = blade.get('flat') if blade else None
    blade_tip_frac = blade.get('tip_frac', 0.3) if blade else None
    blade_twist = blade.get('twist', 0.0) if blade else 0.0
    for k in range(pairs):
        u = k / max(1, pairs - 1)
        sc = sizes[k]
        curl_k = hp.get('curl', 0.0) * (0.7 + 0.6 * (0.5 + 0.5 * math.sin(k * 2.7 + 1.1 + horn_seed)))
        b_k = hp.get('b', 0.30) * (1.0 + 0.09 * math.sin(k * 3.3 + 0.7 + horn_seed))
        raw_k = apply_law(hp.get('vocab', 'growth.horn_spiral'),
                          n=n_horn, a=hp.get('a', 0.10), b=b_k,
                          turns=hp.get('turns', 0.6), rise=hp.get('rise', 0.55))
        r0_k = hp.get('r0', 0.075)
        rmin_k = r0_k * blade_tip_frac if blade else 0.008
        base_radii_k = laws.power_taper(n_horn, r0_k, 1.15, rmin_k)
        ring_p_k = dict(hp['rings']) if hp.get('rings') else None
        if ring_p_k:
            ring_p_k['depth'] = ring_p_k.get('depth', 0.14) * (
                0.8 + 0.4 * (0.5 + 0.5 * math.sin(k * 4.1 + 2.0 + horn_seed)))
        raw_k, base_radii_k = _apply_horn_growth(
            raw_k, base_radii_k, ring_p=ring_p_k, curl=curl_k,
            curl_power=hp.get('curl_power', 1.6),
            root_len=hp.get('root_len', 0.0), root_bulge=hp.get('root_bulge', 1.0))
        if tip_wear and k % 3 == 0:  # pointe usée : PAS toutes les cornes identiques
            base_radii_k[-1] = max(base_radii_k[-1], base_radii_k[-2] * tip_wear)
            base_radii_k[-2] = max(base_radii_k[-2], base_radii_k[-3] * tip_wear * 0.85)
        radii = [r * (0.45 + 0.55 * sc) for r in base_radii_k]
        yaw = hp.get('yaw0', 6) + u * hp.get('yaw_spread', 62)
        hpitch = hp.get('pitch', -35) - u * hp.get('pitch_spread', 20)
        jit = 0.05 * math.sin(k * 5.1)
        base = (bf[0] + (bt[0] - bf[0]) * u, bf[1] + (bt[1] - bf[1]) * u,
                bf[2] + (bt[2] - bf[2]) * u + jit)
        for s, tag in ((1, 'l'), (-1, 'r')):
            pts = ops.transform_pts(raw_k, loc=W((s * base[0], base[1], base[2])),
                                    rot_deg=(pitch + hpitch, 0, s * (yaw + 6 * jit)),
                                    scale=sc * hp.get('scale', 1.0))
            # résolution réduite (budget sommets) : `n_horn` points de contrôle portent
            # déjà le détail (anneaux), la résolution NURBS/bevel par défaut (pensée
            # pour des tubes à peu de points, ex. dents/crêtes) est inutilement dense.
            tilts_k = ([blade_twist * i / (n_horn - 1) for i in range(n_horn)]
                      if blade_twist else None)
            h = ops.tube(f'horn_{tag}{k}', pts, radii, resolution_u=6, bevel_resolution=6,
                        flat=blade_flat, tilts=tilts_k)
            materials.assign(h, bone_m)
            if bone_axis_m:
                # réalisé en MESH (nécessaire pour porter un attribut vertex,
                # cf. `detail.write_axis_uv`) -- même schéma que `_apply_fuse_detail`/
                # `_apply_armor` (bake CURVE->MESH via depsgraph, aucun bpy.ops).
                h = core.realize_to_mesh(h)
                _detail.write_axis_uv(h, pts)
                h.data.materials.clear()
                h.data.materials.append(bone_axis_m)
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


def _ellipsoid_surface(d, size):
    """Point ANALYTIQUE (pas de raycast) sur la surface d'un ellipsoïde de
    demi-tailles `size` (x, y, z), dans la direction `d` depuis son centre.
    Retourne (point, unit_dir). Utilisé par `head_galet` pour poser des éléments
    (yeux) EN SURFACE d'une tête-galet sans creuser de cavité."""
    dx, dy, dz = d
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    ux, uy, uz = dx / n, dy / n, dz / n
    denom = (ux / size[0]) ** 2 + (uy / size[1]) ** 2 + (uz / size[2]) ** 2
    t = 1.0 / math.sqrt(denom) if denom > 1e-9 else 0.0
    return (ux * t, uy * t, uz * t), (ux, uy, uz)


@builder('head_galet')
def head_galet(part, mats):
    """Tête « galet-axolotl » (boucle 23 P0-B, thème « UNE SEULE PEAU » — remplace
    `head`, ZÉRO booléen). Base = UV sphere écrasée en Z / élargie en XY (galet
    plat, large, arrondi vers les joues), coords bakées directement dans le mesh
    (pas `object.scale` : le museau suivant a besoin d'unités réelles). Museau =
    étirement PROPORTIONNEL des vertices avant (falloff lisse selon `y` local,
    PAS une découpe) -> grand U, presque grenouille. Yeux posés EN SURFACE
    (`_ellipsoid_surface`, calcul analytique, pas de cavité creusée) + UNE
    paupière-plaque par œil (portion de sphère aplatie) qui coiffe le dessus.
    Oreilles/appendices = plaques coniques écrasées (`ops.spike(flatten=...)`)
    ANCRÉES sur la surface réelle (`ear.dir` -> `_ellipsoid_surface`, base
    enfoncée `embed_frac*height`), générique via la liste `ears` (nombre/tailles/
    positions arbitraires -- 2 grandes + 2 moyennes + petites pointes = un CHOIX
    de spec, pas de code).
    La tête n'est PAS soudée ici (ce builder ne voit pas les autres parts) :
    `weld_groups` (voir `_apply_weld_groups`) fait la soudure crâne<->cou après
    assemblage, comme le faisait `wing weld=true` pour les ailerons caudaux."""
    L = Vector(part['loc'])
    pitch = part.get('pitch', 0.0)
    yaw = part.get('yaw', 0.0)
    Rp = Euler((math.radians(pitch), 0, math.radians(yaw))).to_matrix()
    skin = _mat(mats, part.get('mat', 'scales'))
    out = []

    def W(p):
        v = Rp @ Vector(p)
        return (L.x + v.x, L.y + v.y, L.z + v.z)

    seg = part.get('seg', 30)
    size = tuple(part.get('size', (0.34, 0.30, 0.19)))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(4, seg // 2), radius=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]

    # --- museau : falloff proportionnel des vertices avant (y local > y0), PAS de
    # découpe -- pousse vers l'avant (push_y), évase latéralement (push_x, le U
    # s'élargit vers la pointe) et remonte légèrement le dessous (flatten_z, un
    # museau plat pas un bec). `power` (>1) concentre l'étirement vers l'avant.
    sn = part.get('snout', {})
    y0 = sn.get('y0_frac', 0.20) * size[1]
    push_y = sn.get('push_y', 0.18)
    push_x = sn.get('push_x', 0.14)
    flatten_z = sn.get('flatten_z', 0.05)
    power = sn.get('power', 1.4)
    yr = max(size[1] - y0, 1e-4)
    for v in bm.verts:
        if v.co.y > y0:
            f = min(((v.co.y - y0) / yr) ** power, 1.0)
            v.co.y += push_y * f
            if abs(v.co.x) > 1e-6:
                v.co.x += math.copysign(push_x * f * (abs(v.co.x) / max(size[0], 1e-4)), v.co.x)
            if v.co.z < 0:
                v.co.z += flatten_z * f * 0.6

    for v in bm.verts:  # bake en MONDE (convention du reste du fichier)
        v.co = Rp @ v.co + L
    bm.normal_update()
    mesh = bpy.data.meshes.new(part.get('id', 'head'))
    bm.to_mesh(mesh)
    bm.free()
    sk = core.link(bpy.data.objects.new(part.get('id', 'head'), mesh))
    core.shade_smooth(sk)
    hsub = part.get('subsurf', 1)
    if hsub:
        core.subsurf(sk, hsub)
    materials.assign(sk, skin)
    out.append(sk)

    # --- yeux : globe posé EN SURFACE (pas de cavité), enfoncé de `surf_offset`
    # (fraction de son propre rayon) pour paraître enchâssé plutôt que collé --
    # même convention d'orientation que l'ancien `head` (axe local +X du globe =
    # direction du regard, cf. `materials.eye_globe`). `dir` place le globe sur
    # l'ellipsoïde d'origine (zone NON déformée par le museau -> surface exacte) ;
    # `look_dir` distinct oriente le regard vers l'AVANT (prédateur) indépendamment
    # de la position latérale du globe. ---
    eyep = part.get('eye', {})
    eye_m = _mat(mats, eyep.get('mat', 'eye'))
    edir = eyep.get('dir', (0.85, 0.30, 0.35))
    egr = eyep.get('globe_r', 0.115)
    surf_off = eyep.get('surf_offset', 0.55)
    lus = eyep.get('lid_scale', (0.55, 0.70, 0.34))
    luz = eyep.get('lid_z_off', 0.60)
    lur = eyep.get('lid_rot', (-16, 8, 14))
    for s, tag in ((1, 'l'), (-1, 'r')):
        p_local, u_local = _ellipsoid_surface((s * edir[0], edir[1], edir[2]), size)
        center_local = tuple(c - u * egr * surf_off for c, u in zip(p_local, u_local))
        ld = eyep.get('look_dir', (0.55, 0.75, 0.25))
        look_dir = Rp @ Vector((s * ld[0], ld[1], ld[2]))
        if look_dir.length < 1e-6:
            look_dir = Vector((s, 0.0, 0.0))
        eye_quat = look_dir.normalized().to_track_quat('X', 'Z')
        eye_rot = tuple(math.degrees(a) for a in eye_quat.to_euler())
        g = ops.blob(f'eye_{tag}', W(center_local), (egr, egr, egr), rot_deg=eye_rot)
        materials.assign(g, eye_m)
        out.append(g)
        lid_pos = (center_local[0], center_local[1] + egr * 0.05, center_local[2] + egr * luz)
        lid = ops.blob(f'lid_up_{tag}', W(lid_pos), (egr * lus[0], egr * lus[1], egr * lus[2]),
                       rot_deg=(lur[0], lur[1], s * lur[2]))
        materials.assign(lid, skin)
        out.append(lid)

    # --- oreilles/appendices : plaques triangulaires charnues APLATIES, ANCRÉES sur
    # la coque (round 2 boucle 23, fix « lisent comme des cubes épars/flottants ») --
    # liste générique, N'IMPORTE quelle spec pilote nombre/tailles/positions (2
    # grandes + 2 moyennes + petites pointes de mâchoire = choix de spec, pas de
    # code dédié). `dir` (comme `eye.dir`) place la BASE sur la surface réelle de
    # l'ellipsoïde-crâne via `_ellipsoid_surface` (calcul analytique, même
    # convention que les yeux) -- élimine le placement `pos` à la main qui dérive
    # facilement en l'air (le bug mesuré : nub flottant sous le museau). La base est
    # ensuite ENFONCÉE dans la coque de `embed_frac*height` le long de la normale
    # locale (au lieu d'être posée dessus avec un interstice visible) -- la plaque
    # prolonge donc la surface plutôt que de flotter dessus. L'axe local Z de la
    # plaque (base->pointe, cf. `ops.spike`) est aligné sur la normale de surface
    # puis `tilt` (degrés, XYZ, appliqué APRÈS l'alignement -> tourne dans le repère
    # propre de la plaque) balaie la pointe vers l'arrière/le haut, générique --
    # aucune valeur figée, tout vient de la spec. `seg` monté par défaut à 16 (au
    # lieu de 8) : le bord large d'une grande plaque aplatie a besoin de plus de
    # segments pour lire comme une courbe lisse plutôt qu'un polygone à facettes
    # visibles (l'effet « cube » du round 1). `pos`/`rot` bruts restent le mode
    # rétro-compat si `dir` est absent d'une entrée. ---
    ear_m_default = skin
    for e in part.get('ears', []):
        height = e.get('height', 0.16)
        radius = e.get('radius', 0.11)
        flat = e.get('flatten', (0.55, 1.0))
        tip_frac = e.get('tip_frac', 0.32)
        mirror = e.get('mirror', True)
        seg = e.get('seg', 16)
        em = _mat(mats, e.get('mat')) if e.get('mat') else ear_m_default
        sides = ((1, 'l'), (-1, 'r')) if mirror else ((1, ''),)
        edir = e.get('dir')
        if edir is not None:
            embed = e.get('embed_frac', 0.35)
            tilt = e.get('tilt', (0.0, 0.0, 0.0))
            for s, tag in sides:
                p_local, u_local = _ellipsoid_surface((s * edir[0], edir[1], edir[2]), size)
                u = Vector(u_local)
                if u.length < 1e-6:
                    u = Vector((s, 0.0, 0.0))
                base = Vector(p_local) - u * (height * embed)
                center_local = base + u * (height * 0.5)
                quat = u.normalized().to_track_quat('Z', 'Y')
                if any(tilt):
                    tquat = Euler((math.radians(tilt[0]), math.radians(tilt[1]),
                                   math.radians(s * tilt[2])), 'XYZ').to_quaternion()
                    quat = quat @ tquat
                rot = tuple(math.degrees(a) for a in quat.to_euler())
                ear = ops.spike(f"ear_{e.get('id', 'e')}_{tag}", W(tuple(center_local)),
                                height, radius, rot, seg=seg, flatten=flat, tip_frac=tip_frac)
                materials.assign(ear, em)
                out.append(ear)
        else:
            pos = e['pos']
            rot = e.get('rot', (90, 0, 0))
            for s, tag in sides:
                ear = ops.spike(f"ear_{e.get('id', 'e')}_{tag}", W((s * pos[0], pos[1], pos[2])),
                                height, radius, (rot[0], rot[1], s * rot[2]), seg=seg,
                                flatten=flat, tip_frac=tip_frac)
                materials.assign(ear, em)
                out.append(ear)
    return out


def _apply_weld_groups(spec, groups):
    """`weld_groups` (générique, boucle 23 — étend le `weld=true` local à `wing`
    à N'IMPORTE QUELLE paire/liste de groupes, ex. tête<->cou) : liste de
    `{id, parts:[...], exclude_like:[...]}`. Fusionne en UN SEUL mesh continu
    (`ops.boolean_union`, solveur EXACT + `material_mode='TRANSFER'` — cf.
    docstring `ops.boolean_union` pour le bug de fusion de matériaux évité) tous
    les objets MESH des `parts` listées, hors motifs `exclude_like` (ex. yeux/
    paupières qui doivent rester des objets séparés posés dessus, pas fusionnés).
    Le mesh soudé remplace en place le groupe de la PREMIÈRE part listée, même
    convention que `_apply_fuse_groups` (armor/displace qui ciblent cet id n'ont
    rien à changer)."""
    wgs = spec.get('weld_groups', [])
    if not wgs:
        return
    for wg in wgs:
        parts = wg.get('parts', [])
        exclude = wg.get('exclude_like', [])
        for pid in parts:
            groups[pid] = [core.realize_to_mesh(o) if o.type == 'CURVE' else o
                          for o in groups.get(pid, [])]
        seen, objs = set(), []
        for pid in parts:
            for o in groups.get(pid, []):
                if o.type != 'MESH' or o.name in seen or any(x in o.name for x in exclude):
                    continue
                seen.add(o.name)
                objs.append(o)
        if len(objs) < 2:
            continue
        consumed_ids = {id(o) for o in objs}
        primary = parts[0]
        fused = ops.boolean_union(primary, objs)
        for gid in list(groups.keys()):
            groups[gid] = [o for o in groups[gid] if id(o) not in consumed_ids]
        groups[primary] = [fused] + groups.get(primary, [])


@builder('dewlap')
def dewlap(part, mats):
    """Fanon de gorge : chaîne CONTINUE de plis charnus qui pendent sous la mâchoire/
    le cou (feedback boucle 19 chantier C, diagnostic déjà posé : les points de
    contrôle de la spec (`pts`) sont souvent plus ESPACÉS (~0.44-0.96u, cf. distance
    entre points consécutifs) que la longueur d'un maillon (`sizes`*~2.7*2, ~0.26-
    0.52u) -> un maillon par point de contrôle laisse du vide entre deux blobs, lu
    comme des ovales FLOTTANTS près de la gorge plutôt qu'une chaîne continue).
    Fix générique (pas de valeur dragon) : on RE-ÉCHANTILLONNE la polyligne
    (position ET taille interpolées linéairement) pour qu'aucun segment entre deux
    centres consécutifs n'excède `(1-overlap) * y_reach * (taille_i + taille_{i+1})`
    -- exactement la somme des DEMI-longueurs de deux maillons voisins (un maillon de
    taille r s'étend de `r*y_reach` de chaque côté de son centre) réduite par la
    fraction de recouvrement cible `overlap` (0..1, défaut 0.3 = un maillon mord de
    30% sur son voisin). `y_reach` = même facteur d'allongement que le maillon
    principal historique (2.7). `seg` (résolution des blobs, PLUS BAS que le défaut
    `ops.blob` 32) : la chaîne comporte maintenant plus de maillons -> réduire leur
    résolution individuelle tient le budget sommets sans perdre en continuité (un
    maillon modeste mais bien connecté à ses voisins lit mieux qu'un maillon isolé
    très lisse)."""
    pts = [tuple(p) for p in part['pts']]
    sizes = list(part['sizes'])
    mat = _mat(mats, part.get('mat', 'scales'))
    overlap = part.get('overlap', 0.3)
    y_reach = part.get('y_reach', 2.7)
    seg = part.get('seg', 20)
    out = []
    # --- densification adaptative : insère des points intermédiaires (position +
    # taille interpolées) là où l'espacement dépasse la cible de recouvrement ---
    dense_pts, dense_sizes = [pts[0]], [sizes[0]]
    for i in range(len(pts) - 1):
        p0, p1 = pts[i], pts[i + 1]
        r0, r1 = sizes[i], sizes[i + 1]
        d = math.dist(p0, p1)
        target_gap = max(1e-4, (1.0 - overlap) * y_reach * (r0 + r1))
        m = max(1, math.ceil(d / target_gap))
        for k in range(1, m + 1):
            t = k / m
            dense_pts.append(tuple(p0[j] + (p1[j] - p0[j]) * t for j in range(3)))
            dense_sizes.append(r0 + (r1 - r0) * t)
    n = len(dense_pts)
    for i, (p, r) in enumerate(zip(dense_pts, dense_sizes)):
        # masse principale allongée le long du cou (recouvre le(s) point(s) voisin(s)
        # d'au moins `overlap`) : fond la chaîne en une seule poche continue plutôt
        # qu'un chapelet de perles — ratios aplatis (pas proches de la sphère, sinon
        # rendu en chapelet d'œufs).
        b = ops.blob(f"dewlap_{part.get('id', 'd')}_{i}", p, (r * 0.5, r * y_reach, r * 0.78), seg=seg)
        materials.assign(b, mat)
        out.append(b)
        if i < n - 1:
            # petit pli superposé entre deux maillons, discret (pas une grosse sphère)
            nxt = dense_pts[i + 1]
            mid = tuple((p[k] + nxt[k]) / 2 for k in range(3))
            fr = (r + dense_sizes[i + 1]) * 0.30
            fold = (mid[0], mid[1], mid[2] - fr * 0.55)
            f = ops.blob(f"dewlap_fold_{part.get('id', 'd')}_{i}", fold,
                        (fr * 0.75, fr * 1.3, fr * 0.55), seg=seg)
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
    # vein_mat (chantier B, boucle 19, défaut = bone_mat, rétro-compat) : teinte
    # DÉDIÉE pour l'arbre de veines, distincte de l'os de l'aile -> contraste
    # visible contre la membrane rétro-éclairée (feedback : le réseau géométrique
    # doit se LIRE, pas se fondre avec les lattes/doigts du même ton).
    vein_mat_key = part.get('vein_mat', bone_mat_key)
    # pid (fix boucle 20, note ref-analyst) : préfixe TOUS les noms d'objets de cette
    # part avec son propre id -> plusieurs parts `wing` dans la même spec (ex.
    # wing/hipfin/tailfin_nat/tailfin_pros) ne collisionnent plus sur les mêmes noms
    # génériques (membrane_L, wclaw_L0...) -> `feedback.part_bbox`/`frame_part`
    # retrouvent chaque part individuellement. Substrings (`exclude_like`/
    # `frame_match`/`displace_targets.match`) restent valides (recherche par `in`).
    pid = part.get('id', 'wing')
    # weld (boucle 22, thème « souder pas poser » — feedback P0 aileron caudal
    # « pièces disjointes flottantes ») : défaut False = rétro-compat totale (objets
    # séparés comme avant). Si True, TOUS les objets os/membrane construits pour ce
    # côté (bras, doigts, griffes, lattes, veines, membrane...) sont soudés en un seul
    # mesh continu par booléen UNION exact (`ops.boolean_union`, PAS de voxel remesh —
    # piège connu, gonfle ×3 les tubes fins) au lieu de rester des primitives qui se
    # touchent seulement visuellement. Utile pour un petit aileron où la couture
    # os->membrane doit lire comme UNE pièce, pas pour les grandes ailes principales
    # (coût du solveur exact + inutile, membranes déjà validées).
    weld = part.get('weld', False)
    # skip_bones (round 2 boucle 23, feedback « ailerons caudaux = assemblage de
    # cônes ») : défaut False = rétro-compat totale (bras/main/doigts/griffes comme
    # avant). True -> ne construit PLUS aucun tube os séparé (arm/hand/finger/
    # wclaw/alula) -- seulement la membrane (déjà une PLANE en éventail, cf.
    # `col_pts`/`grid_surface`) : pour un petit aileron simple, le tube "doigt"
    # tracé le long du bord de la membrane fait doublon avec le bord lui-même et se
    # lit comme un cône rond posé dessus plutôt qu'une nervure. `edge_ridge_height`
    # (défaut 0.0) remplace ce tube par un RENFLEMENT directement dans le maillage
    # de la membrane (colonnes "doigt", cf. plus bas) -- une nervure = un bombé du
    # même mesh, pas un objet en plus.
    skip_bones = part.get('skip_bones', False)
    edge_ridge_height = part.get('edge_ridge_height', 0.0)
    for s in sides:
        tag = 'L' if s > 0 else 'R'
        weld_start = len(out)
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
        if not skip_bones:
            if part.get('muscles') or part.get('joints') or part.get('folds'):
                arm = _anatomical_tube(f'{pid}_arm_{tag}', [sh, el, wr], arm_radii,
                                       muscles=part.get('muscles'), joints=part.get('joints'),
                                       folds=part.get('folds'), mirror_sign=s)
            else:
                arm = ops.tube(f'{pid}_arm_{tag}', [sh, el, wr], arm_radii, order=arm_order)
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

        if not skip_bones and knuckle_spread > 0 and n_fingers > 0:
            hand_r0 = arm_radii[-1] * 1.05
            hand_r1 = max(part.get('finger_r0', 0.085) * 0.9, arm_radii[-1] * 0.5)
            far = knuckles[0]
            hand_pts = [W, W.lerp(far, 0.55), far]
            hand_radii = [hand_r0, (hand_r0 + hand_r1) * 0.5, hand_r1]
            hand = ops.tube(f'{pid}_hand_{tag}', [tuple(p) for p in hand_pts], hand_radii)
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
        # edge_ridge_height (round 2 boucle 23, cf. `skip_bones` ci-dessus) : bombe
        # directement les colonnes "racine du doigt" (`col_bow[gi] is not None`,
        # même repère que le tube `finger` qu'on supprime) le long de Z, profil
        # sin(pi*t) (nul à la racine ET au bord libre, max au milieu) -> une
        # nervure EN RELIEF dans le mesh de la membrane, pas un tube collé dessus.
        if edge_ridge_height:
            for gi, col in enumerate(cols):
                if col_bow[gi] is None:
                    continue
                m = len(col)
                for i in range(m):
                    t = i / (m - 1) if m > 1 else 0.0
                    x, y, z = col[i]
                    col[i] = (x, y, z + edge_ridge_height * math.sin(math.pi * t))
        # épaisseur dégradée par rangée : racine (i=0, le long des os) épaisse, bord
        # libre (dernière rangée) fin -> remplace le Solidify constant, donne le
        # volume "planche à voile" au lieu d'une membrane plate.
        thickness_rows = [th_root + (th_edge - th_root) * (i / (nt - 1)) ** 0.7
                          for i in range(nt)]
        mem = ops.grid_surface(f'{pid}_membrane_{tag}', cols, thickness=thickness_rows)
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
                    batt = ops.tube(f'{pid}_batten_{tag}{j}_{bi}', bpts, batten_radii)
                    materials.assign(batt, _mat(mats, bone_mat_key))
                    out.append(batt)
        # veines de membrane EN ARBRE (chantier B, boucle 19 : le motif Voronoï du
        # matériau `membrane` lit comme des cellules abstraites, pas un réseau —
        # remplacé ici par une VRAIE géométrie ramifiée). Depuis chaque doigt, un
        # tronc part vers le bord de fuite du panneau voisin (comme avant), puis
        # BIFURQUE récursivement (`vein_levels` générations, `vein_children`
        # embranchements par génération) : à chaque génération une partie des
        # rameaux continue vers le bord de fuite (en s'affinant, `vein_taper`) et un
        # rameau plus court repart vers la RACINE (l'attache du doigt) — un arbre
        # hiérarchique DIRECTIONNEL, pas un balai de segments parallèles ni des
        # cellules. Suit le même relief (sag/camber/panel_billow, via `panel_pt`)
        # que les colonnes de membrane -> reste COLLÉ à la surface.
        vein_branches = part.get('vein_branches', 0)
        if vein_branches:
            vein_r0 = part.get('vein_branch_r0', batten_r0 / 3.0)
            vein_rmin = part.get('vein_branch_rmin', vein_r0 * 0.3)
            vein_levels = max(0, int(part.get('vein_levels', 2)))
            vein_children = max(1, int(part.get('vein_children', 2)))
            vein_taper = part.get('vein_taper', 0.6)
            vein_root_frac = part.get('vein_root_frac', 0.4)
            _vein_id = itertools.count()

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

            def vein_branch(p0, p1, gen, r0, j, bi, root_ref, max_reach):
                vr = laws.power_taper(3, r0, 1.1, max(vein_rmin, r0 * 0.3))
                pmid = p0.lerp(p1, 0.5)
                res_u, bev_res = (4, 3) if gen == 0 else (3, 2)
                vtube = ops.tube(f'{pid}_vein_{tag}{j}_{bi}_{gen}_{next(_vein_id)}',
                                 [tuple(p0), tuple(pmid), tuple(p1)], vr,
                                 resolution_u=res_u, bevel_resolution=bev_res)
                materials.assign(vtube, _mat(mats, vein_mat_key))
                out.append(vtube)
                if gen >= vein_levels:
                    return
                seg = p1 - p0
                if seg.length < 1e-6:
                    return
                perp = seg.cross(Vector((0, 0, 1)))
                if perp.length < 1e-6:
                    perp = Vector((1, 0, 0))
                perp.normalize()
                for c in range(vein_children):
                    fc = (c + 1) / (vein_children + 1)
                    start = p0.lerp(p1, 0.30 + 0.4 * fc)
                    sign = 1.0 if c % 2 == 0 else -1.0
                    # rameau DISTAL : continue vers le bord de fuite, s'écarte du tronc
                    # (portée réduite chantier B fix, cf. note ci-dessous : 0.55/0.28
                    # -> 0.4/0.16, moins d'élan pour moins dépasser)
                    end_distal = (start + seg * (0.4 * vein_taper)
                                  + perp * sign * seg.length * 0.16 * vein_taper)
                    # FIX régression boucle 19 (step_238_hero) : extrapolation en 3D
                    # pure, sans lien avec le panneau (u,t) -> un rameau distal peut
                    # dépasser `p1` (déjà proche du bord de fuite, t_end<=0.92) et
                    # sortir de la membrane (filaments qui dépassent la silhouette).
                    # `root_ref`/`max_reach` = CENTRE et rayon d'une sphère de sécurité
                    # établie sur le tronc de génération 0 (seul segment garanti dans
                    # la membrane par construction, marge t/u incluse) : la sphère est
                    # centrée sur le MILIEU du tronc avec un rayon réduit (0.55x sa
                    # demi-longueur) pour rester near l'intérieur du panneau (étroit
                    # latéralement) plutôt que de permettre tout le rayon jusqu'à p1
                    # (qui laissait passer des rameaux latéraux hors silhouette) — aucun
                    # point ne peut s'en éloigner plus loin, quelle que soit la
                    # direction -> clippe avant de sortir du panneau au lieu de laisser
                    # filer le rameau.
                    d = end_distal - root_ref
                    dlen = d.length
                    if dlen > max_reach:
                        end_distal = root_ref + d * (max_reach / dlen)
                    vein_branch(start, end_distal, gen + 1, r0 * vein_taper, j, bi,
                                root_ref, max_reach)
                # rameau PROXIMAL : un seul par génération, court, repart vers la
                # racine (l'attache du doigt) -> bifurque aussi en arrière, pas
                # seulement vers l'avant (lecture "arbre", pas "balai"). Reste
                # toujours entre p0 et p1 (barycentre) donc déjà dans la sphère de
                # référence -> pas besoin de clamp.
                root_start = p0.lerp(p1, 0.12)
                root_end = root_start.lerp(p0, vein_root_frac)
                if (root_end - root_start).length > 1e-5:
                    vein_branch(root_start, root_end, gen + 1, r0 * vein_taper * 0.85, j, bi,
                                root_ref, max_reach)

            for j in range(len(ends) - 1):
                for bi in range(vein_branches):
                    frac = (bi + 1) / (vein_branches + 1)
                    t_start = 0.18 + 0.12 * bi   # démarre au tiers proximal du doigt
                    t_end = 0.92 - 0.08 * bi     # s'approche du bord libre sans l'atteindre
                    u_end = 0.22 + 0.5 * frac    # s'écarte du doigt vers le panneau voisin
                    p0 = finger_pt(j, t_start)
                    p1 = panel_pt(j, u_end, t_end)
                    # sphère de sécurité centrée sur le MILIEU du tronc (pas une
                    # extrémité) : rayon = demi-longueur + marge modeste -> reste
                    # proche du tronc établi (déjà validé dans le panneau) au lieu
                    # d'autoriser tout le rayon d'une extrémité à l'autre (trop
                    # généreux latéralement pour un panneau étroit, cf. fix ci-dessus).
                    trunk_center = p0.lerp(p1, 0.5)
                    trunk_reach = (p1 - p0).length * 0.5 * 1.2
                    vein_branch(p0, p1, 0, vein_r0, j, bi, trunk_center, trunk_reach)
        # doigts osseux : bourrelets SAILLANTS posés SUR la membrane (relief), pas des
        # tiges flottantes séparées -> soulevés de `finger_lift` le long de z (même
        # convention que les lattes) pour lire comme une arête en relief sur la surface.
        # Arqués (finger_bow) en éventail au lieu de rayons rectilignes W->tip.
        if not skip_bones:
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
                f = ops.tube(f'{pid}_finger_{tag}{j}', fpts, fr)
                materials.assign(f, _mat(mats, bone_mat_key))
                out.append(f)
                claw = ops.spike(f'{pid}_wclaw_{tag}{j}', (tip[0], tip[1], tip[2] + finger_lift),
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
            afin = ops.tube(f'{pid}_alula_{tag}', a_pts, a_radii)
            materials.assign(afin, _mat(mats, bone_mat_key))
            out.append(afin)
            aclaw = ops.spike(f'{pid}_aclaw_{tag}', (a_tip[0], a_tip[1], a_tip[2] + finger_lift),
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
            a_mem = ops.grid_surface(f'{pid}_alula_mem_{tag}', [arm_col, tip_col],
                                     thickness=[t * 0.55 for t in thickness_rows])
            materials.assign(a_mem, _mat(mats, part.get('mat', 'membrane')))
            out.append(a_mem)

        if weld:
            side_objs = [core.realize_to_mesh(o) if o.type == 'CURVE' else o
                        for o in out[weld_start:]]
            del out[weld_start:]
            if len(side_objs) >= 2:
                fused = ops.boolean_union(f'{pid}_fin_{tag}', side_objs)
                out.append(fused)
            else:
                out.extend(side_objs)
    return out


def _frame_init(tangent):
    """Repère transporté : alias de `ops.frame_init` (chantier B, boucle 19 — la
    même implémentation est réutilisée par `detail.write_axis_uv`/`armor_rows`,
    déplacée dans `ops` pour être partagée sans import circulaire)."""
    return ops.frame_init(tangent)


def _frame_step(prev_tangent, prev_right, tangent):
    """Alias de `ops.frame_step` (cf. `_frame_init`)."""
    return ops.frame_step(prev_tangent, prev_right, tangent)


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
    # skip_tube (boucle 23, thème « UNE SEULE PEAU ») : défaut False = rétro-compat
    # totale (tube de patte construit ici, comportement historique). True = le
    # volume de la patte est déjà porté par une branche `skin_body.limbs` (mesh
    # continu soudé au corps) -- ce builder ne construit alors QUE le pied/orteils/
    # griffes, ancrés sur `foot.loc` comme avant (aucun changement de ce côté).
    skip_tube = part.get('skip_tube', False)
    for s in sides:
        tag = 'L' if s > 0 else 'R'
        pts = [(s * p[0], p[1], p[2]) for p in part['pts']]
        radii = part.get('radii') or laws.power_taper(len(pts), part.get('r0', 0.3), 1.0, 0.1)
        if not skip_tube:
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


@builder('cage')
def cage(part, mats):
    """Pivot sculpteur (b24) : cage basse résolution posée VERTEX PAR VERTEX dans la spec
    (`verts` [[x,y,z],...] + `faces` [[i,...],...], quads de préférence), miroir X
    optionnel (`mirror_x`, défaut True : la spec ne porte que la moitié +X) puis subsurf.
    UNE SEULE PEAU par construction — ni boolean ni primitive ; les proportions se jugent
    à la silhouette (`run.py silh`), le détail vient APRÈS (detail.armor), pas ici."""
    me = bpy.data.meshes.new(part['id'])
    me.from_pydata([tuple(v) for v in part['verts']], [], [tuple(f) for f in part['faces']])
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(part['id'], me)
    core.link(ob)
    if part.get('mirror_x', True):
        core.mirror(ob)
    core.shade_smooth(ob)
    core.subsurf(ob, part.get('subsurf', 2))
    materials.assign(ob, _mat(mats, part.get('mat', 'scales_body')))
    return [ob]


@builder('globe')
def globe(part, mats):
    """Blob de surface générique (b25 : yeux/paupières posés SUR la cage — objets
    séparés, convention b23 conservée : ids préfixés `eye_`/`lid_`, déjà filtrés par
    detail.armor & co). `pos` = centre, `r` = rayon scalaire ou [rx,ry,rz], `look_dir`
    aligne l'axe local +X (direction du regard, cf. materials.eye_globe), `rot` =
    Euler degrés appliqué à défaut de look_dir, `mirror_x` duplique en ±X (_l/_r)."""
    r = part.get('r', 0.1)
    scale = tuple(r) if isinstance(r, (list, tuple)) else (r, r, r)
    px, py, pz = part['pos']
    sides = ((1, '_l'), (-1, '_r')) if part.get('mirror_x', True) else ((1, ''),)
    out = []
    for s, suf in sides:
        ld = part.get('look_dir')
        if ld:
            q = Vector((s * ld[0], ld[1], ld[2])).normalized().to_track_quat('X', 'Z')
            rot = tuple(math.degrees(a) for a in q.to_euler())
        else:
            rx, ry, rz = part.get('rot', (0, 0, 0))
            rot = (rx, ry, s * rz)
        g = ops.blob(part['id'] + suf, (s * px, py, pz), scale, rot_deg=rot)
        materials.assign(g, _mat(mats, part.get('mat', 'scales_body')))
        out.append(g)
    return out


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


def _path_for_part(spec, part_id, side_tag=None):
    """Polyligne de contrôle MONDE (`pts`) d'une part `spine`/`limb` de la spec,
    mirorée selon `side_tag` ('R' inverse x) — même convention que `limb()`/
    `wing()` (x=côté). Chemin de référence PARTAGÉ par `_apply_axis_uv` (attribut
    shader) et les entrées d'armure `layout:'rows'` (`detail.armor_rows`) : une
    seule source de vérité (aucune valeur dragon, dérivée de la spec)."""
    for part in spec.get('parts', []):
        if (part.get('id') or '') != part_id:
            continue
        pts = part.get('pts')
        if not pts:
            return None
        if side_tag == 'R':
            return [(-p[0], p[1], p[2]) for p in pts]
        return [tuple(p) for p in pts]
    return None


def _retint_axis(ob, spec, axis_mat_key):
    """Bascule le matériau d'un objet qui vient de recevoir l'attribut `axis_uv`
    vers sa variante anisotrope (`axis_mat`, ex. 'scales_head'/'scales_legs') SANS
    toucher aux AUTRES sous-objets de la même part (crêtes/blobs/lèvres pour la
    tête, coussinet/orteils pour la patte) qui n'ont PAS reçu l'attribut -- leur
    laisser le matériau isotrope par défaut évite une Attribute node qui renverrait
    (0,0,0) (aucun attribut sur leur mesh) et casserait leur motif d'écailles."""
    mat = spec.get('_mats', {}).get(axis_mat_key)
    if not mat:
        return
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def _apply_axis_uv(spec, groups):
    """Coordonnée curviligne GÉNÉRIQUE (chantier B, boucle 19, faute F4 : « bruit
    isotrope vendu comme organique ») : écrit sur les meshes tubulaires (spine,
    limb) un attribut vertex `axis_uv` (Vector POINT, cf. `detail.write_axis_uv`)
    — u = abscisse curviligne 0..1 le long de l'axe anatomique, v = angle 0..1
    autour de la section. Calculé à partir de la POSITION finale du sommet vs. le
    chemin `pts` connu de la spec (pas d'un attribut de construction) : reste
    valide même si le mesh a ensuite été fusionné/remaillé (`fuse_groups`, SDF)
    -> exposé aux shaders anisotropes (`materials.reptile_scales axis_uv=True`)
    sur le corps fusionné comme sur une pièce non fusionnée. `axis_mat` (optionnel
    dans la spec de la part) bascule SEULEMENT l'objet qui reçoit l'attribut vers
    une variante anisotrope du matériau (cf. `_retint_axis`) -- le `mat` par défaut
    de la part reste inchangé pour ses autres sous-objets.
    Tête : chemin centreligne crâne->museau (axe local Y de `head()`, même repère
    loc/pitch/yaw) sur les objets `skull`/`jaw` uniquement -- traite le cas F4
    « texture face uniforme » sans dupliquer le builder de tête."""
    from . import detail as _detail
    for i, part in enumerate(spec['parts']):
        ptype = part.get('type')
        if ptype not in ('spine', 'limb') or not part.get('pts'):
            continue
        gid = part.get('id') or f"{ptype}_{i}"
        axis_mat = part.get('axis_mat')
        if ptype == 'spine':
            path = _path_for_part(spec, gid)
            for ob in groups.get(gid, []):
                if ob.type == 'MESH' and ob.name == gid:
                    _detail.write_axis_uv(ob, path)
                    if axis_mat:
                        _retint_axis(ob, spec, axis_mat)
        else:
            for tag in ('L', 'R'):
                path = _path_for_part(spec, gid, tag)
                for ob in groups.get(gid, []):
                    if ob.type != 'MESH':
                        continue
                    if ob.name == f'{gid}_{tag}':
                        _detail.write_axis_uv(ob, path)
                        if axis_mat:
                            _retint_axis(ob, spec, axis_mat)
                    elif f'_{tag}' in ob.name and 'axis_uv' not in ob.data.attributes:
                        # annexes du membre (toe/footpad/claw…) : elles partagent
                        # les matériaux axis_uv du tube — sans l'attribut le
                        # shader dégénère (Voronoï à coordonnée constante =
                        # pad pâle uniforme, constat critique boucle 19)
                        _detail.write_axis_uv(ob, path)
    for i, part in enumerate(spec['parts']):
        if part.get('type') != 'head':
            continue
        gid = part.get('id') or f'head_{i}'
        axis_mat = part.get('axis_mat')
        L = Vector(part['loc'])
        pitch = part.get('pitch', -8.0)
        yaw = part.get('yaw', 0.0)
        Rp = Euler((math.radians(pitch), 0, math.radians(yaw))).to_matrix()
        upper = part.get('upper', [[-0.05, 0.26, 0.21], [1.18, 0.10, 0.055]])
        y0, y1 = upper[0][0], upper[-1][0]
        path = [tuple(L + Rp @ Vector((0.0, y0 + (y1 - y0) * t, 0.0)))
                for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
        for ob in groups.get(gid, []):
            if ob.type == 'MESH' and ob.name in ('skull', 'jaw'):
                _detail.write_axis_uv(ob, path)
                if axis_mat:
                    _retint_axis(ob, spec, axis_mat)


def _apply_armor(spec, groups):
    """Écailles GÉOMÉTRIQUES chevauchantes ciblées par groupe de parts (I1, sans passer
    par fuse). `detail.armor` = liste d'entrées {target(s), instance{...}, density,
    scale, caudal, curvature, mask{axis,range,to}, scale_grad{axis,range,scale_lo,scale_hi},
    exclude:[sous-chaînes de nom d'objet à sauter, ex. cornes/dents/yeux]}.
    Permet de restreindre les plaques à une région (cou, tête) sans dupliquer la géométrie
    du corps ni toucher aux parts non concernées.
    `layout:'rows'` (chantier B, boucle 19, faute F4 : « semis Poisson isotrope » au
    lieu de rangées anatomiques) : au lieu du semis Poisson ci-dessous, place les
    plaques en RANGÉES régulières le long de l'axe de la part (`_path_for_part`) en
    quinconce, tailles en champ continu par zone (`detail.armor_rows`) — le semis
    Poisson reste le comportement par défaut (fallback) pour toute entrée sans
    `layout`."""
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
        if e.get('layout') == 'rows':
            path_part = e.get('path', targets[0] if targets else None)
            mat = _mat(spec.get('_mats', {}), e.get('mat', 'scales'))
            for ob in objs:
                tag = 'R' if ob.name.endswith('_R') else ('L' if ob.name.endswith('_L') else None)
                path = _path_for_part(spec, path_part, tag)
                if not path:
                    continue
                new_ob = _detail.armor_rows(
                    ob, plate, path, mat,
                    rows=e.get('rows', 20), cols=e.get('cols', 10),
                    v_range=tuple(e.get('v_range', (0.08, 0.92))),
                    quincunx=e.get('quincunx', 0.5),
                    u_range=tuple(e.get('u_range', (0.0, 1.0))),
                    scale_u=e.get('scale_u'), joint_u=e.get('joint_u'),
                    joint_width=e.get('joint_width', 0.06),
                    joint_dip=e.get('joint_dip', 0.55),
                    flank_falloff=e.get('flank_falloff', 0.45),
                    size=tuple(e.get('scale', (0.09, 0.14))),
                    jitter=e.get('jitter', 0.15), rot_jitter=e.get('rot_jitter', 0.12),
                    seed=e.get('seed', 1), name=f'armor_rows_{idx}_{ob.name}')
                if new_ob:
                    groups.setdefault('_armor_rows', []).append(new_ob)
            continue
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
    _apply_weld_groups(spec, groups)
    _apply_axis_uv(spec, groups)
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
