"""ARCHIVE b24 : generateur d'AMORCAGE de la cage Krokmou (v8, IoU 0.9031).
La spec specs/krokmou_cage.json est DESORMAIS LA SOURCE DE VERITE (editee a la main,
vertex-level) : ne relancer ce script que pour repartir de zero -- il ECRASE la specAmorcage cage Krokmou v1 (b24 P0-C) : anneaux de sections le long du profil FIGE
(PTS_V4, krokmou_silh_trace.txt), moitie +X (mirror_x), gelee dans specs/krokmou_cage.json.
Stations = lectures manuelles du polygone (top/bottom CORPS SEUL sans oreilles/pattes,
dos x 208-250 = interpole sous l'aile comme dans le masque). Largeurs = anatomie estimee
(pas de vue face) : tete large/plate, cou plus etroit, epaules larges, queue fine.
v2 : + 4 pattes individuelles (pose de marche de la ref, qui n'est pas une vraie ortho :
les pattes lointaines sont decalees en Y) + paire d'oreilles miroir + museau carre +
queue affinee."""
import json

S = 0.014          # px -> unites Blender (corps ~4 u de long)
X0, Y0 = 200, 301  # origine : x_img 200 -> Y=0 ; sol image y=301 -> Z=0

# (x_img, y_top, y_bot, demi-largeur px)
STATIONS = [
    (58,  229, 247, 15),   # bout du museau (carre : 2 stations proches)
    (65,  216, 249, 26),
    (85,  193, 253, 40),
    (100, 185, 256, 48),   # crane large et plat
    (115, 185, 258, 46),
    (126, 183, 240, 37),
    (132, 181, 244, 36),   # jonction tete-cou
    (150, 173, 251, 30),   # cou
    (165, 162, 260, 34),
    (185, 159, 268, 40),   # poitrail profond
    (207, 155, 266, 44),   # epaules (le plus large)
    (228, 193, 272, 42),   # dos interpole sous l'aile
    (245, 241, 276, 36),
    (262, 254, 286, 30),   # hanches
    (285, 256, 294, 24),
    (300, 258, 296, 17),
    (315, 284, 299, 11),   # la queue plonge
    (332, 288, 301, 8),
    (347, 289, 300, 6),
    (353, 290, 300, 5),    # coupe avant ailerons (bout franc)
]


def Y(x_img):
    return round((x_img - X0) * S, 3)


def Z(y_img):
    return round((Y0 - y_img) * S, 3)


GROW = 1.06  # compensation du retrecissement subsurf (mesure : sommet cage -> surface lissee)


def half_ring(x_img, yt, yb, w_px):
    y = (x_img - X0) * S
    zt, zb = (Y0 - yt) * S, (Y0 - yb) * S
    zm = (zt + zb) / 2.0
    zt, zb = zm + (zt - zm) * GROW, zm - (zm - zb) * GROW
    w = w_px * S * GROW
    return [
        (0.0, y, zt),
        (0.75 * w, y, zm + 0.65 * (zt - zm)),
        (w, y, zm),
        (0.75 * w, y, zm - 0.65 * (zm - zb)),
        (0.0, y, zb),
    ]


def loft(rings, close=True):
    """Quads entre anneaux successifs (meme cardinal) + caps ngon aux extremites."""
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
    return [[round(c, 3) for c in v] for v in verts], faces


def body_part():
    rings = [half_ring(*st) for st in STATIONS]
    verts, faces = loft(rings, close=False)
    return {"type": "cage", "id": "body_cage", "mirror_x": True, "subsurf": 2,
            "mat": "scales_body", "verts": verts, "faces": faces}


def full_ring(cx, cy, cz, rx, ry):
    """Section HORIZONTALE (plan XY) 6 points a hauteur cz — les pattes sont des tubes
    verticaux : sections empilees en Z (le bug v2 posait des cerceaux verticaux -> ruban)."""
    import math
    pts = []
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a), cz))
    return pts


