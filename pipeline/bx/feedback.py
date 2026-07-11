"""bx.feedback — boucle de retour compressée (convergences C2+C3 des deux docs, + axe 5
de la doctrine SDF : perception ×5-10 par itération, hors-LLM).
C2 : planche-contact 4 vues (face/profil/dessus/¾) assemblée en UN SEUL PNG via numpy
     → un seul coût vision par itération au lieu de quatre.
C3 : silhouettes binaires + score IoU (|A∩B|/|A∪B|, cible > 0.85) contre la référence
     → note de proportion objective, sans interprétation visuelle.
C5 (« sheet4 ») : planche-contact 6 vues (profil/face/dessus ortho + héros persp +
     silhouette + passe ID par pièce couleurs plates) cadrée auto sur la bbox globale,
     plus `inspect_report` (JSON pièce -> bbox/dims/compteurs, sans rendu). La
     correspondance objet -> pièce de spec est GÉNÉRIQUE : elle s'appuie sur l'id de
     part (préfixe exact) puis, à défaut, sur un petit vocabulaire de sous-chaînes par
     TYPE de builder (`PART_TYPE_HINTS` — spine/head/wing/limb/dewlap, pas des noms de
     dragon) déjà utilisées par `bx.organic` pour nommer ses objets ; aucune liste
     d'identifiants dragon en dur. Un override optionnel `spec['scene']['id_colors']`
     (clé = id de pièce ou id_L/id_R, valeur = RGB) peut remplacer la palette par défaut."""
import math
import os
import re

import bpy
import numpy as np
from mathutils import Vector

from . import core


def _render_pixels(path, res, samples, transparent=False):
    sc = bpy.context.scene
    sc.render.film_transparent = transparent
    core.render(path, res=res, samples=samples)
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(res[1], res[0], 4)
    bpy.data.images.remove(img)
    return px[::-1]  # origine bas-gauche de Blender → ordre lecture haut-bas


def _save_png(path, arr):
    """Écrit un tableau (h, w, 4) float 0-1 en PNG via bpy — zéro dépendance externe."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new('sheet', width=w, height=h, alpha=True)
    img.pixels = arr[::-1].ravel().tolist()
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return path


def _place_cam(loc, target, ortho_scale=None, lens=50):
    cam = core.camera(loc, target=target, lens=lens)
    if ortho_scale:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho_scale
    return cam


def default_views(target=(0, 0, 1.5), dist=9.0, ortho_scale=7.0):
    """front / side / top orthographiques + ¾ perspective, autour de `target`."""
    tx, ty, tz = target
    return [
        ('front', (tx, ty - dist, tz), ortho_scale),
        ('side', (tx + dist, ty, tz), ortho_scale),
        ('top', (tx, ty - 0.001, tz + dist), ortho_scale),
        ('three_quarter', (tx + dist * 0.7, ty - dist * 0.7, tz + dist * 0.45), None),
    ]


def contact_sheet(path, views=None, res=(512, 384), samples=12, target=(0, 0, 1.5)):
    """Rend chaque vue puis assemble une grille 2×2 en un seul PNG (np.hstack/vstack).
    Retourne (chemin, liste des vues). Les caméras temporaires sont retirées."""
    views = views or default_views(target=target)
    tiles = []
    tmp = os.path.splitext(path)[0]
    for name, loc, ortho in views:
        cam = _place_cam(loc, target, ortho_scale=ortho)
        tiles.append(_render_pixels(f'{tmp}_{name}.png', res, samples))
        bpy.data.objects.remove(cam)
    while len(tiles) % 2:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
    _save_png(path, np.vstack(rows))
    for name, _, _ in views:
        p = f'{tmp}_{name}.png'
        if os.path.exists(p):
            os.remove(p)
    return path, [v[0] for v in views]


def silhouette(loc=None, target=(0, 0, 1.5), ortho_scale=7.0, res=(512, 384),
               axis='side', dist=9.0):
    """Masque binaire de silhouette : rendu ortho à fond transparent, seuil sur l'alpha.
    Insensible à l'éclairage et aux matériaux (contrairement à un seuil de luminance)."""
    if loc is None:
        tx, ty, tz = target
        loc = {'side': (tx + dist, ty, tz), 'front': (tx, ty - dist, tz),
               'top': (tx, ty - 0.001, tz + dist)}[axis]
    cam = _place_cam(loc, target, ortho_scale=ortho_scale)
    tmp = bpy.app.tempdir or '/tmp'
    px = _render_pixels(os.path.join(tmp, '_sil.png'), res, samples=8, transparent=True)
    bpy.data.objects.remove(cam)
    return px[..., 3] > 0.5


