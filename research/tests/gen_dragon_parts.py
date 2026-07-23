"""OUTIL b29 : appendices du Colosse — PLAQUES OSSEUSES dorsales (l'identite : cuirasse),
cornes lourdes balayees, arcade + oeil + machoire, crocs, ligne de levre, AILES deployees,
orteils/griffes des 4 pieds. FUSIONNE dans specs/dragon.json (remplace les parts de meme id,
ajoute les materiaux manquants) : idempotent, contrairement a gen_dragon_cage.py.

Repere : la creature regarde -Y ; Y = (x_img - 560)*0.010, Z = (660 - y_img)*0.010
(cf. references/dragon_ref.md). Toutes les positions viennent des stations du document de
design, pas de nombres tires au hasard.

Regles b26 rappelees (elles coutent cher a redecouvrir) :
- plaque fine / facettee -> subsurf 0, sinon le Catmull-Clark rogne le contour ;
- un creux de membrane ne peut pas etre plus profond que la corde poignet->pointe suivante.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from gen_appendages import _norm, tube_along  # noqa: E402
from gen_dragon_trace import BODY, S  # noqa: E402
from gen_dragon_cage import Y, Z  # noqa: E402


def station(x_img):
    """Interpole le profil de design a un x quelconque -> (y_haut, y_bas, demi-largeur)."""
    for (xa, ta, ba, wa), (xb, tb, bb, wb) in zip(BODY, BODY[1:]):
        if xa <= x_img <= xb:
            u = (x_img - xa) / (xb - xa)
            return (ta + u * (tb - ta), ba + u * (bb - ba), wa + u * (wb - wa))
    return BODY[-1][1:]


def on_skin(x_img, frac, out=0.78):
    """Point de la SURFACE a l'abscisse x_img : `frac` = 0 au sommet du dos, 1 au ventre ;
    `out` = fraction de la demi-largeur locale (1 = flanc le plus large)."""
    yt, yb, w = station(x_img)
    y_img = yt + frac * (yb - yt)
    t = (y_img - (yt + yb) / 2.0) / max((yb - yt) / 2.0, 1e-6)
    span = math.sqrt(max(0.0, 1.0 - min(1.0, t * t)))
    return (round(w * S * span * out, 3), Y(x_img), Z(y_img))


# ==================================================================== PLAQUES OSSEUSES
# LE TRAIT D'ESPECE (cf. dragon_ref.md) : le dos n'est PAS herisse de pointes (ca, c'est le
# dragon d'illustration ou la wyverne de glace). Il est CUIRASSE — des osteodermes epais et
# FUSIONNES, facon crocodile/ankylosaure. Modelisation : plaques facettees basses (subsurf 0,
# sinon le Catmull-Clark les fond en bosses molles) en DEUX rangees paramedianes + une rangee
# de bosses mediane discrete. Grosses plaques sur le garrot et le sacrum (les points de choc).

def scute(pid, base, up, along, length, width, rise, keel=0.55):
    """Un osteoderme keele : hexagone allonge le long du corps (`along`), bombe par une
    ARETE mediane (keel). Facettes vives -> lit « os », pas « ballon ». subsurf 0."""
    a = _norm(along)
    u = _norm(up)
    o = _norm([a[1] * u[2] - a[2] * u[1], a[2] * u[0] - a[0] * u[2],
               a[0] * u[1] - a[1] * u[0]])          # laterale = along x up
    hl, hw = length / 2.0, width / 2.0

    def P(fa, fo, fz):
        return [round(base[k] + a[k] * fa * hl + o[k] * fo * hw + u[k] * fz, 4)
                for k in range(3)]
    # 6 sommets de contour (hexagone allonge) + 2 sommets de crete (arete mediane surelevee)
    verts = [P(-1.0, 0.0, 0.0), P(-0.5, 1.0, 0.06 * rise), P(0.5, 1.0, 0.06 * rise),
             P(1.0, 0.0, 0.0), P(0.5, -1.0, 0.06 * rise), P(-0.5, -1.0, 0.06 * rise),
             P(-0.35, 0.0, rise), P(0.35, 0.0, rise)]
    faces = [[0, 1, 6], [1, 2, 7, 6], [2, 3, 7], [3, 4, 7], [4, 5, 6, 7], [5, 0, 6],
             [0, 5, 4, 3, 2, 1]]
    return {"type": "cage", "id": pid, "mirror_x": False, "subsurf": 0,
            "mat": "bone", "verts": verts, "faces": faces}


# Rangee paramediane : (x_img, echelle). Du haut du cou au tiers de la queue. Maximum sur le
# garrot et le sacrum. `out` (fraction de largeur) tient les 2 rangees de part et d'autre du dos.
PLATES = [(238, 0.55), (262, 0.62), (288, 0.70), (316, 0.80), (346, 0.92), (378, 1.02),
          (410, 1.08), (444, 1.05), (480, 0.98), (516, 0.94), (552, 0.92), (588, 0.95),
          (622, 1.00), (656, 1.02), (690, 1.00), (724, 0.88), (760, 0.74), (798, 0.60),
          (838, 0.48), (880, 0.36)]


def plate_parts():
    out = []
    for i, (x_img, sc) in enumerate(PLATES):
        yt, _, w = station(x_img)
        z_top = Z(yt)
        y = Y(x_img)
        # 2 rangees paramedianes (mirror_x du part), posees sur l'epaule du dos
        for row, (frac_out, tilt) in enumerate(((0.34, 0.30), (0.66, 0.62))):
            wx = w * S * frac_out
            base = [wx, y, z_top - 0.02 * sc]
            up = _norm([tilt, 0.05, 1.0])            # bombe vers l'exterieur
            along = (0.0, 1.0, 0.0)                  # allongee le long du corps
            out.append(scute(f"plate_{i:02d}_r{row}", base, up, along,
                             length=0.30 * sc, width=0.22 * sc, rise=0.11 * sc))
            out[-1]["mirror_x"] = True
        # bosse mediane basse (sur l'axe), une station sur deux
        if i % 2 == 0:
            out.append(scute(f"plate_{i:02d}_mid", [0.0, y, z_top + 0.01],
                             (0, 0, 1), (0, 1, 0),
                             length=0.26 * sc, width=0.18 * sc, rise=0.07 * sc))
    return out


# ============================================================================= CORNES
def horn_parts():
    """Grande paire frontale balayee vers l'ARRIERE par-dessus le cou (le bloc-tete en
    BELIER, lecture « dragon » nº1). Cornes EPAISSES a la base. Asymetrie voulue : la corne
    droite est ECHANCREE (pointe cassee) — une bete intacte lit « figurine neuve »."""
    # base sur le haut du crane (derriere l'arcade), sweep back+up over the neck
    pts = [[0.30, Y(196), Z(360)], [0.42, Y(214), Z(338)], [0.52, Y(244), Z(322)],
           [0.58, Y(282), Z(316)], [0.60, Y(320), Z(322)], [0.58, Y(352), Z(338)]]
    radii = [0.16, 0.135, 0.10, 0.066, 0.034, 0.010]
    out = []
    for side, suf, keep, tip_r in ((1, "_l", 6, 0.010), (-1, "_r", 4, 0.045)):
        out.append(tube_along("horn_main" + suf,
                              [[side * x, y, z] for x, y, z in pts[:keep]],
                              radii[:keep - 1] + [tip_r],
                              up=(1, 0, 0), subsurf=2, mat="bone", mirror_x=False,
                              miter=True))
    # petite paire a l'angle de la machoire (cornes de joue), mirror_x
    out.append(tube_along("horn_cheek",
                          [[0.30, Y(196), Z(452)], [0.36, Y(214), Z(446)],
                           [0.40, Y(236), Z(444)]],
                          [0.060, 0.038, 0.009],
                          up=(1, 0, 0), subsurf=2, mat="bone", mirror_x=True, miter=True))
    return out


# =========================================================== TETE : arcade, oeil, machoire
def head_parts():
    xe, ye, ze = on_skin(164, 0.33, out=0.84)      # oeil ENFONCE dans l'orbite (out bas)
    # arcade sourciliere = crete osseuse (tube a demi enfoui le long du haut de l'orbite),
    # lourde -> son ombre tombe dans l'oeil (le levier « regard qui pese »).
    # arcade LOURDE et qui FRONCE : elle avance sur l'avant de l'orbite (frac plus bas a
    # l'avant) -> un regard qui pese, plus dur/anguleux (anti-cartoon).
    brow_pts, brow_r = [], []
    for x_img, frac, r in ((140, 0.34, 0.052), (160, 0.22, 0.080),
                           (182, 0.15, 0.090), (206, 0.19, 0.058)):
        bx, by, bz = on_skin(x_img, frac, out=0.93)
        brow_pts.append([round(bx, 3), by, bz])
        brow_r.append(r)
    # crete NASALE osseuse sur l'axe du museau : casse le dome lisse en DEUX plans (anti-
    # cartoon — un crane dur a une arete mediane), et prolonge la ligne d'armure jusqu'au nez.
    ridge_pts = [list(on_skin(x, 0.0)) for x in (72, 104, 140, 176)]
    for p in ridge_pts:
        p[2] += 0.02
    return [
        tube_along("skull_ridge", ridge_pts, [0.028, 0.046, 0.050, 0.024],
                   up=(0, 0, 1), subsurf=2, mat="bone", mirror_x=False, miter=True),
        tube_along("brow", brow_pts, brow_r, up=(0, 0, 1), subsurf=2, mat="hide",
                   mirror_x=True, miter=True),
        # ARETE ZYGOMATIQUE (pommette osseuse) : de sous l'orbite vers l'angle de la
        # machoire. Elle plaque un PLAN DUR sur la joue desormais plate -> un crane
        # anatomique, pas une boite lisse.
        tube_along("cheek_ridge",
                   [list(on_skin(150, 0.46, out=0.99)), list(on_skin(178, 0.54, out=1.03)),
                    list(on_skin(206, 0.61, out=0.97))],
                   [0.026, 0.044, 0.030], up=(0, 0, 1), subsurf=2, mat="bone",
                   mirror_x=True, miter=True),
        # narines : 2 fentes aplaties sur le dessus du museau carre
        {"type": "globe", "id": "nostril", "mirror_x": True,
         "pos": [round(on_skin(94, 0.24, out=0.72)[0], 3), Y(94), Z(422)],
         "r": [0.040, 0.062, 0.026], "rot": [0, 0, -12], "mat": "hide_matte"},
        # oeil PETIT (r 0.10 sur un crane de ~2.5 u) : le rapport oeil/crane fait le GROS animal
        {"type": "globe", "id": "eye", "mirror_x": True,
         "pos": [round(xe, 3), ye, ze], "r": 0.10,
         "look_dir": [0.42, -0.86, 0.28], "mat": "eye"},
        # MASSE DE MACHOIRE (adducteurs) : cree le decrochement museau/crane et donne au
        # crane sa forme en coin vue de dessus. Sans elle : un seul fuseau lisse (« chausson »).
        {"type": "globe", "id": "jaw_mass", "mirror_x": True,
         "pos": [round(on_skin(198, 0.48, out=0.80)[0], 3), Y(198), Z(454)],
         "r": [0.085, 0.185, 0.125], "rot": [0, 0, 5], "mat": "hide"},
        # paupiere : un globe nu lit « bille collee » ; une plaque de peau qui mord dessus
        # l'inscrit dans le crane et durcit le regard.
        {"type": "globe", "id": "lid_up", "mirror_x": True,
         "pos": [round(xe - 0.02, 3), ye, round(ze + 0.075, 3)],
         "r": [0.075, 0.130, 0.055], "rot": [-15, 0, -7], "mat": "hide"},
    ]


# ------------------------------------------------------------ ligne de levre / commissure
# Altitude EXPLICITE qui descend vers l'arriere (une fraction constante ferait un SOURIRE :
# le crane se creuse vers l'arriere). Gueule fermee, lourde.
LIP = [(60, 468), (90, 471), (124, 474), (158, 476), (192, 476), (214, 470)]


def lip_frac(x_img):
    for (xa, ya), (xb, yb) in zip(LIP, LIP[1:]):
        if xa <= x_img <= xb:
            y = ya + (yb - ya) * (x_img - xa) / (xb - xa)
            break
    else:
        y = LIP[0][1] if x_img < LIP[0][0] else LIP[-1][1]
    yt, ybo, _ = station(x_img)
    return (y - yt) / max(ybo - yt, 1e-6)


LIP_XS = [64, 92, 124, 156, 188, 210]


def lip_part():
    """Sur une peau sombre, la bouche se voit par l'OMBRE d'un surplomb (levre superieure
    qui deborde), pas par la couleur. Materiau mat -> contraste par la rugosite."""
    rings = []
    for x_img in LIP_XS:
        f = lip_frac(x_img)
        xa, ya, za = on_skin(x_img, f - 0.08, out=1.0)
        xb, yb, zb = on_skin(x_img, f, out=1.0)
        xc, yc, zc = on_skin(x_img, f + 0.08, out=1.0)
        rings.append([
            (round(xa + 0.022, 4), ya, round(za + 0.008, 4)),   # haut, sorti
            (round(xb + 0.062, 4), yb, zb),                     # arete du surplomb
            (round(xc - 0.048, 4), yc, zc),                     # bas, rentre sous la peau
            (round(xa - 0.018, 4), ya, round(za - 0.006, 4)),   # retour interne
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


# --------------------------------------------------------------------------- crocs
# Peu nombreux, GROS et irreguliers (une rangee reguliere = « peigne »). ~8-10 % du crane.
# Une canine nettement plus longue ; un croc superieur CASSE (usure, comme la corne droite).
# Un croc superieur (128) et un inferieur (114) sont CASSES net (h ~0.026) : usure de combat,
# comme la corne droite. Une denture reguliere et intacte lit « figurine neuve ».
FANGS_UP = [(74, 0.078), (100, 0.140), (128, 0.026), (158, 0.124), (190, 0.092)]
FANGS_LO = [(86, 0.104), (114, 0.026), (144, 0.086), (176, 0.064)]


def fang_parts():
    """Gueule close -> les crocs se lisent forcement sur le COTE : on les sort lateralement
    (out > 1) et on les incline vers l'exterieur pour qu'ils percent la peau."""
    out = []
    for i, (x_img, h) in enumerate(FANGS_UP):
        x, y, z = on_skin(x_img, lip_frac(x_img) - 0.02, out=1.03)
        out.append({"type": "spike", "id": f"tooth_u{i}", "mirror_x": True,
                    "pos": [round(x, 3), y, round(z + 0.03, 3)], "dir": [0.40, -0.06, -1.0],
                    "height": h, "radius": round(h * 0.32, 3), "tip_frac": 0.03,
                    "seg": 10, "mat": "fang"})
    for i, (x_img, h) in enumerate(FANGS_LO):
        x, y, z = on_skin(x_img, lip_frac(x_img) + 0.09, out=1.03)
        out.append({"type": "spike", "id": f"tooth_l{i}", "mirror_x": True,
                    "pos": [round(x, 3), y, round(z - 0.03, 3)], "dir": [0.40, -0.10, 1.0],
                    "height": h, "radius": round(h * 0.32, 3), "tip_frac": 0.03,
                    "seg": 10, "mat": "fang"})
    return out


# =============================================================================== AILES
# Membrane TENDUE (une aile pliee est une impasse prouvee en b26/b27). Attache sur le DOS
# derriere les epaules (dragon a 6 membres : ailes SEPAREES des pattes avant). Envergure
# ~11.6 u pour un corps de 10 u : des ailes a la mesure de la masse.
W_ROOT = (0.55, -1.15, 3.25)      # racine sur le dos, derriere le garrot
ELBOW = (2.05, -1.95, 4.10)       # coude tendu vers l'exterieur et haut
WRIST = (3.70, -0.50, 4.55)       # poignet loin, aile ouverte
TIPS = [(4.95, -1.35, 4.30), (5.75, -0.15, 3.65), (5.80, 1.25, 2.70), (5.20, 2.65, 1.60)]
HIP = (0.90, 1.70, 1.95)          # attache arriere de la membrane, sur le flanc


def _rnd(a):
    """Pseudo-aleatoire deterministe [0,1) (meme graine -> meme dechirure a chaque build)."""
    x = math.sin(a * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


def web(pid, apex, edge_a, edge_b, notch=0.13, sag=0.30, nu=9, nv=8, mat="membrane",
        normal=None, crease=0.055, folds=2.5, drop=0.0, tatter=0.0, holes=()):
    """Panneau de membrane entre DEUX doigts, en grille (pas en polygone : une facette plane
    lit « origami »). Affaissement selon la GRAVITE + plis radiaux (crease/folds) + `drop`.

    v3 (feedback « ailes trop cartoon/chauve-souris lisse ») — deux mecanismes de DECHIRURE :
    - `tatter` (0..1) : le bord de fuite (u=1) est ronge IRREGULIEREMENT (rentre par des
      quantites pseudo-aleatoires par colonne) -> un drapeau dechiquete, pas un feston propre.
      Les doigts osseux (tubes poses sur les bords) RESSORTENT alors au-dela de la membrane.
    - `holes` : liste (uc, vc, ru, rv) en fractions de grille -> on SUPPRIME les faces dans
      ces ellipses = des TROUS francs (subsurf 0 : bords bruts, ca lit « membrane percee »)."""
    if normal is not None:
        n = list(normal)
    else:
        ea = [edge_a[k] - apex[k] for k in range(3)]
        eb = [edge_b[k] - apex[k] for k in range(3)]
        n = _norm([ea[1] * eb[2] - ea[2] * eb[1], ea[2] * eb[0] - ea[0] * eb[2],
                   ea[0] * eb[1] - ea[1] * eb[0]])
    if n[2] > 0:
        n = [-c for c in n]
    g = _norm([n[0] * 0.35, n[1] * 0.35, n[2] * 0.35 - 1.0])
    verts = []
    for j in range(nv + 1):
        v = j / nv
        far = [edge_a[k] + (edge_b[k] - edge_a[k]) * v for k in range(3)]
        scal = 1.0 - notch * math.sin(math.pi * v)
        if tatter:
            # le bord de fuite mange plus au MILIEU du panneau (les doigts le tiennent aux 2
            # bouts) ; variation par colonne pour une dechirure irreguliere
            scal *= 1.0 - tatter * (0.35 + 0.65 * math.sin(math.pi * v)) * _rnd(j * 1.7 + 0.5)
        rip = crease * math.sin(folds * 2.0 * math.pi * v) * math.sin(math.pi * v)
        for i in range(nu + 1):
            u = i / nu
            amp = sag * math.sin(math.pi * v) * u * u
            verts.append([round(apex[k] + (far[k] - apex[k]) * u * scal
                                + g[k] * amp + n[k] * (rip * (u ** 1.4) - drop), 4)
                          for k in range(3)])
    faces = []
    for j in range(nv):
        for i in range(nu):
            uc, vc = (i + 0.5) / nu, (j + 0.5) / nv
            if any(((uc - hu) / hru) ** 2 + ((vc - hv) / hrv) ** 2 < 1.0
                   for hu, hv, hru, hrv in holes):
                continue                                     # face supprimee = trou
            a = j * (nu + 1) + i
            faces.append([a, a + 1, a + nu + 2, a + nu + 1])
    return {"type": "cage", "id": pid, "mirror_x": True, "subsurf": 0,
            "mat": mat, "verts": verts, "faces": faces}


def wing_parts():
    nrm = _norm([(ELBOW[1] - W_ROOT[1]) * (TIPS[2][2] - W_ROOT[2])
                 - (ELBOW[2] - W_ROOT[2]) * (TIPS[2][1] - W_ROOT[1]),
                 (ELBOW[2] - W_ROOT[2]) * (TIPS[2][0] - W_ROOT[0])
                 - (ELBOW[0] - W_ROOT[0]) * (TIPS[2][2] - W_ROOT[2]),
                 (ELBOW[0] - W_ROOT[0]) * (TIPS[2][1] - W_ROOT[1])
                 - (ELBOW[1] - W_ROOT[1]) * (TIPS[2][0] - W_ROOT[0])])
    # Bord d'attaque : peu dechire (c'est la structure). Les inter-doigts et le grand pan
    # arriere, eux, sont EN LAMBEAUX (tatter) et PERCES (holes) — une aile de charognard qui
    # s'est battu. Trous et dechirures sont deterministes (graine dans _rnd).
    out = [web("wing_lead", ELBOW, W_ROOT, WRIST, notch=0.34, sag=0.06, nu=6, nv=6,
               normal=nrm, crease=0.02, folds=1.5, drop=0.06, tatter=0.10)]
    web_cfg = [(0.34, [(0.72, 0.50, 0.15, 0.24)]),
               (0.42, [(0.58, 0.32, 0.13, 0.20), (0.82, 0.72, 0.11, 0.16)]),
               (0.48, [(0.66, 0.55, 0.17, 0.26)])]
    for i, (a, b) in enumerate(zip(TIPS, TIPS[1:])):
        tat, hol = web_cfg[i]
        out.append(web(f"wing_web{i}", WRIST, a, b, sag=0.17, nu=12, nv=11, normal=nrm,
                       crease=0.05, folds=2.0 + 0.5 * i, drop=0.06, tatter=tat, holes=hol))
    out.append(web("wing_flank", WRIST, TIPS[3], HIP, notch=0.06, sag=0.32, nu=12, nv=13,
                   normal=nrm, crease=0.07, folds=3.0, drop=0.06, tatter=0.30,
                   holes=[(0.50, 0.38, 0.14, 0.18), (0.76, 0.70, 0.12, 0.16)]))
    out.append(tube_along("wing_arm", [list(W_ROOT), list(ELBOW), list(WRIST)],
                          [0.26, 0.185, 0.130], up=(0, 0, 1), subsurf=2, mat="hide",
                          mirror_x=True, miter=True))
    for i, tip in enumerate(TIPS):
        mid = [WRIST[k] + (tip[k] - WRIST[k]) * 0.5 for k in range(3)]
        mid[2] += 0.12
        # le doigt se PROLONGE en une petite griffe osseuse AU-DELA de la membrane rongee
        # (elle a recule sous tatter) -> les os saillants demandes.
        claw = [tip[k] + (tip[k] - mid[k]) * 0.28 for k in range(3)]
        claw[2] -= 0.06
        out.append(tube_along(f"wing_finger{i}", [list(WRIST), mid, list(tip), claw],
                              [0.130, 0.072, 0.028, 0.008], up=(0, 0, 1), subsurf=2,
                              mat="bone", mirror_x=True, miter=True))
    return out


# ================================================================= ORTEILS / GRIFFES
def foot_parts(prefix, x_off, x_ball, y_ball_img):
    """Pied LARGE a gros orteils ecartes (l'appui d'un poids lourd) + grosses griffes qui
    s'ancrent. mirror_x -> le pied de l'autre cote. Le pied avant et le pied arriere
    partagent la meme construction, a leurs abscisses respectives."""
    ball = [x_ball, Y(y_ball_img), Z(654)]
    # 3 orteils vers l'avant (-Y) ecartes + 1 ergot arriere
    toes = {f"toe_{prefix}_out": ([x_off + 0.18, Y(y_ball_img - 44), Z(654)]),
            f"toe_{prefix}_mid": ([x_off, Y(y_ball_img - 54), Z(654)]),
            f"toe_{prefix}_in": ([x_off - 0.16, Y(y_ball_img - 44), Z(654)])}
    out = []
    for pid, tip in toes.items():
        mid = [(ball[k] + tip[k]) / 2 for k in range(3)]
        mid[2] += 0.06
        out.append(tube_along(pid, [ball, mid, tip], [0.11, 0.078, 0.045],
                              up=(0, 0, 1), subsurf=2, mat="hide", mirror_x=True, miter=True))
    # ergot arriere (dewclaw)
    out.append(tube_along(f"toe_{prefix}_spur",
                          [[x_off, Y(y_ball_img + 20), Z(650)],
                           [x_off, Y(y_ball_img + 46), Z(656)]],
                          [0.060, 0.020], up=(0, 0, 1), subsurf=2, mat="hide",
                          mirror_x=True, miter=True))
    # GRIFFES : grosses, recourbees vers le sol devant chaque orteil avant
    claws = {f"claw_{prefix}_out": ([x_off + 0.18, Y(y_ball_img - 44), Z(654)],
                                    [x_off + 0.20, Y(y_ball_img - 84), Z(640)]),
             f"claw_{prefix}_mid": ([x_off, Y(y_ball_img - 54), Z(654)],
                                    [x_off, Y(y_ball_img - 96), Z(638)]),
             f"claw_{prefix}_in": ([x_off - 0.16, Y(y_ball_img - 44), Z(654)],
                                   [x_off - 0.18, Y(y_ball_img - 84), Z(640)])}
    for pid, (a, b) in claws.items():
        mid = [(a[k] + b[k]) / 2 for k in range(3)]
        mid[2] -= 0.03
        out.append(tube_along(pid, [a, mid, b], [0.070, 0.046, 0.010],
                              up=(0, 0, 1), subsurf=2, mat="claw", mirror_x=True, miter=True))
    return out


# =============================================================== BAVE ACIDE (signature)
def drool_parts():
    """Coulures de bave acide qui PENDENT de la machoire inferieure — la signature « poison »
    la plus lisible. Longueurs et positions IRREGULIERES (asymetriques, pas de mirror_x) :
    une bave reguliere lit « decoratif ». Materiau `acid` emissif -> elles luisent."""
    out = []
    for i, (x_img, ln) in enumerate([(96, 0.24), (140, 0.36), (188, 0.20), (118, 0.15)]):
        x, y, z = on_skin(x_img, lip_frac(x_img) + 0.10, out=1.0)
        top = [round(x, 3), y, round(z, 3)]
        bot = [round(x + 0.01, 3), round(y + 0.02, 3), round(z - ln, 3)]
        mid = [round((top[k] + bot[k]) / 2.0, 3) for k in range(3)]
        out.append(tube_along(f"drool_{i}", [top, mid, bot], [0.026, 0.015, 0.004],
                              up=(0, 0, 1), subsurf=2, mat="acid", mirror_x=False, miter=True))
    return out


# ==================================================================== materiaux
MATS = {
    # OS / corne / plaques : os TERNE et PATINE (pas de l'ivoire neuf, sinon les plaques
    # « popcorn » brillent trop et l'armure lit « bonbon »). Sombre-chaud, tres rugueux, avec
    # une racine encore plus sombre : l'armure d'une bete qui se bat, pas un trophee poli.
    # OS / cornes / plaques : os PATINE et CORRODE (vert-gris malade) — l'armure est rongee
    # par le poison de la bete elle-meme, comme la hide.
    "bone": {"builder": "enamel", "p": {
        "color": [0.27, 0.30, 0.205], "root_color": [0.09, 0.11, 0.07],
        "rough": 0.70, "sss": 0.04, "root_frac": 0.44}},
    "claw": {"builder": "enamel", "p": {
        "color": [0.155, 0.175, 0.105], "root_color": [0.055, 0.065, 0.04],
        "rough": 0.36, "sss": 0.03, "root_frac": 0.42}},
    # crocs TACHES (jaune-vert sale) : des dents qui macerent dans l'acide, pas de l'ivoire.
    "fang": {"builder": "enamel", "p": {
        "color": [0.47, 0.49, 0.31], "root_color": [0.20, 0.19, 0.10],
        "rough": 0.42, "sss": 0.06, "root_frac": 0.40}},
    # ACIDE : materiau EMISSIF vert (builder `eye`, simple emission) pour la bave et les
    # coulures qui luisent dans les fissures — la signature « poison » qu'on lit d'un coup.
    "acid": {"builder": "eye", "p": {"color": [0.35, 0.85, 0.16], "glow": 3.2}},
    # peau MATE (ligne de levre) : meme builder que `hide`, rugosite poussee, specular ecrase.
    "hide_matte": {"builder": "reptile_scales", "p": {
        "scale": 22, "scale2": 60, "bump": 0.06,
        "base": [0.020, 0.018, 0.016], "tint": [0.024, 0.020, 0.016],
        "rough": 0.76, "rough_edge": 0.60, "sss": 0.04, "micro": 0.06,
        "edge_copper": 0.0, "edge_width": 0.015, "instance_variation": 0.14,
        "patina_amount": 0.0, "spec_level": 0.07, "sheen": 0.0,
        "aniso": 0.0, "specular_tint": [0.86, 0.84, 0.80]}},
    # membrane : CUIR sombre, pas un voile rose. En fast (EEVEE/clay preview) la transmission
    # sur-eclaire l'aile en rose bonbon ; on la baisse a 0.10 et on ASSOMBRIT franchement la
    # nappe -> une membrane epaisse et coriace, a la mesure du Colosse. Le contre-jour l'allume
    # encore (le vrai « effet dragon ») mais sans cramer.
    # membrane RONGEE : cuir gris-vert malade, veines VERT-POISON marquees, tres ridee. La
    # transmission faible (0.10) l'allume a contre-jour en vert glauque (pas en rose).
    "membrane": {"builder": "membrane", "p": {
        "color": [0.035, 0.042, 0.028], "edge_color": [0.09, 0.13, 0.06],
        "rough": 0.62, "transmission": 0.10, "sss": 0.16,
        "sss_radius": [0.12, 0.18, 0.09],
        "vein_scale": 7.0, "vein_strength": 0.50, "vein_width": 0.036, "vein_bump": 0.62,
        "vein_dark": [0.06, 0.15, 0.05],
        "vein_radial_n": 5, "vein_radial_strength": 0.30, "vein_radial_width": 0.26,
        "wrinkle_scale": 20.0, "wrinkle_strength": 0.30}},
    # oeil : iris VERT-POISON luminescent + pupille fendue etroite. Le glow releve -> l'oeil
    # luit comme la bave : lecture « venimeux » immediate.
    "eye": {"builder": "eye_globe", "p": {
        "sclera_color": [0.040, 0.055, 0.030], "iris_color": [0.34, 0.62, 0.12],
        "iris_color2": [0.70, 0.95, 0.32], "pupil_color": [0.003, 0.006, 0.003],
        "pupil_width": 0.15, "pupil_length": 2.3, "pupil_edge": 0.012,
        "iris_r": 0.44, "rough": 0.11, "clearcoat": 0.12, "spec_level": 0.2,
        "glow": 0.16, "catchlight": 0.85, "catchlight_pos": [0.44, 0.40],
        "catchlight_size": 0.05, "catchlight_soft": 0.02}},
}


def main():
    path = os.path.join(ROOT, 'specs', 'dragon.json')
    spec = json.load(open(path))
    new = (plate_parts() + horn_parts() + head_parts() + fang_parts()
           + [lip_part()] + drool_parts() + wing_parts()
           + foot_parts("fore", 0.62, 0.62, 411) + foot_parts("hind", 0.70, 0.70, 701))
    by_id = {p['id']: p for p in spec['parts']}
    for p in new:
        by_id[p['id']] = p
    spec['parts'] = list(by_id.values())
    spec['materials'].update({k: v for k, v in MATS.items()
                              if k not in spec['materials']})
    with open(path, 'w') as f:
        json.dump(spec, f, indent=1)
    print(f"{len(new)} appendices fusionnes -> {len(spec['parts'])} parts")


if __name__ == '__main__':
    main()
