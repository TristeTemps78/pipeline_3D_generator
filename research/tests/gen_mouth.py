"""OUTIL b25 : IMPRIME le JSON de la part `mouth_line` (decalque de la ligne de bouche
sur la cage tete de Krokmou). N'ECRIT RIEN -- la spec reste editee a la main (piege
gen_krokmou_cage.py, qui lui ECRASE la spec). Relancer apres avoir touche aux anneaux
0-5 de body_cage, ou pour changer le trace / le decollement.

Methode : les 6 anneaux de tete de la cage donnent, par interpolation en Y, une section
(zt, zm, zb, demi-largeur w). La cage a ete construite avec GROW=1.06 autour de zm ->
la SURFACE lissee s'obtient en degonflant de 1/1.06. On evalue la section a la hauteur
voulue, puis on loft une petite section rectangulaire (bande fermee : `validate` veut
des volumes etanches) le long de la courbe de bouche, decollee vers l'exterieur.
"""
import json
import math

GROW = 1.06

# anneaux tete de specs/krokmou_cage.json : (y, zt, zm, zb, w) -- valeurs CAGE
RINGS = [
    (-1.988, 1.016, 0.882, 0.748, 0.223),   # bout du museau
    (-1.890, 1.204, 0.959, 0.714, 0.386),
    (-1.610, 1.537, 1.092, 0.647, 0.594),
    (-1.400, 1.654, 1.127, 0.600, 0.712),   # crane le plus large
    (-1.190, 1.655, 1.113, 0.571, 0.683),
    (-1.036, 1.676, 1.253, 0.830, 0.549),
]

# courbe de bouche : (y, z du centre de la bande) -- monte vers l'arriere, commissure
# JUSTE sous l'oeil (oeil : pos z 1.21, r 0.21 -> bas ~1.00). Le premier point est
# DEVANT le museau, sur l'axe (x=0) : le miroir X y referme la bande.
CURVE = [
    (-1.982, 0.884, True),   # pointe : sur l'axe, la normale regarde -Y (le museau
    (-1.972, 0.884, False),  # lisse s'arrete a y=-1.984, mesure par run.py inspect)
    (-1.952, 0.888, False),
    (-1.918, 0.897, False),
    (-1.870, 0.912, False),
    (-1.750, 0.938, False),
    (-1.620, 0.958, False),
    (-1.500, 0.968, False),
    (-1.400, 0.974, False),
    (-1.330, 0.978, False),
    (-1.280, 0.980, False),  # commissure (sous l'oeil : bas du globe a z~1.03 ici)
]

# Section de la bande : LEVRE EN SURPLOMB plutot que corniche symetrique (round 1 :
# une bande centree lisait « ledge » et se voyait a peine). Le bord HAUT ressort, le
# bord BAS replonge sous la peau -> l'ombre portee sous le surplomb DESSINE la ligne,
# et aucun bord ne flotte : sur du noir, le contraste vient de l'ombre, pas de l'albedo.
HW = 0.020         # demi-largeur de la bande (en z)
LIFT_UP = 0.020    # saillie du bord haut (levre)
LIFT_LO = -0.006   # bord bas : juste sous la peau
LIFT_IN = -0.030   # face interne (bande fermee, jamais visible)


def section(y):
    """(zt, zm, zb, w) de la SURFACE lissee, interpoles en y entre les anneaux."""
    ys = [r[0] for r in RINGS]
    y = max(min(y, ys[-1]), ys[0])
    for i in range(len(RINGS) - 1):
        if ys[i] <= y <= ys[i + 1]:
            f = (y - ys[i]) / (ys[i + 1] - ys[i])
            a, b = RINGS[i], RINGS[i + 1]
            zt, zm, zb, w = (a[k] + (b[k] - a[k]) * f for k in (1, 2, 3, 4))
            return zm + (zt - zm) / GROW, zm, zm - (zm - zb) / GROW, w / GROW
    a = RINGS[0]
    return a[1], a[2], a[3], a[4] / GROW


Y_CAP, Y_END = -1.900, -1.988   # arrondi du bout du museau (le subsurf ferme la cage
#                                 plate en calotte : la largeur tombe a 0 sur l'axe)


def cap_factor(y):
    if y >= Y_CAP:
        return 1.0
    s = min((Y_CAP - y) / (Y_CAP - Y_END), 1.0)
    return math.sqrt(max(0.0, 1.0 - s * s))


def half_width_at(y, z):
    """Demi-largeur de la surface a la hauteur z : polyligne de la section (le profil
    de l'anneau est [sommet, 0.75w a 65 % de la hauteur, w a mi-hauteur, ...])."""
    _, zm, zb, w = section(y)
    if z < zm:
        t = (zm - z) / max(zm - zb, 1e-6)
        w = w * (1.0 - 0.25 * t / 0.65) if t <= 0.65 else \
            0.75 * w * max(1.0 - (t - 0.65) / 0.35, 0.0)
    return w * cap_factor(y)


def frame(y, z, tip):
    """Point de surface p, normale sortante n, direction de largeur u (dans le plan de
    la section). Vers le bout du museau la normale bascule progressivement vers -Y
    (calotte), sinon elle est radiale dans la section."""
    x = 0.0 if tip else half_width_at(y, z)
    _, zm, _, _ = section(y)
    nx, nz = x, (z - zm)
    ln = math.hypot(nx, nz) or 1.0
    s = 0.0 if y >= Y_CAP else min((Y_CAP - y) / (Y_CAP - Y_END), 1.0)
    n = (nx / ln * (1 - s), -s, nz / ln * (1 - s))
    ln = math.sqrt(sum(c * c for c in n)) or 1.0
    n = tuple(c / ln for c in n)
    # u = z_hat orthogonalise par rapport a n
    d = n[2]
    ux, uy, uz = -n[0] * d, -n[1] * d, 1.0 - n[2] * d
    lu = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
    return (x, y, z), n, (ux / lu, uy / lu, uz / lu)


def build():
    verts, faces = [], []
    for y, z, tip in CURVE:
        p, n, u = frame(y, z, tip)
        ring = []
        for lift, s in ((LIFT_IN, 1), (LIFT_UP, 1), (LIFT_LO, -1), (LIFT_IN, -1)):
            ring.append([round(p[k] + n[k] * lift + u[k] * s * HW, 4) for k in range(3)])
        verts.extend(ring)
    n_st = len(CURVE)
    for r in range(n_st - 1):
        for j in range(4):
            a, b = r * 4 + j, r * 4 + (j + 1) % 4
            faces.append([a, b, b + 4, a + 4])
    if not CURVE[0][2]:   # station de tete SUR l'axe : le miroir (clip+merge) referme
        faces.append([3, 2, 1, 0])   # la bande devant le museau -> pas de bouchon ici,
    last = (n_st - 1) * 4            # sinon 2 ngons coincidents = arêtes non manifold.
    faces.append([last, last + 1, last + 2, last + 3])
    return {"type": "cage", "id": "mouth_line", "mirror_x": True, "subsurf": 0,
            "mat": "skin_matte", "verts": verts, "faces": faces}


if __name__ == '__main__':
    print(json.dumps(build()))