def mask_from_image(path, threshold=0.5, invert=True, size=None):
    """Silhouette binaire depuis une image de référence externe (luminance seuillée).
    invert=True : sujet sombre sur fond clair (cas classique des refs concept-art)."""
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    lum = px[..., :3].mean(axis=-1)
    mask = (lum < threshold) if invert else (lum > threshold)
    bpy.data.images.remove(img)
    return mask


def _bbox_normalize(mask, out_shape=(256, 256)):
    """Recadre sur la bounding box de la silhouette puis rééchantillonne (nearest)
    vers une taille commune : compare les FORMES, pas le cadrage des deux images."""
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return np.zeros(out_shape, dtype=bool)
    crop = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    yi = (np.arange(out_shape[0]) * crop.shape[0] / out_shape[0]).astype(int)
    xi = (np.arange(out_shape[1]) * crop.shape[1] / out_shape[1]).astype(int)
    return crop[yi][:, xi]


def iou(mask_a, mask_b, normalize=True):
    """Intersection over Union des deux silhouettes. 1.0 = formes identiques.
    Objectif de convergence des specs : > 0.85 (doc 2)."""
    if normalize:
        mask_a, mask_b = _bbox_normalize(mask_a), _bbox_normalize(mask_b)
    union = np.logical_or(mask_a, mask_b).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(mask_a, mask_b).sum() / union)


def edge_density(rgb, mask=None):
    """Densité de bords (proxy de « quantité de détail lisible ») via gradient type Sobel.
    Sur les pixels sujet seulement. Sert à comparer bruit-displace vs écailles-géo (I1)
    et rendu vs référence (I2) : plus d'arêtes nettes = détail plus lu."""
    g = rgb[..., :3].mean(-1)
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    gy = np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
    mag = np.sqrt(gx ** 2 + gy ** 2)
    if mask is None:
        mask = g > 0.02
    if mask.sum() == 0:
        return 0.0
    return float((mag[mask] > 0.06).mean())


def color_stats(rgb, mask=None):
    """Couleur linéaire moyenne du sujet + part de pixels cuivrés (r>1.25×g,b), + (CR5,
    audit boucle 17) percentiles de LUMINANCE p5/p50/p95 (Rec.709) sur le sujet SEUL :
    la moyenne cuivrée peut coller à la réf alors que la DISTRIBUTION diverge (fond clair
    + lumière plate vs noir charbon + contrastes durs) — p5 capte les creux/l'ombre
    (doit être quasi-noir sur une réf 'charbon'), p95 les spéculaires/highlights de rim,
    p50 le niveau global. C'est le juge du contraste que cuivre/couleur moyenne ne voient
    pas. Comparable aux ancres mesurées sur la réf (research/inversions.md)."""
    if mask is None:
        mask = rgb[..., :3].mean(-1) > 0.02
    subj = rgb[..., :3][mask]
    if len(subj) == 0:
        return {'mean': [0, 0, 0], 'copper_fraction': 0.0,
                'luminance_p5': 0.0, 'luminance_p50': 0.0, 'luminance_p95': 0.0}
    copper = subj[(subj[:, 0] > subj[:, 1] * 1.25) & (subj[:, 0] > subj[:, 2] * 1.25)]
    lum = subj @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)  # Rec.709 luma
    p5, p50, p95 = np.percentile(lum, [5, 50, 95])
    return {'mean': [round(float(x), 3) for x in subj.mean(0)],
            'copper_fraction': round(len(copper) / len(subj), 3),
            'copper_mean': [round(float(x), 3) for x in copper.mean(0)] if len(copper) else None,
            'luminance_p5': round(float(p5), 4),
            'luminance_p50': round(float(p50), 4),
            'luminance_p95': round(float(p95), 4)}


