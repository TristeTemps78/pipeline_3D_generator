"""OUTIL : appendices de la wyverne — epines dorsales, cornes, arcade, oeil, crocs,
AILES, orteils/griffes. FUSIONNE dans specs/wyvern.json (remplace les parts de meme id,
ajoute les materiaux manquants) : contrairement a gen_wyvern_cage.py, ne detruit rien.

Repere : la creature regarde -Y ; Y = (x_img - 420)*0.009, Z = (545 - y_img)*0.009
(cf. references/wyvern_ref.md). Toutes les positions viennent des stations du document
de design, pas de nombres tires au hasard.

Regles b26 rappelees ici parce qu'elles coutent cher a redecouvrir :
- plaque fine (membrane) -> subsurf 0, sinon le Catmull-Clark rogne le contour et avale
  les festons ;
- un creux de membrane ne peut pas etre plus profond que la corde poignet->pointe
  suivante, sinon le doigt (segment droit) sort de la membrane.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from gen_appendages import _norm, plate, tube_along  # noqa: E402
from gen_wyvern_trace import BODY, S  # noqa: E402
from gen_appendages import _norm as _n2  # noqa: E402,F401
from gen_wyvern_cage import Y, Z  # noqa: E402


def station(x_img):
    """Interpole le profil de design a un x quelconque -> (y_haut, y_bas, demi-largeur)."""
    for (xa, ta, ba, wa), (xb, tb, bb, wb) in zip(BODY, BODY[1:]):
        if xa <= x_img <= xb:
            u = (x_img - xa) / (xb - xa)
            return (ta + u * (tb - ta), ba + u * (bb - ba), wa + u * (wb - wa))
    return BODY[-1][1:]


def on_skin(x_img, frac, out=0.78):
    """Point de la SURFACE a l'abscisse x_img : `frac` = 0 au sommet du dos, 1 au ventre ;
    `out` = fraction de la demi-largeur locale (1 = flanc le plus large). Evite de poser
    les appendices « en l'air » — le bug le plus courant de la methode cage."""
    yt, yb, w = station(x_img)
    y_img = yt + frac * (yb - yt)
    # largeur de l'ellipse a cette hauteur (section ovale du loft)
    t = (y_img - (yt + yb) / 2.0) / max((yb - yt) / 2.0, 1e-6)
    span = math.sqrt(max(0.0, 1.0 - min(1.0, t * t) ** 1.0))
    return (round(w * S * span * out, 3), Y(x_img), Z(y_img))


# ----------------------------------------------------------------- epines dorsales
# Rangee mediane occiput -> queue. Profil de hauteur : discret sur le crane, MAXIMUM sur
# le garrot (c'est la que la bete parait large), degressif sur la queue.
# v2 : hauteurs DIVISEES PAR ~1.8. Une crete de 0.50 u sur un dos de 1.0 u, c'est du
# fantasy illustre ; les osteodermes d'un crocodile ou d'un varan depassent a peine.
RIDGE = [
    (220, 0.11), (244, 0.15), (268, 0.19), (292, 0.23), (316, 0.27), (340, 0.30),
    (364, 0.33), (390, 0.35), (416, 0.37), (444, 0.38), (472, 0.37), (500, 0.35),
    (530, 0.32), (560, 0.29), (590, 0.26), (620, 0.23), (652, 0.20), (686, 0.17),
    (720, 0.14), (754, 0.11), (788, 0.08), (822, 0.06),
]


