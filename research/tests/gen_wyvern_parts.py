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
RIDGE = [
    (264, 0.20), (288, 0.28), (312, 0.35), (338, 0.41), (364, 0.45), (394, 0.47),
    (420, 0.48), (450, 0.50), (482, 0.50), (514, 0.47), (548, 0.43), (582, 0.38),
    (616, 0.34), (650, 0.30), (682, 0.25), (714, 0.21), (748, 0.17), (782, 0.13),
    (816, 0.09), (848, 0.06),
]


def ridge_parts():
    out = []
    for i, (x_img, h) in enumerate(RIDGE):
        _, y, z = on_skin(x_img, 0.0)
        lean = 0.30 + 0.55 * (i / (len(RIDGE) - 1))   # de plus en plus couchee vers l'arriere
        out.append({"type": "spike", "id": f"ridge_{i:02d}", "mirror_x": False,
                    "pos": [0.0, y, round(z - 0.06, 3)], "dir": [0.0, lean, 1.0],
                    "height": h, "radius": round(0.055 + 0.30 * h, 3),
                    "flatten": [0.30, 1.35], "tip_frac": 0.06, "seg": 12, "mat": "horn"})
    return out


# ------------------------------------------------------------------------- cornes
def horn_parts():
    """Grande paire occipitale balayee vers l'arriere PAR-DESSUS le cou (la lecture
    « dragon » nº1 en silhouette) + petite paire a l'angle de la machoire."""
    big = tube_along("horn_main",
                     [[0.20, Y(248), Z(336)], [0.29, Y(276), Z(296)],
                      [0.38, Y(312), Z(262)], [0.46, Y(352), Z(240)],
                      [0.50, Y(392), Z(236)]],
                     [0.110, 0.088, 0.064, 0.036, 0.009],
                     up=(1, 0, 0), subsurf=2, mat="horn", mirror_x=True, miter=True)
    jaw = tube_along("horn_jaw",
                     [[0.30, Y(228), Z(408)], [0.37, Y(252), Z(396)],
                      [0.41, Y(276), Z(390)]],
                     [0.055, 0.034, 0.008],
                     up=(1, 0, 0), subsurf=2, mat="horn", mirror_x=True, miter=True)
    return [big, jaw]


# --------------------------------------------------------------- tete : arcade, oeil
def head_parts():
    xe, ye, ze = on_skin(194, 0.30, out=0.92)     # oeil, ENFONCE (out < 1)
    # Round 1 : l'arcade etait un `spike` aplati -> une PLAQUE HEXAGONALE collee sur le
    # crane, l'artefact le plus voyant de la tete. Une arcade est une CRETE osseuse : un
    # tube a demi enfoui qui longe le haut de l'orbite le fait, et son ombre portee
    # tombe pile dans l'oeil — le levier de peur recherche.
    brow_pts, brow_r = [], []
    for x_img, frac, r in ((168, 0.30, 0.055), (186, 0.20, 0.080),
                           (206, 0.15, 0.088), (226, 0.17, 0.062)):
        bx, by, bz = on_skin(x_img, frac, out=0.90)
        brow_pts.append([round(bx, 3), by, bz])
        brow_r.append(r)
    return [
        tube_along("brow", brow_pts, brow_r, up=(0, 0, 1), subsurf=2, mat="hide",
                   mirror_x=True, miter=True),
        # Narines : 2 fentes aplaties sur le dessus du museau (b25). Sans elles, le
        # museau se termine en bloc lisse et la tete lit « jouet ».
        {"type": "globe", "id": "nostril", "mirror_x": True,
         "pos": [round(on_skin(101, 0.22, out=0.72)[0], 3), Y(101), Z(383)],
         "r": [0.045, 0.075, 0.028], "rot": [0, 0, -14], "mat": "hide_matte"},
        # Oeil PETIT (r 0.085 sur un crane de 1.7 u) : c'est le rapport oeil/crane qui
        # fait lire un GROS animal — l'oeil de Krokmou faisait 0.21 pour l'effet inverse.
        {"type": "globe", "id": "eye", "mirror_x": True,
         "pos": [round(xe, 3), ye, ze], "r": 0.075,
         "look_dir": [0.52, -0.80, 0.30], "mat": "eye"},
    ]