def _resize_h(arr, target_h):
    h, w = arr.shape[:2]
    tw = int(w * target_h / h)
    yi = (np.arange(target_h) * h / target_h).astype(int)
    xi = (np.arange(tw) * w / tw).astype(int)
    return arr[yi][:, xi]


def compare_sheet(out_path, ref_path, cam_loc, target, res=(640, 640), samples=24,
                  ortho_scale=None, lens=70):
    """Inversion I2 : rend une région EN MACRO, la colle CÔTE À CÔTE avec la frame de réf,
    et renvoie les deltas numériques (couleur, densité de bords). Aucun rendu orphelin.
    La créature/scène doit déjà être construite ET éclairée (ou clay) par l'appelant."""
    cam = _place_cam(cam_loc, target, ortho_scale=ortho_scale, lens=lens)
    ren = _render_pixels(out_path + '.tmp.png', res, samples)[..., :3]
    bpy.data.objects.remove(cam)
    ref = bpy.data.images.load(ref_path)
    rw, rh = ref.size
    refpx = np.array(ref.pixels[:], dtype=np.float32).reshape(rh, rw, 4)[::-1, :, :3]
    bpy.data.images.remove(ref)
    h = min(ren.shape[0], refpx.shape[0])
    pair = np.hstack([_resize_h(refpx, h), np.ones((h, 6, 3), np.float32) * 0.5,
                      _resize_h(ren, h)])
    _save_png(out_path, np.dstack([pair, np.ones(pair.shape[:2], np.float32)]))
    if os.path.exists(out_path + '.tmp.png'):
        os.remove(out_path + '.tmp.png')
    # Métriques sur images NORMALISÉES à une hauteur commune : edge_density est une
    # fraction de pixels-bord, donc dépendante de la résolution d'analyse — sans ça,
    # réf (native ~1500px) et rendu (560/900px) ne sont pas comparables, et le chiffre
    # bouge entre --fast et HQ sans que l'image change.
    ana_h = 512
    ref_a, ren_a = _resize_h(refpx, ana_h), _resize_h(ren, ana_h)
    return {'sheet': out_path,
            'ref': {'color': color_stats(ref_a), 'edge_density': round(edge_density(ref_a), 4)},
            'render': {'color': color_stats(ren_a), 'edge_density': round(edge_density(ren_a), 4)}}


def proportions(mask):
    """Mesures numériques compactes d'une silhouette : ratio L/H et centroïde normalisé.
    Sert à calculer des deltas d'échelle par axe pour corriger la spec (doc 2)."""
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    return {'aspect': round(w / h, 3),
            'centroid': (round((xs.mean() - xs.min()) / w, 3),
                         round((ys.mean() - ys.min()) / h, 3))}


# ---------------------------------------------------------------------------
# Axe 5 doctrine : registre pièce<->objets (générique par TYPE de builder),
# bbox scène, planche 6 vues « sheet4 », introspection sans rendu « inspect ».
# ---------------------------------------------------------------------------

PART_TYPE_HINTS = {
    # sous-chaînes de noms d'objets écrites par bx.organic pour CE type de builder
    # (vocabulaire générique du builder, pas des noms de dragon) — utilisées en repli
    # quand le nom de l'objet ne commence pas directement par l'id de la part.
    'spine': ['dorsal'],
    'head': ['skull', 'jaw', 'tooth', 'gum', 'eye', 'lid', 'nostril', 'nose', 'ridge', 'face', 'horn'],
    'wing': ['arm', 'hand', 'membrane', 'batten', 'finger', 'wclaw', 'vein'],
    'limb': ['footpad', 'toe', 'claw', 'leg'],
    'dewlap': ['dewlap'],
}