def crystal(pid, base, tip, r, sides=6, waist=0.62, twist=0.0, mat="ice"):
    """Prisme FACETTE effile : anneau de base -> anneau d'epaulement -> pointe.

    Un cristal de glace ne se modelise pas comme une epine charnue : ce sont des PLANS
    qui se coupent en aretes vives, et c'est l'arete qui accroche la lumiere. D'ou
    `subsurf: 0` — le Catmull-Clark arrondirait justement ce qui fait la lecture. Le
    `waist` (epaulement) evite le cone parfait : un vrai cristal a un fut puis une
    pointe, pas une pente unique."""
    d = [tip[k] - base[k] for k in range(3)]
    ln = math.sqrt(sum(c * c for c in d)) or 1.0
    t = [c / ln for c in d]
    up = (0.0, 0.0, 1.0) if abs(t[2]) < 0.9 else (1.0, 0.0, 0.0)
    s_ = _norm([t[1] * up[2] - t[2] * up[1], t[2] * up[0] - t[0] * up[2],
                t[0] * up[1] - t[1] * up[0]])
    u_ = _norm([s_[1] * t[2] - s_[2] * t[1], s_[2] * t[0] - s_[0] * t[2],
                s_[0] * t[1] - s_[1] * t[0]])
    verts, faces = [], []
    for ring, (frac, rad, rot) in enumerate(((0.0, r, 0.0), (waist, r * 0.78, twist))):
        c = [base[k] + d[k] * frac for k in range(3)]
        for j in range(sides):
            a = rot + 2.0 * math.pi * j / sides
            verts.append([round(c[k] + (s_[k] * math.cos(a) + u_[k] * math.sin(a)) * rad, 4)
                          for k in range(3)])
    verts.append([round(v, 4) for v in tip])
    for j in range(sides):
        k = (j + 1) % sides
        faces.append([j, k, sides + k, sides + j])
        faces.append([sides + j, sides + k, 2 * sides])
    faces.append(list(reversed(range(sides))))
    return {"type": "cage", "id": pid, "mirror_x": False, "subsurf": 0,
            "mat": mat, "verts": verts, "faces": faces}


def ridge_parts():
    """Type GLACE : la crete dorsale n'est plus une rangee d'osteodermes de keratine
    mais un CHAMP DE CRISTAUX pousses hors de la peau — c'est le trait d'espece le plus
    lisible en silhouette. Chaque station porte une pointe maitresse plus deux eclats
    lateraux plus petits et divergents : une pousse cristalline n'est jamais alignee."""
    out = []
    for i, (x_img, h) in enumerate(RIDGE):
        _, y, z = on_skin(x_img, 0.0)
        lean = 0.30 + 0.55 * (i / (len(RIDGE) - 1))
        base = [0.0, y, z - 0.05]
        n = _norm([0.0, lean, 1.0])
        out.append(crystal(f"ridge_{i:02d}", base,
                           [base[k] + n[k] * h * 1.45 for k in range(3)],
                           round(0.016 + 0.115 * h, 3), twist=0.4 * i))
        if i % 2 == 0 and h > 0.14:      # eclats lateraux, une station sur deux
            for sgn in (1, -1):
                d2 = _norm([sgn * 0.55, lean * 0.8, 1.0])
                out.append(crystal(f"ridge_{i:02d}_s{'l' if sgn > 0 else 'r'}",
                                   [sgn * 0.045, y - 0.02, z - 0.04],
                                   [sgn * 0.045 + d2[0] * h * 0.80,
                                    y - 0.02 + d2[1] * h * 0.80,
                                    z - 0.04 + d2[2] * h * 0.80],
                                   round(0.011 + 0.075 * h, 3), sides=5, twist=0.9 * i))
    return out


# ------------------------------------------------------------------------- cornes
def horn_parts():
    """Grande paire occipitale balayee vers l'arriere PAR-DESSUS le cou (la lecture
    « dragon » nº1 en silhouette) + petite paire a l'angle de la machoire."""
    pts = [[0.19, Y(194), Z(372)], [0.27, Y(220), Z(342)], [0.35, Y(252), Z(312)],
           [0.41, Y(288), Z(294)], [0.44, Y(326), Z(292)]]
    radii = [0.085, 0.068, 0.050, 0.028, 0.008]
    out = []
    # ASYMETRIE VOULUE : la corne droite est CASSEE net. Une bete parfaitement
    # symetrique et intacte lit « figurine neuve » ; une usure suffit a dire « ca vit,
    # ca se bat ». D'ou 2 cornes separees au lieu d'un mirror_x.
    for side, suf, keep, tip_r in ((1, "_l", 5, 0.007), (-1, "_r", 3, 0.030)):
        out.append(tube_along("horn_main" + suf,
                              [[side * x, y, z] for x, y, z in pts[:keep]],
                              radii[:keep - 1] + [tip_r],
                              up=(1, 0, 0), subsurf=2, mat="ice", mirror_x=False,
                              miter=True))
    out.append(tube_along("horn_jaw",
                          [[0.24, Y(178), Z(436)], [0.29, Y(198), Z(428)],
                           [0.32, Y(216), Z(424)]],
                          [0.040, 0.024, 0.006],
                          up=(1, 0, 0), subsurf=2, mat="ice", mirror_x=True,
                          miter=True))
    return out


