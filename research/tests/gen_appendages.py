"""OUTIL b26 : IMPRIME le JSON des appendices cage de Krokmou (ailerons caudaux, ailes,
bras d'aile). N'ECRIT RIEN dans la spec (meme regle que gen_mouth.py).

Deux helpers reutilisables, volontairement generiques :
  plate(outline, thickness)  : polygone 3D ferme -> plaque EPAISSE etanche (extrusion
                               le long de la normale du polygone, calcul de Newell) ;
                               c'est la brique « membrane/aileron » de la methode cage.
  tube_along(pts, radii)     : polyligne -> tube ferme a sections carrees (4 pts) ;
                               brique « os/bras », subsurf le rend rond.
Les deux rendent des dicts de part `cage` prets a coller dans specs/krokmou_cage.json.
"""
import json
import math


def _norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def _newell(pts):
    """Normale d'un polygone 3D quelconque (robuste aux points non coplanaires)."""
    nx = ny = nz = 0.0
    for i, (x1, y1, z1) in enumerate(pts):
        x2, y2, z2 = pts[(i + 1) % len(pts)]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return _norm((nx, ny, nz))


def plate(pid, outline, thickness=0.06, subsurf=1, mat='scales_body', mirror_x=False,
          normal=None):
    n = normal or _newell(outline)
    h = thickness / 2.0
    top = [[round(p[k] + n[k] * h, 4) for k in range(3)] for p in outline]
    bot = [[round(p[k] - n[k] * h, 4) for k in range(3)] for p in outline]
    m = len(outline)
    verts = top + bot
    faces = [list(range(m)), [m + i for i in reversed(range(m))]]
    for i in range(m):
        j = (i + 1) % m
        faces.append([j, i, m + i, m + j])
    return {"type": "cage", "id": pid, "mirror_x": mirror_x, "subsurf": subsurf,
            "mat": mat, "verts": verts, "faces": faces}


def tube_along(pid, pts, radii, up=(0, 0, 1), subsurf=2, mat='scales_body',
               mirror_x=False):
    """Sections carrees perpendiculaires a la polyligne (repere de Frenet simplifie :
    tangente + `up` de reference) -> tube ferme. 4 pts/section : le subsurf arrondit."""
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = _norm([b[k] - a[k] for k in range(3)])
        s = _norm([t[1] * up[2] - t[2] * up[1], t[2] * up[0] - t[0] * up[2],
                   t[0] * up[1] - t[1] * up[0]])
        u = _norm([s[1] * t[2] - s[2] * t[1], s[2] * t[0] - s[0] * t[2],
                   s[0] * t[1] - s[1] * t[0]])
        r = radii[i]
        rx, ry = (r, r) if isinstance(r, (int, float)) else r
        rings.append([[round(p[k] + s[k] * rx * sx + u[k] * ry * sy, 4) for k in range(3)]
                      for sx, sy in ((1, 1), (1, -1), (-1, -1), (-1, 1))])
    verts = [v for r in rings for v in r]
    faces = [[3, 2, 1, 0]]
    for r in range(len(rings) - 1):
        for j in range(4):
            a, b = r * 4 + j, r * 4 + (j + 1) % 4
            faces.append([a, b, b + 4, a + 4])
    last = (len(rings) - 1) * 4
    faces.append([last, last + 1, last + 2, last + 3])
    return {"type": "cage", "id": pid, "mirror_x": mirror_x, "subsurf": subsurf,
            "mat": mat, "verts": verts, "faces": faces}


# ---------------------------------------------------------------- Krokmou b26
# Queue : bout a y=2.142, z~0.08, demi-largeur 0.074 (anneau 19 de body_cage).
# Ailerons TERMINAUX quasi horizontaux, legerement releves et balayes vers l'arriere.
# Cote DROIT de la creature (elle regarde -Y, donc sa droite = -X) = PROTHESE rouge.
FIN = [
    (0.05, 1.780, 0.065),   # racine avant
    (0.42, 1.850, 0.190),
    (1.12, 1.990, 0.365),   # pointe avant
    (1.30, 2.320, 0.430),   # pointe arriere
    (0.56, 2.390, 0.255),
    (0.05, 2.270, 0.100),   # racine arriere
]