_SIDE_RE = re.compile(r'(?:^|_)([LR])(?:\d|_|$)')
_DUP_SUFFIX_RE = re.compile(r'\.\d{3}$')


def _side_of(name):
    """Tag bilatéral MAJUSCULE (arm_L, hindleg_R, finger_L0...) — distinct des tags
    minuscules l/r utilisés en interne par `head` (eye_l, horn_r...) qui ne doivent
    PAS être scindés en groupes séparés."""
    m = _SIDE_RE.search(name)
    return m.group(1) if m else None


def _hint_matches(hint, name):
    """Sous-chaîne `hint` comme TOKEN entier (borné par `_`/début/fin/chiffre), pas une
    simple sous-chaîne brute : évite par ex. que le hint wing 'arm' matche à l'intérieur
    de 'armor_plate_0_0' (bibliothèque d'écailles, générique, hors anatomie)."""
    return re.search(r'(?:^|_)' + re.escape(hint) + r'(?:$|_|[0-9])', name) is not None


def classify_object(name, parts, overrides=None):
    """Associe un nom d'objet Blender à une pièce de spec (clé de groupe), sans aucune
    liste dragon en dur : 1) préfixe explicite `id_colors`/overrides (spec) ; 2) l'objet
    porte l'id de part en préfixe (`hindleg_L`.startswith('hindleg_')) ; 3) à défaut, un
    TOKEN parmi `PART_TYPE_HINTS[type]` sur l'ensemble des parts (résout par ex.
    `wclaw_L0` en faveur de wing, jamais confondu avec `claw_L0`/limb grâce aux
    frontières de token, quel que soit l'ordre des parts dans la spec).
    Insensible au suffixe anti-collision Blender (`body.001` -> `body`).
    `parts` : liste de (id, type). Retourne `id` ou `id_L`/`id_R` (wing/limb), ou None."""
    name = _DUP_SUFFIX_RE.sub('', name)
    if overrides:
        for prefix in overrides:
            if name == prefix or name.startswith(prefix + '_'):
                return prefix
    best = None
    for pid, ptype in parts:
        if name == pid or name.startswith(pid + '_'):
            best = (len(pid) + 1000, pid, ptype)
            break
    if best is None:
        for pid, ptype in parts:
            for hint in PART_TYPE_HINTS.get(ptype, ()):
                if _hint_matches(hint, name):
                    cand = (len(hint), pid, ptype)
                    if best is None or cand[0] > best[0]:
                        best = cand
    if best is None:
        return None
    _, pid, ptype = best
    side = _side_of(name)
    if side and ptype in ('wing', 'limb'):
        return f'{pid}_{side}'
    return pid


def spec_parts(spec):
    """(id, type) pour chaque part de la spec, dans l'ordre déclaré."""
    return [(p.get('id') or f"{p['type']}_{i}", p['type'])
            for i, p in enumerate(spec.get('parts', []))]


def part_bbox(spec, part_key):
    """Bbox MONDE d'un groupe de pièces, clé par préfixe : 'hindleg' couvre aussi
    'hindleg_L'/'hindleg_R'. Retourne (center, radius) — radius = demi-diagonale,
    prêt pour un cadrage caméra. None si aucune pièce ne matche (id inconnu)."""
    deps = bpy.context.evaluated_depsgraph_get()
    registry = part_registry(spec_parts(spec))
    mins, maxs = [], []
    for key, objs in registry.items():
        if key != part_key and not key.startswith(part_key + '_'):
            continue
        for ob in objs:
            coords, _ = _obj_world_coords(ob, deps)
            if not coords:
                continue
            xs, ys, zs = zip(*coords)
            mins.append((min(xs), min(ys), min(zs)))
            maxs.append((max(xs), max(ys), max(zs)))
    if not mins:
        return None
    bmin = [min(v[i] for v in mins) for i in range(3)]
    bmax = [max(v[i] for v in maxs) for i in range(3)]
    center = tuple((bmin[i] + bmax[i]) / 2 for i in range(3))
    radius = sum((bmax[i] - bmin[i]) ** 2 for i in range(3)) ** 0.5 / 2
    return center, radius