# --------------------------------------------------------------- tete : arcade, oeil
def head_parts():
    xe, ye, ze = on_skin(148, 0.30, out=0.88)     # oeil, ENFONCE (out < 1)
    # Round 1 : l'arcade etait un `spike` aplati -> une PLAQUE HEXAGONALE collee sur le
    # crane, l'artefact le plus voyant de la tete. Une arcade est une CRETE osseuse : un
    # tube a demi enfoui qui longe le haut de l'orbite le fait, et son ombre portee
    # tombe pile dans l'oeil — le levier de peur recherche.
    brow_pts, brow_r = [], []
    for x_img, frac, r in ((130, 0.31, 0.034), (150, 0.20, 0.050),
                           (168, 0.15, 0.056), (188, 0.18, 0.038)):
        bx, by, bz = on_skin(x_img, frac, out=0.90)
        brow_pts.append([round(bx, 3), by, bz])
        brow_r.append(r)
    return [
        tube_along("brow", brow_pts, brow_r, up=(0, 0, 1), subsurf=2, mat="hide",
                   mirror_x=True, miter=True),
        # Narines : 2 fentes aplaties sur le dessus du museau (b25). Sans elles, le
        # museau se termine en bloc lisse et la tete lit « jouet ».
        {"type": "globe", "id": "nostril", "mirror_x": True,
         "pos": [round(on_skin(78, 0.22, out=0.70)[0], 3), Y(78), Z(408)],
         "r": [0.028, 0.048, 0.018], "rot": [0, 0, -14], "mat": "hide_matte"},
        # Oeil PETIT (r 0.085 sur un crane de 1.7 u) : c'est le rapport oeil/crane qui
        # fait lire un GROS animal — l'oeil de Krokmou faisait 0.21 pour l'effet inverse.
        {"type": "globe", "id": "eye", "mirror_x": True,
         "pos": [round(xe, 3), ye, ze], "r": 0.072,
         "look_dir": [0.52, -0.80, 0.30], "mat": "eye"},
        # PAUPIERE : un globe nu se lit « bille de verre collee ». Une plaque de peau
        # qui mord sur le haut de l'oeil suffit a l'inscrire dans le crane — et son
        # ombre portee retrecit la fente, ce qui durcit le regard.
        # MASSE DE MACHOIRE : sans elle, museau et crane forment un seul fuseau lisse et
        # la tete lit « chausson ». Le renflement des adducteurs, juste derriere la
        # commissure, cree le DECROCHEMENT qui separe les deux — et donne au crane sa
        # forme en coin vue de dessus.
        {"type": "globe", "id": "jaw_mass", "mirror_x": True,
         "pos": [round(on_skin(180, 0.44, out=0.82)[0], 3), Y(180), Z(424)],
         "r": [0.075, 0.155, 0.115], "rot": [0, 0, 6], "mat": "hide"},
        {"type": "globe", "id": "lid_up", "mirror_x": True,
         "pos": [round(xe - 0.012, 3), ye, round(ze + 0.058, 3)],
         "r": [0.055, 0.098, 0.040], "rot": [-16, 0, -8], "mat": "hide"},
    ]


# --------------------------------------------------- LIGNE DE BOUCLE : la commissure
# Round 1 : la levre suivait une FRACTION constante de la hauteur du crane. Comme le
# crane se creuse vers l'arriere, la commissure remontait -> un SOURIRE, et toute la bete
# lisait « amicale ». La bouche est donc definie par une altitude EXPLICITE, qui descend
# vers l'arriere : commissure basse = gueule fermee sur quelque chose.
LIP = [(54, 428), (72, 431), (92, 434), (112, 437), (134, 440), (156, 442),
       (178, 443), (196, 438)]


def lip_frac(x_img):
    """Altitude de la levre a x, convertie en fraction locale pour `on_skin`."""
    for (xa, ya), (xb, yb) in zip(LIP, LIP[1:]):
        if xa <= x_img <= xb:
            y = ya + (yb - ya) * (x_img - xa) / (xb - xa)
            break
    else:
        y = LIP[0][1] if x_img < LIP[0][0] else LIP[-1][1]
    yt, ybo, _ = station(x_img)
    return (y - yt) / max(ybo - yt, 1e-6)


