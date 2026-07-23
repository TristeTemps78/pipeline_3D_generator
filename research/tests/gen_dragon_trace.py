"""OUTIL b29 : dessine LA REFERENCE du Colosse — decalque ortho de profil, CORPS + 4 PATTES.

CE FICHIER EST LE DOCUMENT DE DESIGN (comme gen_wyvern_trace.py). Il porte le tableau `BODY`
(x_img, y_haut, y_bas, demi-largeur) et les deux chaines de pattes `LEG_FORE`/`LEG_HIND` que
gen_dragon_cage.py importe tels quels pour lofter la cage 3D. L'IoU ne valide donc PAS le
dessin (il vient d'ici) : il mesure la DERIVE 3D->2D (retrecissement subsurf, forme des
sections, jonction des pattes). La reference est A NOUS -> committable -> le score tourne en CI.

Convention image (identique wyverne) : x vers la DROITE = du museau vers la queue (la creature
regarde a GAUCHE, = facing:"left" du jeu aval), y vers le BAS, sol a y=SOL. La 4e colonne
(demi-largeur) ne sert PAS au dessin 2D — c'est la largeur « de taureau » que le profil ne
peut pas montrer, donc un vrai degre de liberte laisse a la 3D.

Exclus du decalque (appendices ajoutes ensuite, masques par scene.silh.exclude_like) :
ailes, cornes, dents, plaques dorsales.

INTENTION DE DESIGN (registre « colosse lourd, cuirasse », cf. references/dragon_ref.md) —
l'exact oppose de la wyverne, levier par levier :
- crane LARGE et LOURD, museau CARRE (jamais effile), arcade epaisse, masses de machoire ;
- cou COURT et TRES epais (encolure de taureau), porte bas et droit — pas d'arc de cygne ;
- GARROT en bosse musculaire (le point le plus haut) : omoplates + deltoides ;
- tronc en TONNEAU : poitrail profond (quille sternale) et ventre PLEIN — AUCUN pincement de
  taille (c'est la difference nº1 avec la wyverne, qui creuse la taille pour lire « affamee ») ;
- 4 pattes COLONNES epaisses et quasi droites (graviportantes, poids lourd), pieds larges ;
- queue EPAISSE a la base, tenue BAS, contrepoids de massue (pas le fouet haut de la wyverne).

Sorties :
  references/dragon_ortho_side.png         corps + 4 pattes = LA reference scoree
  references/dragon_ortho_side_nolegs.png  tronc seul (aide de lecture, non scoree)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
from gvl.laws import catmull_rom  # noqa: E402  (fonction pure, sans bpy)

W, H = 1150, 720
SOL = 660          # ligne de sol
S = 0.010          # px -> unites Blender (bete de ~10 u de long, ~3.7 u au garrot)
X0, Y0 = 560, SOL  # x_img 560 -> Y=0 (centre la bete) ; sol -> Z=0

# --- LE CORPS : une seule chaine museau -> bout de la queue ---------------------------
# (x_img, y_haut, y_bas, demi-largeur px)   x STRICTEMENT croissant (loft valide)
# y plus PETIT = plus HAUT. Garrot = point haut (y_haut minimal). La demi-largeur ne change
# PAS le decalque 2D.
BODY = [
    # -- CRANE : large, lourd, museau carre (~16 % de la longueur, densement echantillonne :
    #    le subsurf 2 lisse d'autant plus qu'une forme est petite et grossierement stationnee).
    #    Tete PORTEE HAUT et jutant vers l'avant (pas pendante) : le crane massif est tenu par
    #    un cou puissant, il ne DROOPE pas — c'est ce qui separe « colosse » de « lezard mou ».
    (60,  396, 480, 18),   # bout du museau, CARRE, haut et large (crane massif)
    (74,  389, 485, 24),
    (90,  384, 489, 31),   # narines, hautes et larges
    (106, 379, 492, 37),
    (124, 372, 495, 43),   # chanfrein DROIT et massif (pas creux : un broyeur, pas un reptile fin)
    (144, 360, 497, 49),   # avant de l'orbite
    (164, 346, 499, 56),   # ORBITE + arcade LOURDE ; machoire PROFONDE (le crane se creuse)
    (184, 337, 497, 61),   # sommet du crane + masses temporales (le muscle qui broie)
    (204, 340, 487, 60),   # occiput LARGE
    (222, 351, 468, 51),   # ENCOCHE occipitale (legere) : elle detache la tete du cou
    # -- COU de TAUREAU : COURT, tres epais, quasi horizontal, monte franchement au garrot.
    #    Il reste HAUT (pas de creux) : une encolure de taureau, pas l'arc d'un cygne.
    (244, 354, 453, 47),   # depart du cou, deja tres epais
    (270, 348, 445, 50),
    (298, 340, 437, 53),   # le trapeze gonfle
    (326, 330, 431, 57),
    # -- GARROT / EPAULES : la bosse musculaire, POINT LE PLUS HAUT
    (356, 322, 429, 62),   # omoplates
    (390, 297, 430, 68),   # sommet du garrot (deltoides)
    (424, 289, 433, 72),   # dos, tres large
    # -- THORAX en TONNEAU : poitrail profond, ventre PLEIN, ZERO pincement de taille
    (460, 287, 454, 75),   # la quille sternale descend (poitrail profond)
    (498, 287, 471, 77),   # tonneau maximal (poitrail le plus bas)
    (536, 289, 469, 76),   # flanc plein
    (574, 293, 463, 73),   # ventre reste PLEIN (contraste voulu avec la wyverne)
    (612, 297, 459, 70),
    # -- BASSIN / SACRUM : 2e masse (hanches, cuisses)
    (646, 297, 457, 69),   # bassin large
    (680, 293, 453, 71),   # hanche / sacrum : renflement
    (714, 301, 451, 64),   # amorce de la cuisse arriere
    # -- QUEUE : epaisse a la base, tenue BAS, contrepoids lourd (s'amincit lentement)
    (748, 315, 453, 54),   # base de queue EPAISSE
    (786, 331, 457, 45),
    (826, 349, 463, 38),
    (868, 369, 471, 31),
    (912, 391, 479, 24),
    (956, 415, 487, 18),
    (1000, 441, 497, 13),
    (1042, 467, 505, 8),
    (1074, 489, 513, 4),   # pointe de la queue, tenue BAS
]

# --- PATTES : COLONNES epaisses (graviportantes). 2 chaines (avant + arriere), chacune
#     mirror_x -> les 4 pattes. Plantees symetriquement -> de profil la proche et la
#     lointaine se superposent EXACTEMENT (rendu ortho = decalque, pas la penalite d'IoU
#     qu'imposait la pose de marche de Krokmou). (x, y, rayon px)
# v2 (anti-cartoon) : un poteau-ballon a section quasi constante lit « jouet ». Une vraie
# patte a des ARTICULATIONS (le rayon se PINCE au coude/genou/jarret) et des MASSES (triceps,
# cuisse) entre elles ; et elle ZIGZAGUE en x (avant-arriere) au lieu de tomber droit. Le
# decalque et la cage sortant de la meme chaine, le zigzag apparait dans les DEUX -> le score
# de silhouette suit, il ne PUNIT pas la forme articulee.
LEG_FORE = [
    (400, 336, 46),   # epaule (enfouie dans le garrot) — grosse masse
    (404, 388, 45),   # bras / triceps (renfle)
    (396, 440, 34),   # COUDE : pointe vers l'ARRIERE (x recule) et se PINCE
    (407, 498, 27),   # avant-bras, fin et tendineux
    (411, 552, 25),   # carpe (poignet) — le plus fin
    (411, 602, 28),   # metacarpe
    (411, 648, 31),   # pied large (au sol)
]
LEG_HIND = [
    (690, 322, 52),   # hanche (enfouie dans le sacrum)
    (683, 376, 58),   # CUISSE (biceps femoral) : la masse la plus grosse de la bete
    (669, 434, 43),   # GENOU : pointe vers l'AVANT (x recule), se pince
    (688, 492, 31),   # tibia, fin et tendineux
    (705, 546, 28),   # JARRET / talon : pointe vers l'ARRIERE et HAUT (digitigrade)
    (700, 598, 30),   # metatarse long
    (701, 648, 32),   # pied (au sol)
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
        _draw_chain(d, LEG_FORE)
        _draw_chain(d, LEG_HIND)
    return img


def main():
    import numpy as np
    for name, legs in (('dragon_ortho_side', True), ('dragon_ortho_side_nolegs', False)):
        img = render(legs)
        out = os.path.join(ROOT, 'references', name + '.png')
        img.save(out)
        a = np.array(img) < 128
        ys, xs = np.nonzero(a)
        print(f"{name}.png  aire {a.sum()} px  bbox x[{xs.min()}..{xs.max()}] "
              f"y[{ys.min()}..{ys.max()}] ({xs.max() - xs.min()} x {ys.max() - ys.min()})")
    print(f"echelle : {S} u/px -> longueur {round((1074 - 60) * S, 2)} u, "
          f"hauteur au garrot {round((SOL - 289) * S, 2)} u")


if __name__ == '__main__':
    main()