def bbox_by_match(match):
    """Bbox MONDE de tous les objets MESH/CURVE visibles au rendu dont le nom
    contient au moins une des sous-chaînes de `match` (str ou liste) — cadrage
    caméra GÉNÉRIQUE sur un SOUS-ENSEMBLE de pièce (boucle 19 chantier C : shots de
    VÉRIFICATION FEATURE `eye`/`teeth`, ex. globe + paupières, ou dents + gencives +
    lèvres) quand `frame_part` (groupe de spec ENTIER, ex. toute la tête) serait trop
    large pour juger une feature précise à l'échelle où elle doit lire. Complète
    `part_bbox` (qui ne connaît que les groupes déclarés dans `spec['parts']`) sans
    dépendre du registre de classification par part -- une simple sous-chaîne de nom
    d'objet, comme `detail.displace_targets[].match`. Retourne (center, radius) ou
    None si aucun objet ne matche."""
    names = [match] if isinstance(match, str) else list(match)
    deps = bpy.context.evaluated_depsgraph_get()
    mins, maxs = [], []
    for ob in bpy.context.scene.objects:
        if ob.type not in ('MESH', 'CURVE') or ob.hide_render:
            continue
        if not any(nm in ob.name for nm in names):
            continue
        coords, _ = _obj_world_coords(ob, deps)
        if not coords:
            continue
        xs, ys, zs = zip(*coords)
        mins.append((min(xs), min(ys), min(zs)))
        maxs.append((max(xs), max(ys), max(zs)))
    if not mins:
        return None
    bmin = [min(v[i] for v in mins) for i in range(3)]
    bmax = [max(v[i] for v in maxs) for i in range(3)]
    center = tuple((bmin[i] + bmax[i]) / 2 for i in range(3))
    radius = sum((bmax[i] - bmin[i]) ** 2 for i in range(3)) ** 0.5 / 2
    return center, radius


def part_registry(parts, overrides=None):
    """Scène déjà construite -> {groupe: [objets Blender]}. Objets non classés -> 'other'.
    Exclut `hide_render` (bibliothèque d'archétypes d'écailles `armor_plate_*`/
    `keeled_scale` : sources d'instances Geometry Nodes cachées au rendu par
    `bx.detail`, jamais visibles telles quelles — pas des pièces anatomiques)."""
    registry = {}
    for ob in bpy.context.scene.objects:
        if ob.type not in ('MESH', 'CURVE') or ob.hide_render:
            continue
        key = classify_object(ob.name, parts, overrides) or 'other'
        registry.setdefault(key, []).append(ob)
    return registry


def _obj_world_coords(ob, deps):
    """Sommets MONDE de la géométrie évaluée (bake bevel/modifiers, comme
    `core.realize_to_mesh`) ; repli sur `bound_box` (contrôle seul, sans bevel) si
    l'évaluation échoue. Retourne (liste de Vector, nb sommets)."""
    ev = ob.evaluated_get(deps)
    me = None
    try:
        me = ev.to_mesh()
    except RuntimeError:
        me = None
    if me and me.vertices:
        coords = [ob.matrix_world @ v.co for v in me.vertices]
        n = len(me.vertices)
        ev.to_mesh_clear()
        return coords, n
    if me:
        ev.to_mesh_clear()
    coords = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return coords, (len(ob.data.vertices) if ob.type == 'MESH' else 0)


