"""OUTIL : AMORCAGE de la cage 3D de la wyverne -> ECRIT specs/wyvern.json.

Meme role que gen_krokmou_cage.py : une fois lance, la spec devient LA SOURCE DE VERITE
et s'edite a la main. ATTENTION : le relancer ECRASE specs/wyvern.json.

Lit le document de design (gen_wyvern_trace.py) : les stations BODY (x, y_haut, y_bas,
demi-largeur) et la chaine LEG. Le decalque 2D et la cage 3D partagent donc le meme profil
de PROFIL ; ce que l'IoU mesure ensuite, c'est la derive propre a la 3D (retrecissement du
subsurf, forme des sections, soudure des pattes) — pas le dessin.

Reutilise `tube_along` de gen_appendages.py (brique b26) pour les pattes.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from gen_appendages import tube_along  # noqa: E402
from gen_wyvern_trace import BODY, LEG, S, X0, Y0  # noqa: E402

# Compensation du retrecissement subsurf. Krokmou utilisait DEUX constantes (1.06 corps /
# 1.2 tubes de patte) ; la vraie loi derriere ces deux nombres est que le Catmull-Clark
# rogne d'autant PLUS que la section est PETITE (le rayon de courbure impose la perte).
# D'ou une compensation qui suit la taille de la section au lieu d'un facteur global —
# c'est ce qui rattrape la tete et le cou, systematiquement trop maigres a 1.06.
GROW_A, GROW_B = 1.045, 3.6  # grow = A + B/taille_px   (mesures : cf. HANDOFF b27)


def _grow(size_px, cap=1.35):
    return min(GROW_A + GROW_B / max(size_px, 12.0), cap)
GROW_LEG = 1.18    # sections carrees 4 pts : le Catmull-Clark ronge bien plus
#     mesure : passer GROW_LEG a 1.30 fait PERDRE 0.0087 d'IoU (patte globalement trop
#     grosse) — le manque venait des BOUTS de tube (les capuchons rentrent sous subsurf),
#     pas de l'epaisseur. Correctif : prolonger la chaine aux 2 extremites (cf. leg_part).
X_LEG = 0.33       # ecartement lateral des pattes (mirror_x fait la paire)


def Y(x_img):
    return (x_img - X0) * S


def Z(y_img):
    return (Y0 - y_img) * S


def half_ring(x_img, yt, yb, w_px):
    """Demi-section (moitie +X) a 5 points, comme Krokmou b24 : haut, epaule haute,
    flanc, epaule basse, bas. Le subsurf + mirror_x en font une section ovale continue."""
    y = Y(x_img)
    zt, zb = Z(yt), Z(yb)
    zm = (zt + zb) / 2.0
    gz = _grow(yb - yt)
    zt, zb = zm + (zt - zm) * gz, zm - (zm - zb) * gz
    w = w_px * S * _grow(2 * w_px)
    return [
        (0.0, y, zt),
        (0.75 * w, y, zm + 0.65 * (zt - zm)),
        (w, y, zm),
        (0.75 * w, y, zm - 0.65 * (zm - zb)),
        (0.0, y, zb),
    ]


def loft(rings, close=False):
    n = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    wrap = range(n) if close else range(n - 1)
    for r in range(len(rings) - 1):
        for j in wrap:
            a, b = r * n + j, r * n + (j + 1) % n
            faces.append([a, b, b + n, a + n])
    faces.append(list(reversed(range(n))))
    last = (len(rings) - 1) * n
    faces.append([last + j for j in range(n)])
    return [[round(c, 4) for c in v] for v in verts], faces


def body_part():
    verts, faces = loft([half_ring(*st) for st in BODY])
    return {"type": "cage", "id": "body_cage", "mirror_x": True, "subsurf": 2,
            "mat": "hide", "verts": verts, "faces": faces}


def _extend(chain, i_from, i_to, k):
    """Prolonge la chaine au-dela du point i_to en extrapolant le segment i_from->i_to.
    Sert a ENFOUIR les capuchons du tube (le subsurf les rentre, ce qui creusait une
    poche de MANQUE a la hanche) : le bout de tube tombe alors dans le bassin / sous le
    sol, la ou personne ne le voit."""
    ax, ay, ar = chain[i_from]
    bx, by, br = chain[i_to]
    return (bx + (bx - ax) * k, by + (by - ay) * k, br)


def leg_part():
    """Patte arriere : tube_along sur la chaine LEG du document de design.
    mirror_x -> la paire, superposee de profil (pose plantee symetrique)."""
    chain = [_extend(LEG, 1, 0, 0.55)] + list(LEG) + [_extend(LEG, -2, -1, 0.5)]
    pts = [[X_LEG, Y(x), Z(y)] for x, y, _ in chain]
    radii = [r * S * GROW_LEG for _, _, r in chain]
    return tube_along("leg", pts, radii, up=(0, 1, 0), subsurf=2, mat="hide",
                      mirror_x=True, miter=True)


def main():
    parts = [body_part(), leg_part()]
    spec = {
        "name": "wyvern",
        "ref": "Wyverne originale (conception maison, 2026-07-22) : predateur bipede sec, "
               "pose a l'affut tete basse. Reference = references/wyvern_ortho_side.png, "
               "notre propre decalque (voir references/wyvern_ref.md). Spec de DEV : "
               "editee a la main apres cet amorcage.",
        "materials": {
            "hide": {"builder": "reptile_scales", "p": {
                "scale": 28, "scale2": 74, "bump": 0.14,
                "base": [0.021, 0.018, 0.016], "tint": [0.03, 0.022, 0.016],
                "rough": 0.56, "rough_edge": 0.4, "sss": 0.05, "micro": 0.16,
                "edge_copper": 0.0, "edge_width": 0.015, "instance_variation": 0.16,
                "patina_amount": 0.0, "spec_level": 0.18, "sheen": 0.02,
                "aniso": 0.06, "specular_tint": [0.86, 0.84, 0.8]}},
        },
        "parts": parts,
        "scene": {
            "camera": {"loc": [7.0, -8.5, 1.6], "target": [0.0, -0.4, 1.5], "lens": 50},
            "silh": {"ref": "references/wyvern_ortho_side.png", "axis": "side",
                     "ortho_scale": 9.0, "target": [0.0, 0.5, 1.4],
                     "exclude_like": ["wing", "horn", "tooth", "ridge", "brow"]},
        },
    }
    out = os.path.join(ROOT, 'specs', 'wyvern.json')
    with open(out, 'w') as f:
        json.dump(spec, f, indent=1)
    print("cage :", {p["id"]: len(p["verts"]) for p in parts})
    print("ecrit", out)


if __name__ == '__main__':
    main()