# ------------------------------------------------------------------------- crocs
# Peu nombreux, GROS et IRREGULIERS : une rangee reguliere se lit « peigne » ou « dents
# de dessin anime ». Tailles alternees + une canine nettement plus longue que les autres.
# v2 : crocs proportionnes au NOUVEAU crane (1.06 u) — ~8-10 % de sa longueur, comme
# un theropode reel. Un croc a 18 % du crane, c'est un dessin anime. Le 3e superieur est
# CASSE (h 0.030) : meme logique d'usure que la corne droite.
FANGS_UP = [(66, 0.060), (88, 0.105), (110, 0.032), (134, 0.095), (158, 0.072)]
FANGS_LO = [(76, 0.080), (100, 0.056), (124, 0.066), (150, 0.050)]


def fang_parts():
    """Round 1 : crocs poses A la ligne de levre et pointes vers le BAS -> entierement
    NOYES dans la machoire inferieure (le crane est une peau fermee, il n'y a pas de
    bouche ouverte). Un croc de gueule close se lit forcement sur le COTE : on le sort
    lateralement (out > 1) et on l'incline vers l'exterieur pour qu'il perce la peau."""
    out = []
    for i, (x_img, h) in enumerate(FANGS_UP):
        x, y, z = on_skin(x_img, lip_frac(x_img) - 0.02, out=1.03)
        out.append({"type": "spike", "id": f"tooth_u{i}", "mirror_x": True,
                    "pos": [round(x, 3), y, round(z + 0.03, 3)], "dir": [0.42, -0.08, -1.0],
                    "height": h, "radius": round(h * 0.30, 3), "tip_frac": 0.03,
                    "seg": 10, "mat": "fang"})
    for i, (x_img, h) in enumerate(FANGS_LO):
        x, y, z = on_skin(x_img, lip_frac(x_img) + 0.09, out=1.03)
        out.append({"type": "spike", "id": f"tooth_l{i}", "mirror_x": True,
                    "pos": [round(x, 3), y, round(z - 0.03, 3)], "dir": [0.42, -0.12, 1.0],
                    "height": h, "radius": round(h * 0.30, 3), "tip_frac": 0.03,
                    "seg": 10, "mat": "fang"})
    return out


# -------------------------------------------------------------- ligne de levre (b25)
LIP_XS = [56, 74, 94, 114, 136, 158, 178, 194]


def lip_part():
    """Sur une peau sombre, une bouche ne se voit ni par la couleur ni par une rainure
    symetrique : elle se voit par l'OMBRE d'un surplomb (lecon b25, payee en un round
    perdu). Section = levre superieure qui DEBORDE (bord haut sorti, bord bas rentre),
    materiau mat -> le contraste vient de la rugosite et de l'ombre portee."""
    rings = []
    for x_img in LIP_XS:
        f = lip_frac(x_img)
        xa, ya, za = on_skin(x_img, f - 0.08, out=1.0)
        xb, yb, zb = on_skin(x_img, f, out=1.0)
        xc, yc, zc = on_skin(x_img, f + 0.08, out=1.0)
        rings.append([
            (round(xa + 0.016, 4), ya, round(za + 0.006, 4)),   # haut, sorti
            (round(xb + 0.050, 4), yb, zb),                     # arete du surplomb
            (round(xc - 0.038, 4), yc, zc),                     # bas, RENTRE sous la peau
            (round(xa - 0.014, 4), ya, round(za - 0.004, 4)),   # retour interne
        ])
    verts = [list(v) for r in rings for v in r]
    faces = []
    for r in range(len(rings) - 1):
        for j in range(4):
            a, b = r * 4 + j, r * 4 + (j + 1) % 4
            faces.append([a, b, b + 4, a + 4])
    faces.append([3, 2, 1, 0])
    last = (len(rings) - 1) * 4
    faces.append([last, last + 1, last + 2, last + 3])
    return {"type": "cage", "id": "mouth_line", "mirror_x": True, "subsurf": 0,
            "mat": "hide_matte", "verts": verts, "faces": faces}