def scene_bbox(objs=None):
    """Bbox monde (min, max) sur `objs` (défaut : tous les MESH/CURVE visibles au rendu
    de la scène — exclut les sources d'instances GN cachées, cf. `part_registry`)."""
    deps = bpy.context.evaluated_depsgraph_get()
    objs = objs if objs is not None else [
        o for o in bpy.context.scene.objects if o.type in ('MESH', 'CURVE') and not o.hide_render]
    mins, maxs = [], []
    for ob in objs:
        coords, _ = _obj_world_coords(ob, deps)
        if not coords:
            continue
        xs, ys, zs = zip(*coords)
        mins.append((min(xs), min(ys), min(zs)))
        maxs.append((max(xs), max(ys), max(zs)))
    if not mins:
        return (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
    bmin = tuple(min(v[i] for v in mins) for i in range(3))
    bmax = tuple(max(v[i] for v in maxs) for i in range(3))
    return bmin, bmax


def auto_frame(bmin, bmax, margin=0.08):
    """Centre + échelle ortho + distance caméra couvrant la bbox avec une marge
    5-10% (uniforme sur les 3 axes : simple et robuste, quitte à laisser un peu plus
    d'air sur l'axe le plus court)."""
    center = tuple((bmin[i] + bmax[i]) / 2 for i in range(3))
    half = [max((bmax[i] - bmin[i]) / 2, 0.25) for i in range(3)]
    ext = max(half)
    ortho_scale = ext * 2 * (1 + margin)
    dist = ext * 3 + 4
    return center, ortho_scale, dist


_ID_PALETTE = [
    (0.90, 0.15, 0.15), (0.15, 0.55, 0.95), (0.20, 0.85, 0.35), (0.95, 0.75, 0.10),
    (0.65, 0.25, 0.85), (0.95, 0.45, 0.15), (0.15, 0.85, 0.85), (0.85, 0.15, 0.60),
    (0.55, 0.55, 0.55), (0.35, 0.75, 0.15), (0.30, 0.30, 0.90), (0.90, 0.60, 0.75),
]


def _group_color(key, idx, overrides=None):
    if overrides and key in overrides:
        c = overrides[key]
        return (c[0], c[1], c[2])
    return _ID_PALETTE[idx % len(_ID_PALETTE)]


def id_pass(registry, overrides=None):
    """Remplace TOUS les matériaux par une émission plate distincte par groupe de pièce
    (pas d'ombres : Emission pur, insensible à l'éclairage/normales) et retire les
    lumières. Retourne {groupe: (r,g,b)}. Détruit les matériaux d'origine — à appeler
    en DERNIER dans une passe de rendu jetable (sheet4)."""
    for ob in list(bpy.context.scene.objects):
        if ob.type == 'LIGHT':
            bpy.data.objects.remove(ob)
    colors = {}
    for idx, key in enumerate(sorted(registry)):
        color = _group_color(key, idx, overrides)
        colors[key] = color
        mat = bpy.data.materials.new(f'id_{key}')
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*color, 1)
        em.inputs['Strength'].default_value = 1.0
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
        for ob in registry[key]:
            if ob.type in ('MESH', 'CURVE'):
                ob.data.materials.clear()
                ob.data.materials.append(mat)
    core.world(color=(0.08, 0.08, 0.09), strength=1.0)
    return colors