# Aile droite/+X. Round 1 : trop redressee + festons trop mous = « oreilles d'elephant ».
# Round 2 : bord d'attaque presque droit epaule->poignet->POINTE loin en arriere, creux
# de membrane PROFONDS entre les doigts, racine plus basse (flanc, pas sommet du dos).
WING = [
    (0.40, -0.45, 1.58),    # racine du bord d'attaque (epaule)
    (1.25, -0.35, 1.92),    # coude
    (2.05, 0.10, 2.02),     # poignet
    (3.05, 0.75, 1.98),     # POINTE (doigt 1)
    (2.71, 1.02, 1.78),     # creux de membrane (voir CREUX ci-dessous)
    (2.55, 1.55, 1.52),     # doigt 2
    (2.25, 1.60, 1.39),     # creux
    (2.00, 2.05, 1.10),     # doigt 3
    (1.29, 1.47, 1.11),     # creux
    (0.42, 1.20, 0.92),     # racine du bord de fuite (hanche)
]
# Rotation d'ensemble autour de la racine (axe Z) : en balayage arriere trop marque,
# l'aile COTE CAMERA disparait derriere le corps au 3/4. -18 deg = ailes plus ouvertes,
# les deux lisent dans le meme cadre. La forme de la membrane, elle, ne change pas.
SWEEP = -18.0


def _sweep(pts, deg=SWEEP):
    a = math.radians(deg)
    cx, cy = pts[0][0], pts[0][1]
    out = []
    for x, y, z in pts:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * math.cos(a) - dy * math.sin(a),
                    cy + dx * math.sin(a) + dy * math.cos(a), z))
    return out


# Diedre : les racines restent collees au flanc, tout le reste monte -> la membrane
# passe AU-DESSUS de la ligne de dos au lieu de la traverser (lecture brouillonne au 3/4).
WING = [(x, y, z + (0.0 if i in (0, len(WING) - 1) else 0.26))
        for i, (x, y, z) in enumerate(_sweep(WING))]
ARM = [WING[0], WING[1], WING[2], WING[3]]
ARM_R = [0.19, 0.135, 0.09, 0.03]
# CREUX : le festonnage ne peut pas etre plus PROFOND que la corde poignet->pointe
# suivante, sinon le doigt (segment droit) sort de la membrane (round 3 : des aiguilles
# depassaient). Regle : creux = milieu des 2 pointes voisines, tire de ~12 % vers le
# poignet — concave mais toujours en dehors des doigts.
# Doigts : ce sont EUX qui font lire « aile de chauve-souris » plutot que « palette ».
FINGERS = [(WING[2], WING[5]), (WING[2], WING[7])]
FINGER_R = [0.065, 0.022]


def build():
    out = [
        # subsurf 0 sur les plaques fines (lecon b24) : le Catmull-Clark RETRECIT le
        # contour -> festons avales et doigts qui depassent de la membrane (round 2).
        plate('tail_fin_l', FIN, thickness=0.07, subsurf=0, mat='scales_body'),
        plate('tail_fin_r', [(-x, y, z) for x, y, z in FIN], thickness=0.07, subsurf=0,
              mat='prosthesis'),
        plate('wing', WING, thickness=0.055, subsurf=0, mat='membrane', mirror_x=True),
        tube_along('wing_arm', ARM, ARM_R, subsurf=2, mat='scales_body', mirror_x=True),
    ]
    for i, (a, tip) in enumerate(FINGERS):
        b = tuple(a[k] + (tip[k] - a[k]) * 0.93 for k in range(3))  # rester DANS la membrane
        mid = tuple((a[k] + b[k]) / 2 for k in range(3))
        out.append(tube_along(f'wing_finger{i}', [a, mid, b],
                              [FINGER_R[0], (FINGER_R[0] + FINGER_R[1]) / 2, FINGER_R[1]],
                              subsurf=2, mat='scales_body', mirror_x=True))
    return out


if __name__ == '__main__':
    print(json.dumps(build())[:400])