# -------------------------------------------------------------------------- ailes
# v4. Les v1-v3 cherchaient une aile A DEMI PLIEE (« mantel ») : a chaque fois les
# panneaux tombaient en plans quasi verticaux et lisaient « rideau de carton ». Une
# membrane PLIEE est un exercice de drape, tres dur a faire tenir en quelques polygones.
# Une membrane TENDUE, elle, est physiquement plate entre ses doigts : c'est sa vraie
# forme, et ce sont les DOIGTS en relief + le feston du bord de fuite qui la font lire.
# D'ou : ailes deployees, envergure 9.2 u pour un corps de 7.5 u.
W_ROOT = (0.42, -0.15, 2.28)
ELBOW = (1.60, -0.90, 2.85)       # coude tendu vers l'EXTERIEUR
WRIST = (2.90, 0.10, 3.10)        # poignet loin, l'aile est ouverte
TIPS = [(3.90, -0.75, 3.05), (4.55, 0.25, 2.55), (4.60, 1.45, 1.85), (4.10, 2.65, 1.05)]
HIP = (0.60, 1.90, 1.15)          # attache arriere de la membrane, sur le flanc


def _notch(a, b, k=0.12):
    """Feston entre 2 pointes : milieu tire de k vers le POIGNET. Plus profond, le doigt
    (segment droit) sortirait de la membrane (piege mesure en b26)."""
    return [(a[i] + b[i]) / 2.0 * (1 - k) + WRIST[i] * k for i in range(3)]


def web(pid, apex, edge_a, edge_b, notch=0.13, sag=0.30, nu=9, nv=8, mat="membrane",
        normal=None, crease=0.055, folds=2.5, drop=0.0):
    """Panneau de membrane entre DEUX doigts, en grille — pas en polygone.

    Rounds 1 et 2 (plaque unique, puis une plaque par inter-doigt) ont echoue de la meme
    facon : une facette plane, quel que soit son contour, se lit « origami ». Une peau
    tendue a besoin de COURBURE a l'interieur du panneau. D'ou la parametrisation :
      P(u,v) = apex + u * (1 - notch*sin(pi*v)) * (lerp(a, b, v) - apex)   puis un
      affaissement le long de la normale, ~ sin(pi*v) * u.
    `notch` porte le feston du bord de fuite (0 sur les doigts, maximal au milieu — la
    regle b26 « pas plus profond que la corde » est respectee par construction, le creux
    etant un RACCOURCISSEMENT radial et non un point deplace derriere les doigts) ;
    `sag` porte le ventre de la membrane."""
    if normal is not None:
        n = list(normal)
    else:
        ea = [edge_a[k] - apex[k] for k in range(3)]
        eb = [edge_b[k] - apex[k] for k in range(3)]
        n = _norm([ea[1] * eb[2] - ea[2] * eb[1], ea[2] * eb[0] - ea[0] * eb[2],
                   ea[0] * eb[1] - ea[1] * eb[0]])
    if n[2] > 0:                       # l'affaissement va toujours vers le BAS
        n = [-c for c in n]
    # v3 (feedback « trop cartoon ») : deux ajouts qui font passer la membrane de
    # « carton » a « peau ».
    # 1. l'affaissement suit la GRAVITE, pas la normale du panneau : une membrane au
    #    repos PEND, elle ne se creuse pas perpendiculairement a elle-meme ;
    # 2. PLIS RADIAUX (`crease`/`folds`) : une membrane alaire se froisse en eventail
    #    depuis le poignet. C'est le detail qui casse la facette plane, et il se voit
    #    en silhouette comme en speculaire — le shader `wrinkle_*` ne fait ni l'un ni
    #    l'autre, il ne joue que sur la normale.
    g = _norm([n[0] * 0.35, n[1] * 0.35, n[2] * 0.35 - 1.0])
    verts = []
    for j in range(nv + 1):
        v = j / nv
        far = [edge_a[k] + (edge_b[k] - edge_a[k]) * v for k in range(3)]
        scal = 1.0 - notch * math.sin(math.pi * v)
        rip = crease * math.sin(folds * 2.0 * math.pi * v) * math.sin(math.pi * v)
        for i in range(nu + 1):
            u = i / nu
            amp = sag * math.sin(math.pi * v) * u * u
            # `drop` : toute la nappe est reculee sous le plan des os -> les doigts
            # (tubes poses sur les bords) RESSORTENT en nervures au lieu d'affleurer.
            # Sans ca, os et membrane se confondent et il ne reste qu'une facette.
            verts.append([round(apex[k] + (far[k] - apex[k]) * u * scal
                                + g[k] * amp + n[k] * (rip * (u ** 1.4) - drop), 4)
                          for k in range(3)])
    faces = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append([a, a + 1, a + nu + 2, a + nu + 1])
    return {"type": "cage", "id": pid, "mirror_x": True, "subsurf": 0,
            "mat": mat, "verts": verts, "faces": faces}