# --------------------------------------------------- LIGNE DE BOUCLE : la commissure
# Round 1 : la levre suivait une FRACTION constante de la hauteur du crane. Comme le
# crane se creuse vers l'arriere, la commissure remontait -> un SOURIRE, et toute la bete
# lisait « amicale ». La bouche est donc definie par une altitude EXPLICITE, qui descend
# vers l'arriere : commissure basse = gueule fermee sur quelque chose.
LIP = [(84, 406), (104, 410), (126, 414), (150, 418), (176, 421), (200, 423),
       (222, 422), (242, 417)]


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
FANGS_UP = [(108, 0.10), (134, 0.19), (162, 0.12), (190, 0.155)]
FANGS_LO = [(120, 0.13), (150, 0.09), (178, 0.11)]


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
LIP_XS = [86, 106, 128, 152, 178, 202, 224, 240]


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
            (round(xb + 0.030, 4), yb, zb),                     # arete du surplomb
            (round(xc - 0.026, 4), yc, zc),                     # bas, RENTRE sous la peau
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
# Aile de MANTEL (le rapace qui recouvre sa proie) : coude haut et en avant, poignet
# ramene en arriere, doigts qui retombent -> menace, pas vol.
W_ROOT = (0.45, 0.25, 2.30)
ELBOW = (1.30, -0.90, 3.05)       # coude HAUT et EN AVANT de l'epaule
WRIST = (1.70, 0.55, 3.30)        # poignet ramene en arriere : l'aile reste pliee
TIPS = [(2.65, -0.60, 2.45), (3.10, 0.35, 1.55), (3.00, 1.40, 0.75), (2.50, 2.35, 0.28)]
HIP = (0.62, 2.05, 1.25)          # attache arriere de la membrane, sur le flanc


def _notch(a, b, k=0.12):
    """Feston entre 2 pointes : milieu tire de k vers le POIGNET. Plus profond, le doigt
    (segment droit) sortirait de la membrane (piege mesure en b26)."""
    return [(a[i] + b[i]) / 2.0 * (1 - k) + WRIST[i] * k for i in range(3)]