def leg_part(pid, x_off, x_center_img, w_px, forward_toe=9):
    """Patte trapue verticale : hanche enfouie -> genou -> cheville -> pied elargi vers
    l'avant (-Y). Sections horizontales, mirror_x False (pose de marche asymetrique)."""
    y = (x_center_img - X0) * S
    w = w_px * S * GROW * 1.2  # tubes 6 pts : le subsurf 2 retrecit bien plus que le corps
    toe = -forward_toe * S
    rings = [
        full_ring(x_off, y, Z(252), 1.15 * w, 1.5 * w),               # hanche (enfouie)
        full_ring(x_off, y, Z(272), 1.0 * w, 1.25 * w),               # cuisse/genou
        full_ring(x_off, y + 0.03, Z(290), 0.8 * w, 0.95 * w),        # cheville
        full_ring(x_off, y + toe * 0.4, Z(296), 0.95 * w, 1.25 * w),  # cou-de-pied
        full_ring(x_off, y + toe * 0.8, Z(302), 1.05 * w, 1.35 * w),  # orteils au sol
    ]
    verts, faces = loft(rings, close=True)
    return {"type": "cage", "id": pid, "mirror_x": False, "subsurf": 2,
            "mat": "scales_body", "verts": verts, "faces": faces}


def ears_part():
    """Paire d'oreilles (miroir X) : plaque conique base crane -> pointe arriere-haut.
    La ref montre 2 bosses (paire vraie decalee par la quasi-ortho) : on vise le milieu."""
    base_y0, base_y1, base_z = Y(104), Y(137), Z(196)
    tip_y0, tip_y1, tip_z = Y(114), Y(130), Z(168)
    x_base, x_tip, th = 0.18, 0.26, 0.09
    rings = [
        [(x_base - th, base_y0, base_z), (x_base + th, base_y0, base_z),
         (x_base + th, base_y1, base_z), (x_base - th, base_y1, base_z)],
        [(x_tip - th, tip_y0, tip_z), (x_tip + th, tip_y0, tip_z),
         (x_tip + th, tip_y1, tip_z), (x_tip - th, tip_y1, tip_z)],
    ]
    verts, faces = loft(rings, close=True)
    return {"type": "cage", "id": "ears", "mirror_x": True, "subsurf": 0,
            "mat": "scales_body", "verts": verts, "faces": faces}


def tail_ridge_part():
    """Crete dorsale de la queue (masque : y 259-283, x 300-337, encoche de fond dessous) :
    plaque fine ancree dans le haut de la queue."""
    th = 0.03
    rings = [
        [(-th, Y(302), Z(285)), (th, Y(302), Z(285)), (th, Y(334), Z(265)), (-th, Y(334), Z(265))],
        [(-th, Y(300), Z(260)), (th, Y(300), Z(260)), (th, Y(336), Z(261)), (-th, Y(336), Z(261))],
    ]
    verts, faces = loft(rings, close=True)
    return {"type": "cage", "id": "tail_ridge", "mirror_x": False, "subsurf": 0,
            "mat": "scales_body", "verts": verts, "faces": faces}


parts = [
    body_part(),
    tail_ridge_part(),
    leg_part("leg_front_far", -0.30, 112, 11, forward_toe=9),
    leg_part("leg_front_near", 0.30, 180, 15),
    leg_part("leg_hind_far", -0.33, 243, 13, forward_toe=6),
    leg_part("leg_hind_near", 0.33, 239, 13, forward_toe=6),
    ears_part(),
]
total = sum(len(p["verts"]) for p in parts)
print("cage :", {p["id"]: len(p["verts"]) for p in parts}, f"total {total} verts")

spec_full = json.load(open(r"C:\Git project\pipeline_3D_generator\specs\krokmou.json"))
spec = {
    "name": "krokmou_cage",
    "ref": "Cage sculpteur v1 (b24) : corps+cou+tete+queue UNE SEULE PEAU + 4 pattes "
           "posees (marche) + oreilles, jugee au score silhouette (run.py silh) contre "
           "references/krokmou_ortho_side_body.png. Spec de DEV : fusionnee dans "
           "krokmou.json une fois le jalon IoU atteint.",
    "materials": {"scales_body": spec_full["materials"]["scales_body"]},
    "parts": parts,
    "scene": {
        "camera": {"loc": [5.5, -5.5, 2.4], "target": [0, 0, 1.0], "lens": 40},
        "silh": {"ref": "references/krokmou_ortho_side_body.png",
                 "axis": "side", "ortho_scale": 8.0},
    },
}
out = r"C:\Git project\pipeline_3D_generator\specs\krokmou_cage.json"
with open(out, "w") as f:
    json.dump(spec, f, indent=1)
print("ecrit", out)