def wing_parts():
    # Une normale d'affaissement COMMUNE a tous les panneaux : calculee panneau par
    # panneau, elle bascule d'un panneau au suivant et fabrique des aretes en accordeon
    # (l'effet « parapluie » du round 3).
    nrm = _norm([(ELBOW[1] - W_ROOT[1]) * (TIPS[2][2] - W_ROOT[2])
                 - (ELBOW[2] - W_ROOT[2]) * (TIPS[2][1] - W_ROOT[1]),
                 (ELBOW[2] - W_ROOT[2]) * (TIPS[2][0] - W_ROOT[0])
                 - (ELBOW[0] - W_ROOT[0]) * (TIPS[2][2] - W_ROOT[2]),
                 (ELBOW[0] - W_ROOT[0]) * (TIPS[2][1] - W_ROOT[1])
                 - (ELBOW[1] - W_ROOT[1]) * (TIPS[2][0] - W_ROOT[0])])
    # Propatagium : le voile CONCAVE tendu devant le bras (epaule->coude->poignet).
    # Le round 3 mettait une plaque plate a cet endroit : c'etait le grand triangle de
    # papier qu'on voyait de profil. Un voile creux, lui, dessine le bord d'attaque.
    out = [web("wing_lead", ELBOW, W_ROOT, WRIST, notch=0.34, sag=0.06, nu=6, nv=6,
               normal=nrm, crease=0.02, folds=1.5, drop=0.05)]
    for i, (a, b) in enumerate(zip(TIPS, TIPS[1:])):
        out.append(web(f"wing_web{i}", WRIST, a, b, sag=0.16, normal=nrm,
                       crease=0.045, folds=2.0 + 0.5 * i, drop=0.055))
    # Plagiopatagium : le grand pan qui redescend du dernier doigt jusqu'au flanc. Feston
    # discret (il porte le poids) et affaissement plus marque : c'est lui qui fait le
    # « manteau » qui recouvre la proie.
    out.append(web("wing_flank", WRIST, TIPS[3], HIP, notch=0.06, sag=0.30, nv=9,
                   normal=nrm, crease=0.065, folds=3.0, drop=0.055))
    out.append(tube_along("wing_arm", [list(W_ROOT), list(ELBOW), list(WRIST)],
                          [0.20, 0.145, 0.105], up=(0, 0, 1), subsurf=2, mat="hide",
                          mirror_x=True, miter=True))
    for i, tip in enumerate(TIPS):
        mid = [WRIST[k] + (tip[k] - WRIST[k]) * 0.5 for k in range(3)]
        mid[2] += 0.10                                   # le doigt s'arque vers le haut
        out.append(tube_along(f"wing_finger{i}", [list(WRIST), mid, list(tip)],
                              [0.105, 0.058, 0.014], up=(0, 0, 1), subsurf=2,
                              mat="ice", mirror_x=True, miter=True))
    return out


# ------------------------------------------------------------------ orteils, griffes
def foot_parts():
    ball = [0.33, Y(558), Z(534)]
    toes = {"toe_out": [0.50, Y(478), Z(541)], "toe_in": [0.16, Y(482), Z(541)]}
    out = []
    for pid, tip in toes.items():
        mid = [(ball[k] + tip[k]) / 2 for k in range(3)]
        mid[2] += 0.05
        out.append(tube_along(pid, [ball, mid, tip], [0.075, 0.055, 0.030],
                              up=(0, 0, 1), subsurf=2, mat="hide", mirror_x=True,
                              miter=True))
    # ergot arriere (hallux) : la petite pointe qui dit « ca s'ancre dans le sol »
    out.append(tube_along("toe_spur", [[0.33, Y(572), Z(528)], [0.31, Y(604), Z(534)],
                                       [0.30, Y(630), Z(540)]],
                          [0.050, 0.031, 0.013], up=(0, 0, 1), subsurf=2, mat="hide",
                          mirror_x=True, miter=True))
    claws = {"claw_mid": ([0.33, Y(458), Z(541)], [0.33, Y(418), Z(529)]),
             "claw_out": ([0.50, Y(480), Z(541)], [0.53, Y(442), Z(529)]),
             "claw_in": ([0.16, Y(484), Z(541)], [0.13, Y(446), Z(529)]),
             "claw_spur": ([0.30, Y(626), Z(538)], [0.29, Y(656), Z(528)])}
    for pid, (a, b) in claws.items():
        mid = [(a[k] + b[k]) / 2 for k in range(3)]
        mid[2] -= 0.02
        out.append(tube_along(pid, [a, mid, b], [0.048, 0.032, 0.007],
                              up=(0, 0, 1), subsurf=2, mat="ice_claw", mirror_x=True,
                              miter=True))
    return out


