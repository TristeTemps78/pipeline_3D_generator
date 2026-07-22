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
GROW_A, GROW_B = 1.012, 2.0  # grow = A + B/taille_px   (mesures : cf. HANDOFF b27)
#   A est tombe de 1.040 a 1.012 avec le profil « squircle » : un sommet PLAT resiste
#   bien mieux au Catmull-Clark que l'apex d'une ellipse, donc il faut nettement
#   moins compenser (mesure : 2.3 % d'EXCES en bande le long du dos).
#   B est passe de 3.6 a 2.0 en v2 : le cou et la queue sont devenus BEAUCOUP plus fins
#   (proportions realistes), donc la loi en 1/taille sur-corrigeait -> 7.4 % d'EXCES.


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


# Profil de demi-section, en fractions de (demi-largeur, demi-hauteur). v1 utilisait
# 5 points sur une ELLIPSE : un tube en ballon du museau a la queue, une des trois causes
# du « trop cartoon ». v2 : 7 points en « squircle » — dessus et dessous APLATIS, flancs
# PLATS, transitions marquees. Un animal reel n'est pas un cylindre : il a des plans
# (le flanc, le dos) separes par des aretes ou courent les reperes osseux.
SECTION = [
    (0.00,  1.00),   # ligne dorsale
    (0.50,  0.95),   # dos PLAT jusqu'a mi-largeur
    (0.92,  0.60),   # arete dorso-laterale : c'est elle qui attrape la lumiere
    (1.00,  0.02),   # flanc, point le plus large
    (0.90, -0.58),   # arete ventro-laterale
    (0.46, -0.92),   # ventre plat
    (0.00, -1.00),   # ligne ventrale
]


