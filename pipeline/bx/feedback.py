"""bx.feedback — boucle de retour compressée (convergences C2+C3 des deux docs).
C2 : planche-contact 4 vues (face/profil/dessus/¾) assemblée en UN SEUL PNG via numpy
     → un seul coût vision par itération au lieu de quatre.
C3 : silhouettes binaires + score IoU (|A∩B|/|A∪B|, cible > 0.85) contre la référence
     → note de proportion objective, sans interprétation visuelle."""
import math
import os

import bpy
import numpy as np

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
    """Couleur linéaire moyenne du sujet + part de pixels cuivrés (r>1.25×g,b).
    Comparable aux ancres mesurées sur la réf (research/inversions.md)."""
    if mask is None:
        mask = rgb[..., :3].mean(-1) > 0.02
    subj = rgb[..., :3][mask]
    if len(subj) == 0:
        return {'mean': [0, 0, 0], 'copper_fraction': 0.0}
    copper = subj[(subj[:, 0] > subj[:, 1] * 1.25) & (subj[:, 0] > subj[:, 2] * 1.25)]
    return {'mean': [round(float(x), 3) for x in subj.mean(0)],
            'copper_fraction': round(len(copper) / len(subj), 3),
            'copper_mean': [round(float(x), 3) for x in copper.mean(0)] if len(copper) else None}


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
    return {'sheet': out_path,
            'ref': {'color': color_stats(refpx), 'edge_density': round(edge_density(refpx), 4)},
            'render': {'color': color_stats(ren), 'edge_density': round(edge_density(ren), 4)}}


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
