"""OUTIL b29 : AMORCAGE de la cage 3D du Colosse -> ECRIT specs/dragon.json.

Meme role que gen_wyvern_cage.py : une fois lance, la spec devient LA SOURCE DE VERITE et
s'edite a la main. ATTENTION : le relancer ECRASE specs/dragon.json.

Lit le document de design (gen_dragon_trace.py) : stations BODY (x, y_haut, y_bas,
demi-largeur) + les deux chaines LEG_FORE / LEG_HIND. Le decalque 2D et la cage 3D partagent
donc le meme profil de PROFIL ; l'IoU mesure ensuite la derive propre a la 3D.

Reutilise `tube_along` de gen_appendages.py (brique b26) pour les 4 pattes.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from gen_appendages import tube_along  # noqa: E402
from gen_dragon_trace import BODY, LEG_FORE, LEG_HIND, S, X0, Y0  # noqa: E402

# Compensation du retrecissement subsurf (loi b27 : le Catmull-Clark rogne d'autant PLUS que
# la section est PETITE). Le Colosse a de GROSSES sections -> compensation faible et douce.
GROW_A, GROW_B = 1.012, 2.0   # grow = A + B/taille_px   (repris de la wyverne)


def _grow(size_px, cap=1.30):
    return min(GROW_A + GROW_B / max(size_px, 12.0), cap)
GROW_LEG = 1.18       # sections carrees 4 pts : le Catmull-Clark ronge bien plus
X_FORE = 0.62         # ecartement lateral des pattes AVANT (mirror_x -> la paire)
X_HIND = 0.70         # hanches un peu plus larges que les epaules : stance de bulldozer


def Y(x_img):
    return (x_img - X0) * S


def Z(y_img):
    return (Y0 - y_img) * S


# Profil de demi-section (moitie +X), en fractions de (demi-largeur, demi-hauteur). La
# wyverne utilisait un « squircle » MAIGRE (flancs plats, bete seche). Le Colosse veut
# l'inverse : un squircle PLEIN — flanc large tenu longtemps, ventro-laterale gonflee
# (masse musculaire), dos large. Un animal cuirasse est un BLOC, pas un tube maigre.
SECTION = [
    (0.00,  1.00),   # ligne dorsale
    (0.55,  0.95),   # dos LARGE et legerement bombe (les plaques osseuses iront dessus)
    (0.95,  0.66),   # arete dorso-laterale haute : elle attrape la lumiere
    (1.00,  0.05),   # flanc, point le plus large
    (0.96, -0.55),   # arete ventro-laterale PLEINE (le muscle deborde ici)
    (0.60, -0.90),   # ventre large
    (0.00, -1.00),   # ligne ventrale
]

# SECTION DE CRANE, CARREE (anti-cartoon, feedback « museau encore lisse »). Le corps est
# lofte avec un « squircle » rond -> une tete faite du meme profil rend en MUSEAU-BALLON. Un
# crane de brute est un BLOC : dessus PLAT, flancs quasi VERTICAUX, coins DURS, dessous plat.
# Meme nombre de points que SECTION (7) pour que le loft raccorde ; on la BLEND vers SECTION
# le long du cou. Le subsurf 2 arrondira un peu les coins, mais nettement moins qu'un ovale.
HEAD_SECTION = [
    (0.00,  1.00),   # dessus, centre
    (0.72,  0.99),   # dessus PLAT et large (table cranienne)
    (1.00,  0.82),   # COIN dorso-lateral DUR
    (1.00, -0.05),   # flanc quasi VERTICAL (joue plate)
    (1.00, -0.82),   # COIN ventro-lateral DUR (ligne de mandibule)
    (0.70, -0.99),   # dessous plat (menton carre)
    (0.00, -1.00),   # dessous, centre
]


def _blend_section(i):
    """Section de la station i : CRANE carre sur la tete (i<=9), transition sur le cou
    (10..13), squircle du corps ensuite. Coins durs du crane -> museau blocky, pas ballon."""
    t = max(0.0, min(1.0, (i - 9) / 5.0))
    return [(hx + (bx - hx) * t, hz + (bz - hz) * t)
            for (hx, hz), (bx, bz) in zip(HEAD_SECTION, SECTION)]


# MUSCULATURE (le vrai sujet du Colosse, cf. dragon_ref.md). Le decalque de PROFIL n'a
# qu'UN degre de largeur ; le muscle est un renflement LOCALISE et non radial. Plutot que des
# blobs boulonnes (qui rendent en oeufs, cf. HANDOFF), on POUSSE certains secteurs de la
# section a certaines stations -> le muscle vit DANS la peau, une seule surface subsurf.
# `bulge[station_index] = { secteur_SECTION : (mult_largeur, ajout_z_frac) }`.
# Secteurs SECTION : 0 dorsale, 1 dos, 2 dorso-laterale, 3 FLANC, 4 ventro-laterale,
# 5 ventre, 6 ventrale. Invisible de PROFIL (largeur = X) -> ne bouge pas le score de silhouette.
S17, S18 = 17, 18   # thorax (pectoraux)
# b31 etape 1 : le RELIEF etait lisible en largeur (X) mais invisible de 3/4 -> pas de
# CONTRASTE bosse/creux ni d'ARETE qui accroche la lumiere. On alterne desormais PIC (masse
# musculaire, mult >1 + dz asymetrique haut>bas = meplat/arete) et CREUX (sillon, mult <1)
# entre les groupes, au lieu d'un gonflement monotone.
MUSCLE = {
    14: {2: (1.10, 0.02), 3: (1.16, 0.0)},          # deltoide (cap d'epaule), amorce
    15: {2: (1.17, 0.05), 3: (1.24, 0.02), 4: (1.08, -0.01)},   # deltoide PIC + arete haute
    16: {2: (0.95, 0.0), 3: (0.94, 0.0), 4: (0.96, 0.0)},       # SILLON post-scapulaire (creux)
    S17: {2: (0.97, 0.0), 3: (0.95, 0.0), 4: (1.05, -0.01)},    # le creux se referme vers le pectoral
    S18: {2: (1.11, 0.04), 3: (1.19, 0.01), 4: (1.19, -0.02), 5: (1.12, 0.0)},  # pectoral PIC + arete
    21: {3: (0.94, 0.0), 4: (0.93, 0.0)},           # CREUX du flanc, avant la masse de cuisse
    22: {2: (0.97, 0.0), 3: (0.95, 0.0), 4: (0.96, 0.0)},       # creux se prolonge, amorce hanche
    23: {2: (1.17, 0.05), 3: (1.27, 0.02), 4: (1.10, -0.01)},   # biceps femoral PIC + arete haute
    24: {2: (1.12, 0.03), 3: (1.18, 0.01), 4: (1.10, -0.01)},   # cuisse, taper + arete
}


def half_ring(x_img, yt, yb, w_px, bulge=None, section=SECTION):
    """Demi-section (moitie +X). Le subsurf + mirror_x en font une peau continue.
    `bulge` (optionnel) : renflements musculaires par secteur (voir MUSCLE).
    `section` : profil de section (SECTION corps, ou crane carre blende, cf. _blend_section)."""
    y = Y(x_img)
    zt, zb = Z(yt), Z(yb)
    zm = (zt + zb) / 2.0
    hz = (zt - zb) / 2.0 * _grow(yb - yt)
    w = w_px * S * _grow(2 * w_px)
    ring = []
    for si, (fx, fz) in enumerate(section):
        mw, dz = bulge.get(si, (1.0, 0.0)) if bulge else (1.0, 0.0)
        ring.append((fx * w * mw, y, zm + (fz + dz) * hz))
    return ring


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
    verts, faces = loft([half_ring(*st, bulge=MUSCLE.get(i), section=_blend_section(i))
                         for i, st in enumerate(BODY)])
    return {"type": "cage", "id": "body_cage", "mirror_x": True, "subsurf": 2,
            "mat": "hide", "verts": verts, "faces": faces}


def _extend(chain, i_from, i_to, k):
    """Prolonge la chaine au-dela de i_to en extrapolant i_from->i_to. ENFOUIT les capuchons
    du tube (le subsurf les rentre) : le bout de tube tombe dans le corps / sous le sol."""
    ax, ay, ar = chain[i_from]
    bx, by, br = chain[i_to]
    return (bx + (bx - ax) * k, by + (by - ay) * k, br)


def leg_part(pid, chain, x_off):
    """Une patte COLONNE : tube_along sur une chaine LEG du document de design.
    mirror_x -> la paire, superposee de profil (pose plantee symetrique). Sections carrees
    epaisses -> le subsurf les arrondit en colonne graviportante."""
    ext = [_extend(chain, 1, 0, 0.55)] + list(chain) + [_extend(chain, -2, -1, 0.45)]
    pts = [[x_off, Y(x), Z(y)] for x, y, _ in ext]
    radii = [r * S * GROW_LEG for _, _, r in ext]
    return tube_along(pid, pts, radii, up=(0, 1, 0), subsurf=2, mat="hide",
                      mirror_x=True, miter=True)


def main():
    # SOL : sans lui la bete flotte, perd son echelle et son ombre portee ("figurine").
    # C'est le CONTACT (pieds + ombre) qui fait le poids.
    ground = {"type": "ground", "id": "ground", "size": 90, "mat": "rock"}
    parts = [body_part(),
             leg_part("leg_fore", LEG_FORE, X_FORE),
             leg_part("leg_hind", LEG_HIND, X_HIND),
             ground]
    spec = {
        "name": "dragon",
        "ref": "Le Colosse (conception maison, 2026-07-23) : dragon occidental quadrupede, "
               "cuirasse, grosse musculature. Reference = references/dragon_ortho_side.png, "
               "notre propre decalque (voir references/dragon_ref.md). Spec de DEV : editee "
               "a la main apres cet amorcage. Chaine : trace -> cage -> parts.",
        "materials": {
            # HIDE de PIERRE sombre (basalte/obsidienne) a grosses ecailles. `scale` est en
            # CELLULES PAR UNITE MONDE (piege paye 3 rounds sur la wyverne) : ~12 = plaques
            # de ~8 cm sur une bete de 10 m, ca se lit ; le bump doit etre FRANC (~1.2).
            # BASE volontairement NEUTRE-SOMBRE (pas une couleur d'espece figee) : le jeu
            # aval veut re-teinter pour decliner une famille -> b30 exposera `base` en
            # parametre. Ici on garde un gris-pierre chaud qui accepte n'importe quel teint.
            # SPECIALITE = POISON / CORROSION. La hide est une cuirasse RONGEE : peau
            # gris-vert malade + `patina` (le systeme de verdigris du builder, pense « oxyde
            # de cuivre ») pousse a fond en vert acide dans les creux/aretes -> l'armure
            # semble attaquee par sa propre bave. bump releve = surface PIQUEE (corrosion),
            # pas lisse. Base neutre-sombre encore re-teintable pour la famille (b30).
            "hide": {"builder": "reptile_scales", "p": {
                "scale": 12, "scale2": 34, "bump": 1.45,
                "base": [0.026, 0.030, 0.022], "tint": [0.070, 0.082, 0.050],
                "rough": 0.74, "rough_edge": 0.34, "sss": 0.05,
                "sss_radius": [0.10, 0.13, 0.07], "micro": 0.55,
                "edge_copper": 0.06, "edge_width": 0.016, "instance_variation": 0.28,
                "patina_amount": 0.55, "patina_color": [0.11, 0.22, 0.09],
                "patina_gold": [0.26, 0.30, 0.09], "spec_level": 0.18, "sheen": 0.04,
                "aniso": 0.03, "specular_tint": [0.86, 0.92, 0.80]}},
            "rock": {"builder": "rock", "p": {
                "color": [0.10, 0.095, 0.088], "scale": 1.2, "bump": 0.9,
                "burnt": [0.055, 0.05, 0.045], "ember": [0.16, 0.145, 0.13]}},
        },
        "parts": parts,
        "scene": {
            # CONTRE-PLONGEE 3/4 AVANT, tres bas : l'objectif SOUS la ligne des yeux fait
            # dominer la masse. Le Colosse regarde -Y ; on le prend de l'avant (+X, -Y),
            # a hauteur de poitrail. HQ a raffiner en passe LOOK.
            "camera": {"loc": [6.7, -12.6, 2.0], "target": [0.0, -0.4, 1.95],
                       "lens": 44, "fstop": 5.0},
            "silh": {"ref": "references/dragon_ortho_side.png", "axis": "side",
                     "ortho_scale": 12.0, "target": [0.0, 0.0, 1.9],
                     "exclude_like": ["wing", "horn", "tooth", "plate_", "ridge",
                                      "brow", "mouth_", "claw", "toe", "spur"]},
            # Low-key mais NEUTRE (pierre, pas glace) : fond presque noir, la bete decoupee
            # par des contre-jours. Un eclairage a plat transforme une peau sombre en tache.
            "world": {"color": [0.016, 0.015, 0.014], "color_top": [0.045, 0.043, 0.040],
                      "strength": 0.16, "visible_strength": 0.85},
            # SOLEIL BAS et RASANT : l'ombre longue et le modele. Teinte neutre-chaude.
            "sun": {"direction": [-0.40, 0.68, -0.36], "energy": 4.4,
                    "color": [1.0, 0.95, 0.88], "angle_deg": 1.4},
            "area_lights": [
                {"loc": [5.4, -7.2, 3.2], "target": [-0.4, -1.2, 1.9], "energy": 300,
                 "size": 2.6, "color": [1.0, 0.95, 0.88]},       # key chaude, DISCRETE (le
                #     soleil rasant modele la masse ; une key trop forte cramait l'aile en tan)
                {"loc": [-4.6, 6.2, 3.8], "target": [0.0, 0.4, 2.3], "energy": 2200,
                 "size": 1.6, "color": [0.78, 0.85, 1.0]},       # rim froid DUR (decoupe le dos)
                {"loc": [6.2, 4.8, 2.8], "target": [1.6, 1.0, 2.1], "energy": 2800,
                 "size": 2.0, "color": [0.88, 0.91, 1.0]},       # rim froid, croupe/aile/queue
                {"loc": [-5.2, -6.5, 2.2], "target": [0.0, -1.2, 1.8], "energy": 105,
                 "size": 7.5, "color": [0.70, 0.76, 0.92]},      # fill : pas de noir mort
            ],
            "shots": [
                {"id": "hero"},
                {"id": "head", "frame_match": "eye_", "margin": 2.8,
                 "dir": [0.82, -1.0, 0.10], "lens": 80, "fstop": 2.4},
                {"id": "wide", "frame_match": "body_cage", "margin": 1.28,
                 "dir": [0.55, -1.0, 0.12], "lens": 45},
            ],
            "render": {"device": "AUTO", "samples": 48, "denoise": True,
                       "adaptive_threshold": 0.02, "max_bounces": 6,
                       "diffuse_bounces": 3, "glossy_bounces": 3, "volume_bounces": 0,
                       "clamp_indirect": 4.0, "fast_sss": True},
        },
    }
    out = os.path.join(ROOT, 'specs', 'dragon.json')
    with open(out, 'w') as f:
        json.dump(spec, f, indent=1)
    print("cage :", {p["id"]: len(p.get("verts", ())) for p in parts})
    print("ecrit", out)


if __name__ == '__main__':
    main()
