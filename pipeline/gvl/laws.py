"""GVL — lois de croissance mathématiques. Fonctions pures, sans bpy.
Chaque loi retourne des points 3D ou des profils scalaires normalisés."""
import math

PHI = (1 + 5 ** 0.5) / 2
GOLDEN_ANGLE = math.radians(137.507764)


def log_spiral(a=0.06, b=0.22, turns=1.6, n=24, rise=0.35, pitch=0.0):
    """Spirale logarithmique r=a·e^(bθ) (cornes, griffes, coquilles).
    Points dans le plan local Y-Z, montée le long de -Y (vers l'arrière), rise = élévation."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        th = t * turns * 2 * math.pi
        r = a * math.exp(b * th)
        y = -r * math.cos(th) + a
        z = r * math.sin(th) + t * rise
        pts.append((0.0, y, z + t * pitch))
    return pts


def power_taper(n, r0=1.0, k=1.4, rmin=0.02):
    """Allométrie : r(t)=r0·(1-t)^k. Profil de rayons pour membres/queues."""
    return [max(rmin, r0 * (1 - i / (n - 1)) ** k) for i in range(n)]


def catenary(u, tension=2.2):
    """Affaissement de membrane suspendue, normalisé : 0 aux extrémités, 1 au centre."""
    c = math.cosh(tension)
    return (c - math.cosh(tension * (2 * u - 1))) / (c - 1)


def phyllotaxis(n, spread=1.0):
    """Disposition en angle d'or (écailles, pointes, graines). Points 2D (x,y)."""
    pts = []
    for i in range(n):
        r = spread * math.sqrt(i / n)
        th = i * GOLDEN_ANGLE
        pts.append((r * math.cos(th), r * math.sin(th)))
    return pts


def decay_series(n, base=1.0, ratio=0.82):
    """Série géométrique décroissante (tailles de pointes dorsales, phalanges)."""
    return [base * ratio ** i for i in range(n)]


def sample_path(pts, t):
    """Échantillonne une polyligne de contrôle à une fraction continue t (0..1),
    interpolation linéaire par segment. Brique de base du concept `attachment_curve`
    (doctrine v1 axe 2) : une pièce s'attache le long d'une courbe paramétrique sur
    la surface parente au lieu d'un point unique (aile<->flanc, corne<->arcade...).
    Contrairement à `lerp_path` (ré-échantillonne en n points ALIGNÉS), `sample_path`
    donne un point pour un t arbitraire — utile quand plusieurs éléments (colonnes de
    membrane, lattes) doivent suivre la même courbe à des fractions différentes."""
    n = len(pts) - 1
    if n <= 0:
        return tuple(pts[0])
    pos = min(max(t, 0.0), 1.0) * n
    i = min(int(pos), n - 1)
    f = pos - i
    a, b = pts[i], pts[i + 1]
    return tuple(a[k] + (b[k] - a[k]) * f for k in range(3))


def lerp_path(pts, n):
    """Ré-échantillonne une polyligne de contrôle en n points (interp. linéaire)."""
    if n <= len(pts):
        return list(pts)
    out = []
    seg = len(pts) - 1
    for i in range(n):
        t = i / (n - 1) * seg
        j = min(int(t), seg - 1)
        f = t - j
        a, b = pts[j], pts[j + 1]
        out.append(tuple(a[k] + (b[k] - a[k]) * f for k in range(3)))
    return out


def superellipse(w=1.0, h=1.0, exp=2.0, n=28):
    """Anneau superellipse |x/w|^exp+|z/h|^exp=1. exp<2 = section anguleuse
    (crânes reptiliens), exp=2 = ellipse, exp>2 = rectangle arrondi. Points 2D (x,z)."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        x = w * math.copysign(abs(c) ** (2 / exp), c)
        z = h * math.copysign(abs(s) ** (2 / exp), s)
        pts.append((x, z))
    return pts


def lsystem(axiom, rules, depth):
    """L-système symbolique (ramifications : bois de cerf, veines). Retourne la chaîne."""
    s = axiom
    for _ in range(depth):
        s = "".join(rules.get(c, c) for c in s)
    return s