def web(pid, apex, edge_a, edge_b, notch=0.13, sag=0.30, nu=7, nv=6, mat="membrane",
        normal=None):
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
    verts = []
    for j in range(nv + 1):
        v = j / nv
        far = [edge_a[k] + (edge_b[k] - edge_a[k]) * v for k in range(3)]
        scal = 1.0 - notch * math.sin(math.pi * v)
        for i in range(nu + 1):
            u = i / nu
            amp = sag * math.sin(math.pi * v) * u
            verts.append([round(apex[k] + (far[k] - apex[k]) * u * scal + n[k] * amp, 4)
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
    out = [web("wing_lead", ELBOW, W_ROOT, WRIST, notch=0.34, sag=0.10, nu=5, nv=5,
               normal=nrm)]
    for i, (a, b) in enumerate(zip(TIPS, TIPS[1:])):
        out.append(web(f"wing_web{i}", WRIST, a, b, sag=0.38, normal=nrm))
    # Plagiopatagium : le grand pan qui redescend du dernier doigt jusqu'au flanc. Feston
    # discret (il porte le poids) et affaissement plus marque : c'est lui qui fait le
    # « manteau » qui recouvre la proie.
    out.append(web("wing_flank", WRIST, TIPS[3], HIP, notch=0.06, sag=0.55, nv=7,
                   normal=nrm))
    out.append(tube_along("wing_arm", [list(W_ROOT), list(ELBOW), list(WRIST)],
                          [0.17, 0.12, 0.08], up=(0, 0, 1), subsurf=2, mat="hide",
                          mirror_x=True, miter=True))
    for i, tip in enumerate(TIPS):
        mid = [WRIST[k] + (tip[k] - WRIST[k]) * 0.5 for k in range(3)]
        mid[2] += 0.10                                   # le doigt s'arque vers le haut
        out.append(tube_along(f"wing_finger{i}", [list(WRIST), mid, list(tip)],
                              [0.075, 0.042, 0.012], up=(0, 0, 1), subsurf=2,
                              mat="horn", mirror_x=True, miter=True))
    return out


# ------------------------------------------------------------------ orteils, griffes
def foot_parts():
    ball = [0.33, Y(552), Z(529)]
    toes = {"toe_out": [0.52, Y(488), Z(538)], "toe_in": [0.15, Y(492), Z(538)]}
    out = []
    for pid, tip in toes.items():
        mid = [(ball[k] + tip[k]) / 2 for k in range(3)]
        mid[2] += 0.05
        out.append(tube_along(pid, [ball, mid, tip], [0.075, 0.055, 0.030],
                              up=(0, 0, 1), subsurf=2, mat="hide", mirror_x=True,
                              miter=True))
    # ergot arriere (hallux) : la petite pointe qui dit « ca s'ancre dans le sol »
    out.append(tube_along("toe_spur", [[0.33, Y(566), Z(522)], [0.31, Y(600), Z(528)],
                                       [0.30, Y(626), Z(536)]],
                          [0.062, 0.038, 0.016], up=(0, 0, 1), subsurf=2, mat="hide",
                          mirror_x=True, miter=True))
    claws = {"claw_mid": ([0.33, Y(470), Z(536)], [0.33, Y(430), Z(524)]),
             "claw_out": ([0.52, Y(490), Z(538)], [0.55, Y(452), Z(526)]),
             "claw_in": ([0.15, Y(494), Z(538)], [0.12, Y(456), Z(526)]),
             "claw_spur": ([0.30, Y(622), Z(534)], [0.29, Y(652), Z(524)])}
    for pid, (a, b) in claws.items():
        mid = [(a[k] + b[k]) / 2 for k in range(3)]
        mid[2] -= 0.02
        out.append(tube_along(pid, [a, mid, b], [0.048, 0.032, 0.007],
                              up=(0, 0, 1), subsurf=2, mat="talon", mirror_x=True,
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
    "horn": {"builder": "horn", "p": {
        "color": [0.045, 0.035, 0.030], "rough": 0.42, "stripe_scale": 34,
        "stripe_strength": 0.28, "aniso": 0.35, "var": 0.16, "spec_level": 0.32}},
    "talon": {"builder": "horn", "p": {
        "color": [0.028, 0.022, 0.020], "rough": 0.30, "stripe_scale": 46,
        "stripe_strength": 0.20, "aniso": 0.45, "var": 0.12, "spec_level": 0.45}},
    "fang": {"builder": "enamel", "p": {
        "color": [0.44, 0.40, 0.33], "root_color": [0.14, 0.10, 0.07],
        "rough": 0.28, "sss": 0.10, "root_frac": 0.38}},
    # Transmission FAIBLE (0.14) et pas 0 : c'est elle qui allume la membrane a
    # contre-jour — le vrai « effet dragon ». Le piege CLAUDE.md (taches blanches
    # transmises sur coque fine) frappe au-dela de ~0.3 avec des rim tres fortes ;
    # a 0.14 avec un rim a 1500 on garde le glow sans cramer.
    "membrane": {"builder": "membrane", "p": {
        # PIEGE : le gradient de bord du builder `membrane` eclaircit vers le contour.
    # Sur de GRANDS panneaux c'est joli ; sur nos petits webs inter-doigts, tout le
    # panneau est « bord » -> membrane rose pale, l'element le plus clair de l'image.
    # On rapproche donc edge_color de color : le contraste passe par la LUMIERE.
    "color": [0.012, 0.006, 0.005], "edge_color": [0.021, 0.009, 0.006],
        "rough": 0.62, "transmission": 0.07, "sss": 0.07,
        "sss_radius": [0.30, 0.06, 0.04],
        "vein_scale": 9.0, "vein_strength": 0.46, "vein_width": 0.035, "vein_bump": 0.55,
        "vein_radial_n": 5, "vein_radial_strength": 0.28, "vein_radial_width": 0.26,
        "wrinkle_scale": 26.0, "wrinkle_strength": 0.22}},
    # Iris AMBRE + pupille FENDUE tres etroite : l'oeil de predateur diurne.
    "eye": {"builder": "eye_globe", "p": {
        "sclera_color": [0.035, 0.022, 0.012], "iris_color": [0.52, 0.24, 0.02],
        "iris_color2": [0.74, 0.45, 0.05], "pupil_color": [0.004, 0.004, 0.004],
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