def half_ring(x_img, yt, yb, w_px):
    """Demi-section (moitie +X). Le subsurf + mirror_x en font une peau continue."""
    y = Y(x_img)
    zt, zb = Z(yt), Z(yb)
    zm = (zt + zb) / 2.0
    hz = (zt - zb) / 2.0 * _grow(yb - yt)
    w = w_px * S * _grow(2 * w_px)
    return [(fx * w, y, zm + fz * hz) for fx, fz in SECTION]


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
    # SOL : sans lui la bete flotte dans le vide, perd son echelle et son ombre
    # portee — le rendu lit « figurine ». Un sol sombre et mat suffit : c'est le
    # CONTACT (pieds + ombre) qui fait le poids, pas le decor.
    ground = {"type": "ground", "id": "ground", "size": 70, "mat": "rock"}
    parts = [body_part(), leg_part(), ground]
    spec = {
        "name": "wyvern",
        "ref": "Wyverne originale (conception maison, 2026-07-22) : predateur bipede sec, "
               "pose a l'affut tete basse. Reference = references/wyvern_ortho_side.png, "
               "notre propre decalque (voir references/wyvern_ref.md). Spec de DEV : "
               "editee a la main apres cet amorcage.",
        "materials": {
            # PIEGE PAYE EN 3 ROUNDS : `scale` est en CELLULES PAR UNITE MONDE
            # (docstring de reptile_scales), pas un nombre d'ecailles. A 28 puis 62 les
            # plaques faisaient 3.5 puis 1.6 cm : invisibles au rendu -> peau
            # « plastique chocolat ». A 14 (plaques de 7 cm sur une bete de 7.5 m) elles
            # se lisent. Et le bump doit etre FRANC : mesure, 0.55 ne donne RIEN,
            # il faut ~1.35. C'est le relief qui fait la peau, pas la couleur.
            "hide": {"builder": "reptile_scales", "p": {
                "scale": 14, "scale2": 40, "bump": 1.35,
                "base": [0.011, 0.0095, 0.009], "tint": [0.038, 0.024, 0.016],
                "rough": 0.66, "rough_edge": 0.28, "sss": 0.04, "micro": 0.45,
                "edge_copper": 0.12, "edge_width": 0.012, "instance_variation": 0.22,
                "patina_amount": 0.0, "spec_level": 0.14, "sheen": 0.03,
                "aniso": 0.05, "specular_tint": [0.86, 0.84, 0.8]}},
            "rock": {"builder": "rock", "p": {
                "color": [0.0042, 0.0038, 0.0036], "scale": 2.2, "bump": 1.8,
                "burnt": [0.006, 0.005, 0.005], "ember": [0.05, 0.02, 0.008]}},
        },
        "parts": parts,
        "scene": {
            # CONTRE-PLONGEE : l'objectif est SOUS la ligne des yeux (z 0.85 pour une
            # tete a z 1.4) — c'est le cadrage qui fait dominer le sujet. Une prise de
            # vue a hauteur d'epaule d'homme rendrait la meme bete inoffensive.
            # 3/4 AVANT, tres bas, serre sur l'avant du corps. Le frontal pur faisait lire
            # les ailes comme deux parapluies (eventail vu de face) ; le lateral pur cache
            # la queue derriere l'aile. Le 3/4 avant garde le regard, montre l'envergure
            # en raccourci et laisse la croupe filer dans le flou.
            "camera": {"loc": [4.6, -8.6, 0.55], "target": [-0.35, -1.90, 1.22],
                       "lens": 55, "fstop": 2.8},
            "silh": {"ref": "references/wyvern_ortho_side.png", "axis": "side",
                     "ortho_scale": 9.0, "target": [0.0, 0.5, 1.4],
                     "exclude_like": ["wing", "horn", "tooth", "ridge", "brow",
                                      "mouth_", "claw", "toe"]},
            # Low-key : le fond reste presque noir, la bete est DECOUPEE par deux
            # contre-jours. Sur une peau quasi noire, c'est le seul schema qui donne
            # une lecture — un eclairage studio a plat la transforme en tache grise.
            "world": {"color": [0.007, 0.008, 0.012], "color_top": [0.021, 0.024, 0.034],
                      "strength": 0.40, "visible_strength": 0.95},
            "sun": {"direction": [-0.30, 0.55, -0.80], "energy": 1.0,
                    "color": [0.72, 0.80, 1.0]},
            "area_lights": [
                {"loc": [4.2, -6.6, 2.6], "target": [-0.6, -1.6, 1.5], "energy": 340,
                 "size": 2.0, "color": [1.0, 0.84, 0.62]},          # key chaude, DISCRETE
                {"loc": [-4.0, 5.8, 3.2], "target": [0.0, 0.2, 1.9], "energy": 3400,
                 "size": 1.4, "color": [0.52, 0.68, 1.0]},          # rim froid DUR
                {"loc": [5.2, 4.2, 2.4], "target": [1.4, 0.8, 1.9], "energy": 2600,
                 "size": 1.8, "color": [0.95, 0.58, 0.34]},         # rim chaud, membranes
                {"loc": [-4.5, -6.0, 2.0], "target": [0.0, -1.0, 1.4], "energy": 110,
                 "size": 6.0, "color": [0.60, 0.72, 1.0]},          # fill : pas de noir mort
            ],
            "shots": [
                {"id": "hero"},
                {"id": "head", "frame_match": "eye_", "margin": 2.6,
                 "dir": [0.80, -1.0, 0.06], "lens": 80, "fstop": 2.2},
                {"id": "wide", "frame_match": "body_cage", "margin": 1.02,
                 "dir": [0.55, -1.0, 0.10], "lens": 45},
            ],
            "render": {"device": "AUTO", "samples": 48, "denoise": True,
                       "adaptive_threshold": 0.02, "max_bounces": 6,
                       "diffuse_bounces": 3, "glossy_bounces": 3, "volume_bounces": 0,
                       "clamp_indirect": 4.0, "fast_sss": True},
        },
    }
    out = os.path.join(ROOT, 'specs', 'wyvern.json')
    with open(out, 'w') as f:
        json.dump(spec, f, indent=1)
    print("cage :", {p["id"]: len(p.get("verts", ())) for p in parts})
    print("ecrit", out)


if __name__ == '__main__':
    main()