def sheet4(path, spec, fast=False, margin=0.08):
    """Planche-contact 6 vues (axe 5 doctrine) en UN PNG (grille 2 colonnes x 3 rangées) :
    a. ortho profil (x)   b. ortho face (y)
    c. ortho dessus (z)   d. héros persp (scene.hero, ou 3/4 auto)
    e. silhouette (noir/blanc, vue profil)   f. ID par pièce (couleurs plates, vue héros)
    Cadrage auto sur la bbox globale (marge ~`margin`). La scène doit déjà être
    construite ET son mode de rendu choisi (clay/matériaux) par l'appelant.
    Le total en largeur reste <= ~1600px (contrainte planche) : tuile 640px en --fast,
    800px sinon (2 colonnes x 800 = 1600, plafond dur — pas 1152 comme les autres
    commandes HQ, qui elles ne composent qu'UNE vue)."""
    tile_w = 640 if fast else 800
    tile_h = round(tile_w * 3 / 4)
    res = (tile_w, tile_h)
    samples = 10 if fast else 22
    bmin, bmax = scene_bbox()
    center, scale, dist = auto_frame(bmin, bmax, margin=margin)
    cx, cy, cz = center
    hero = spec.get('scene', {}).get('hero', {})
    hero_cam = tuple(hero.get('cam', (cx + dist * 0.7, cy - dist * 0.7, cz + dist * 0.45)))
    hero_target = tuple(hero.get('target', center))
    hero_lens = hero.get('lens', 45)
    parts = spec_parts(spec)
    overrides = spec.get('scene', {}).get('id_colors', {})
    registry = part_registry(parts, overrides)

    tmp = os.path.splitext(path)[0]
    cam = _place_cam((cx + dist, cy, cz), center, ortho_scale=scale)
    profile = _render_pixels(f'{tmp}_a.png', res, samples)
    bpy.data.objects.remove(cam)

    cam = _place_cam((cx, cy - dist, cz), center, ortho_scale=scale)
    face = _render_pixels(f'{tmp}_b.png', res, samples)
    bpy.data.objects.remove(cam)

    cam = _place_cam((cx, cy - 0.001, cz + dist), center, ortho_scale=scale)
    top = _render_pixels(f'{tmp}_c.png', res, samples)
    bpy.data.objects.remove(cam)

    cam = _place_cam(hero_cam, hero_target, lens=hero_lens)
    hero_tile = _render_pixels(f'{tmp}_d.png', res, samples)
    bpy.data.objects.remove(cam)

    mask = silhouette(loc=(cx + dist, cy, cz), target=center, ortho_scale=scale,
                      res=res, axis='side')
    sil = np.ones((res[1], res[0], 4), dtype=np.float32)
    sil[..., :3][mask] = 0.0

    colors = id_pass(registry, overrides)
    cam = _place_cam(hero_cam, hero_target, lens=hero_lens)
    idpass = _render_pixels(f'{tmp}_f.png', res, samples)
    bpy.data.objects.remove(cam)

    tiles = [profile, face, top, hero_tile, sil, idpass]
    rows = [np.hstack(tiles[i:i + 2]) for i in range(0, 6, 2)]
    _save_png(path, np.vstack(rows))
    for suf in ('a', 'b', 'c', 'd', 'f'):
        p = f'{tmp}_{suf}.png'
        if os.path.exists(p):
            os.remove(p)
    legend = ['a=profil(x)', 'b=face(y)', 'c=dessus(z)', 'd=hero(persp)',
              'e=silhouette(profil)', 'f=id_pass(hero)']
    return path, legend, {k: [round(x, 3) for x in v] for k, v in colors.items()}


def inspect_report(spec):
    """Scène déjà construite -> JSON compact : par pièce (bbox/dims/objets/verts_est)
    + compteurs globaux. AUCUN rendu (C1-like, mais registre de parts au lieu de BVH)."""
    deps = bpy.context.evaluated_depsgraph_get()
    parts = spec_parts(spec)
    registry = part_registry(parts)
    out = {}
    tot_objs = tot_verts = 0
    for key in sorted(registry):
        objs = registry[key]
        mins, maxs, verts = [], [], 0
        for ob in objs:
            coords, n = _obj_world_coords(ob, deps)
            if not coords:
                continue
            xs, ys, zs = zip(*coords)
            mins.append((min(xs), min(ys), min(zs)))
            maxs.append((max(xs), max(ys), max(zs)))
            verts += n
        if not mins:
            continue
        bmin = tuple(round(min(v[i] for v in mins), 4) for i in range(3))
        bmax = tuple(round(max(v[i] for v in maxs), 4) for i in range(3))
        dims = tuple(round(bmax[i] - bmin[i], 4) for i in range(3))
        out[key] = {'objects': len(objs), 'bbox_min': list(bmin), 'bbox_max': list(bmax),
                    'dims': list(dims), 'verts_est': verts}
        tot_objs += len(objs)
        tot_verts += verts
    return {'parts': out, 'totals': {'objects': tot_objs, 'verts_est': tot_verts}}