# ------------------------------------------------------------------------ materiaux
MATS = {
    # Peau MATE : sert la ou le relief doit se lire par l'ombre, pas par le brillant
    # (ligne de levre). Meme builder que `hide`, rugosite poussee et specular ecrase.
    "hide_matte": {"builder": "reptile_scales", "p": {
        "scale": 28, "scale2": 74, "bump": 0.05,
        "base": [0.012, 0.010, 0.009], "tint": [0.016, 0.012, 0.009],
        "rough": 0.74, "rough_edge": 0.62, "sss": 0.05, "micro": 0.05,
        "edge_copper": 0.0, "edge_width": 0.015, "instance_variation": 0.14,
        "patina_amount": 0.0, "spec_level": 0.07, "sheen": 0.0,
        "aniso": 0.0, "specular_tint": [0.86, 0.84, 0.8]}},
    "fang": {"builder": "enamel", "p": {
        "color": [0.62, 0.68, 0.72], "root_color": [0.16, 0.22, 0.28],
        "rough": 0.28, "sss": 0.10, "root_frac": 0.38}},
    # Transmission FAIBLE (0.14) et pas 0 : c'est elle qui allume la membrane a
    # contre-jour — le vrai « effet dragon ». Le piege CLAUDE.md (taches blanches
    # transmises sur coque fine) frappe au-dela de ~0.3 avec des rim tres fortes ;
    # a 0.14 avec un rim a 1500 on garde le glow sans cramer.
    "membrane": {"builder": "membrane", "p": {
        "color": [0.115, 0.170, 0.235], "edge_color": [0.30, 0.40, 0.53],
        "rough": 0.48, "transmission": 0.20, "sss": 0.22,
        "sss_radius": [0.10, 0.18, 0.26],
        "vein_scale": 9.0, "vein_strength": 0.42, "vein_width": 0.035, "vein_bump": 0.55,
        "vein_dark": [0.10, 0.22, 0.38],
        "vein_radial_n": 5, "vein_radial_strength": 0.26, "vein_radial_width": 0.26,
        "wrinkle_scale": 26.0, "wrinkle_strength": 0.22}},
    "ice": {"builder": "ice", "p": {}},
    "ice_claw": {"builder": "ice", "p": {
        "color": [0.60, 0.74, 0.90], "deep": [0.10, 0.24, 0.42],
        "transmission": 0.22, "sss": 0.62, "rough_clear": 0.10, "rough_frost": 0.60,
        "frost_scale": 11.0, "fracture_scale": 22.0}},
    # Iris AMBRE + pupille FENDUE tres etroite : l'oeil de predateur diurne.
    "eye": {"builder": "eye_globe", "p": {
        "sclera_color": [0.055, 0.070, 0.085], "iris_color": [0.30, 0.55, 0.72],
        "iris_color2": [0.68, 0.86, 0.96], "pupil_color": [0.004, 0.004, 0.004],
        "pupil_width": 0.17, "pupil_length": 2.1, "pupil_edge": 0.012,
        "iris_r": 0.42, "rough": 0.10, "clearcoat": 0.12, "spec_level": 0.2,
        "glow": 0.04, "catchlight": 0.85, "catchlight_pos": [0.46, 0.40],
        "catchlight_size": 0.045, "catchlight_soft": 0.02}},
}


def main():
    path = os.path.join(ROOT, 'specs', 'wyvern.json')
    spec = json.load(open(path))
    new = (ridge_parts() + horn_parts() + head_parts() + fang_parts()
           + [lip_part()] + wing_parts() + foot_parts())
    by_id = {p['id']: p for p in spec['parts']}
    for p in new:
        by_id[p['id']] = p
    spec['parts'] = list(by_id.values())
    spec['materials'].update({k: v for k, v in MATS.items()
                              if k not in spec['materials']})
    with open(path, 'w') as f:
        json.dump(spec, f, indent=1)
    print(f"{len(new)} appendices fusionnes -> {len(spec['parts'])} parts")
    print("  ", ", ".join(p['id'] for p in new))


if __name__ == '__main__':
    main()
