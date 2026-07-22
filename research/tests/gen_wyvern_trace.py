"""OUTIL : dessine LA REFERENCE de la wyverne — decalque ortho de profil, CORPS SEUL.

Difference capitale avec Krokmou : la reference n'est pas le decalque d'une image (c),
c'est NOTRE document de design, donc committable (le score de silhouette marche desormais
aussi en conteneur/CI, ce qui n'a jamais ete le cas pour Krokmou).

CE FICHIER EST LE DOCUMENT DE DESIGN. Il porte le tableau `BODY` (stations
x_img, y_haut, y_bas, demi-largeur) que gen_wyvern_cage.py importe tel quel pour lofter la
cage 3D. Le score IoU ne valide donc PAS le dessin (il vient d'ici) : il mesure la DERIVE
3D->2D — retrecissement du subsurf, forme des sections, soudure des pattes qui gonfle le
ventre. C'est exactement ce que la metrique a rattrape en b26 (-0.011 a la soudure).

Convention image : x vers la DROITE = de la tete vers la queue (la creature regarde a
GAUCHE), y vers le BAS, sol a y=SOL. La 4e colonne (demi-largeur) ne sert PAS au dessin
2D — c'est la dimension que le decalque ne peut pas montrer, donc un vrai degre de liberte
laisse a la 3D.

Exclus du decalque (appendices ajoutes ensuite, masques par scene.silh.exclude_like) :
ailes, cornes, dents, epines dorsales.

Sorties :
  references/wyvern_ortho_side.png         corps + pattes = LA reference scoree
  references/wyvern_ortho_side_nolegs.png  tronc seul (aide de lecture, non scoree)

Intention de design (registre « predateur sec et nerveux », pose a l'affut) :
- crane en COIN bas et long (182x82 px, ratio 2.2:1) — l'inverse du galet de Krokmou ;
- tete 100 px SOUS la ligne du dos, cou en arc compact et epais (78 px) dont la crete
  depasse a peine le garrot : posture de frappe, pas de cygne decoratif ;
- quille sternale profonde (poitrail 140 px) puis taille pincee (98 px) : le contraste
  cage thoracique / flanc creux est CE qui fait lire « animal reel et affame » ;
- pattes DIGITIGRADES en Z (genou avant, talon haut en arriere, metatarse long), plantees
  symetriquement -> de profil les 2 pattes se superposent EXACTEMENT, donc le rendu ortho
  vaut le decalque (pas la penalite d'IoU qu'imposait la pose de marche de Krokmou) ;
- silhouette d'ensemble longue et basse (854 x 320 px, 2.7:1) : ca rampe vers toi.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
from gvl.laws import catmull_rom  # noqa: E402  (fonction pure, sans bpy)

W, H = 960, 600
SOL = 545          # ligne de sol
S = 0.009          # px -> unites Blender (bete de ~7.7 u de long)
X0, Y0 = 420, SOL  # x_img 420 -> Y=0 (centre la bete) ; sol -> Z=0

# --- LE CORPS : une seule chaine museau -> bout de la queue -------------------------
# (x_img, y_haut, y_bas, demi-largeur px)   x STRICTEMENT croissant (loft valide)
# La demi-largeur ne change PAS le decalque 2D : museau etroit -> crane large est un
# coin vu de dessus, la lecture « predateur » que la vue de profil ne peut pas porter.
# v2 (feedback utilisateur : « il est trop cartoon ») — LES PROPORTIONS D'ABORD.
# v1 : tete 22 % de la longueur, queue 26 %, pattes courtes. C'est la grammaire du
# dessin anime (grosse tete = mignon). Un predateur reel a une PETITE tete et une
# LONGUE queue de contrepoids. v2 : tete 14 %, cou 19 %, tronc 32 %, queue 35 %, et
# la queue est tenue a l'HORIZONTALE (theropode) au lieu de plonger au sol.
BODY = [
    (60,  410, 430, 7),    # bout du museau
    (76,  404, 434, 10),   # narines
    (94,  405, 438, 13),   # CREUX du chanfrein
    (112, 398, 442, 16),
    (130, 388, 446, 20),   # orbite
    (148, 380, 448, 24),   # arcade + machoire : 68 px, crane 1.64:1 (etait 1.28 = bulldog)
    (164, 376, 442, 26),   # sommet du crane
    (178, 382, 428, 22),   # occiput
    (192, 390, 414, 16),   # ENCOCHE : le cou fait 24 px, la tete 68 -> elle se detache
    (212, 372, 400, 17),
    (234, 348, 380, 19),
    (258, 318, 356, 21),   # cou LONG et sec
    (282, 288, 330, 23),
    (306, 262, 306, 26),
    (330, 244, 288, 29),   # crete du cou
    (352, 240, 284, 33),
    (376, 244, 296, 39),   # base du cou
    (402, 250, 322, 45),   # garrot / omoplates
    (430, 252, 352, 51),
    (462, 254, 366, 55),   # QUILLE sternale (112 px)
    (494, 256, 364, 55),   # cage thoracique
    (526, 260, 352, 49),
    (556, 264, 338, 41),   # taille PINCEE (74 px)
    (588, 256, 324, 45),   # bassin
    (618, 248, 314, 49),   # hanche / sacrum
    (650, 258, 300, 32),   # base de queue epaisse
    (684, 268, 302, 27),
    (718, 282, 312, 22),
    (752, 300, 328, 18),
    (786, 322, 348, 14),
    (818, 346, 370, 11),
    (850, 372, 394, 8),
    (876, 398, 418, 5),
    (892, 420, 436, 3),    # pointe de la queue, tenue HAUT
]

# --- LA PATTE ARRIERE : chaine de disques (x, y, rayon), les 2 pattes superposees ----
# Z digitigrade : hanche -> genou EN AVANT -> talon EN ARRIERE et HAUT -> metatarse
# long -> orteils au sol vers l'avant. v2 : plus LONGUE et plus FINE — une patte courte
# et epaisse sous un corps massif, c'est une peluche ; un bipede rapide est haut sur
# pattes et ses masses musculaires s'arretent au genou.
LEG = [
    (605, 296, 42),   # hanche (enfouie dans le bassin)
    (556, 348, 40),   # femur (le muscle s'arrete la)
    (512, 392, 27),   # GENOU (pointe vers l'avant)
    (548, 444, 22),   # tibia — fin, tendineux
    (585, 486, 18),   # TALON (haut, en arriere — digitigrade)
    (572, 516, 16),   # metatarse long
    (556, 532, 13),   # cou-de-pied
    (532, 536, 12),   # orteils
    (502, 538, 10),
    (474, 540, 7),
    (454, 541, 5),    # pointe des griffes
]


def Y(x_img):
    return round((x_img - X0) * S, 3)


def Z(y_img):
    return round((Y0 - y_img) * S, 3)


def body_outline(samples=5):
    """Polygone ferme du tronc : chaine haute (museau->queue) + chaine basse (retour).
    x monotone sur chaque chaine -> aucune auto-intersection possible."""
    top = catmull_rom([(x, yt) for x, yt, _, _ in BODY], samples=samples)
    bot = catmull_rom([(x, yb) for x, _, yb, _ in BODY], samples=samples)
    return list(top) + list(reversed(bot))


def _draw_chain(draw, chain):
    """Chaine de capsules : un disque par station + un quad entre stations voisines."""
    for x, y, r in chain:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=0)
    for (x0, y0, r0), (x1, y1, r1) in zip(chain, chain[1:]):
        dx, dy = x1 - x0, y1 - y0
        n = (dx * dx + dy * dy) ** 0.5 or 1.0
        px, py = -dy / n, dx / n
        draw.polygon([(x0 + px * r0, y0 + py * r0), (x1 + px * r1, y1 + py * r1),
                      (x1 - px * r1, y1 - py * r1), (x0 - px * r0, y0 - py * r0)], fill=0)


def render(with_legs=True):
    from PIL import Image, ImageDraw
    img = Image.new('L', (W, H), 255)
    d = ImageDraw.Draw(img)
    d.polygon(body_outline(), fill=0)
    if with_legs:
        _draw_chain(d, LEG)
    return img


def main():
    import numpy as np
    for name, legs in (('wyvern_ortho_side', True), ('wyvern_ortho_side_nolegs', False)):
        img = render(legs)
        out = os.path.join(ROOT, 'references', name + '.png')
        img.save(out)
        a = np.array(img) < 128
        ys, xs = np.nonzero(a)
        print(f"{name}.png  aire {a.sum()} px  bbox x[{xs.min()}..{xs.max()}] "
              f"y[{ys.min()}..{ys.max()}] ({xs.max() - xs.min()} x {ys.max() - ys.min()})")
    print(f"echelle : {S} u/px -> longueur {round((894 - 62) * S, 2)} u, "
          f"hauteur au garrot {round((SOL - 224) * S, 2)} u")


if __name__ == '__main__':
    main()
