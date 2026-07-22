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
BODY = [
    (72,  380, 424, 12),   # museau CARRE (44 px) : un museau qui s'effile = herbivore
    (94,  372, 428, 15),   # bosse des narines
    (118, 374, 432, 18),   # CREUX du chanfrein : le profil concave fait le reptile
    (146, 366, 438, 23),
    (176, 348, 442, 32),   # le crane se creuse vers l'orbite
    (206, 328, 444, 45),   # arcade sourciliere + machoire : 116 px de PROFONDEUR
    (232, 320, 434, 50),   # sommet du crane
    (256, 328, 414, 43),   # occiput
    (276, 340, 384, 34),   # ENCOCHE derriere le crane : c'est elle qui DETACHE la tete
    (300, 316, 360, 33),   # cou (44 px seulement : sec et tendu)
    (324, 284, 338, 34),
    (348, 252, 316, 37),
    (372, 232, 302, 41),   # crete du cou
    (394, 230, 300, 45),
    (416, 244, 310, 50),   # base du cou (creux au garrot -> la crete se detache)
    (444, 246, 344, 58),   # garrot / omoplates
    (478, 246, 382, 64),   # QUILLE sternale (136 px de profondeur)
    (512, 246, 388, 66),   # cage thoracique la plus large (142 px)
    (548, 250, 372, 58),
    (582, 254, 350, 46),   # taille PINCEE (96 px) : le contraste fait la faim
    (616, 244, 332, 52),   # bassin
    (648, 236, 320, 54),   # hanche / sacrum, point haut du tronc
    (680, 246, 302, 36),   # base de queue epaisse
    (712, 264, 308, 30),
    (744, 290, 330, 25),
    (778, 318, 358, 20),
    (812, 350, 390, 15),
    (846, 386, 422, 11),
    (874, 418, 450, 7),
    (894, 448, 468, 4),    # pointe de la queue
]

# --- LA PATTE ARRIERE : chaine de disques (x, y, rayon), les 2 pattes superposees ----
# Z digitigrade : hanche -> genou EN AVANT -> talon EN ARRIERE et HAUT -> metatarse
# long -> orteils au sol vers l'avant.
LEG = [
    (628, 318, 52),   # hanche (enfouie dans le bassin)
    (580, 360, 48),   # femur MASSIF (le plus gros muscle d'un bipede)
    (534, 394, 36),   # GENOU (pointe vers l'avant)
    (568, 440, 29),   # tibia
    (602, 476, 25),   # TALON (haut, en arriere — digitigrade)
    (590, 508, 21),   # metatarse
    (574, 526, 17),   # cou-de-pied
    (550, 530, 15),   # orteils
    (518, 532, 12),
    (488, 534, 9),
    (466, 536, 6),    # pointe des griffes
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
