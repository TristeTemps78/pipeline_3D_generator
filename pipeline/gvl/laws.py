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


def growth_rings(n, depth=0.14, freq=5.0, sharp=3.0):
    """Anneaux de croissance kératine (cornes/griffes/becs) : bourrelets périodiques
    ISOLÉS le long d'un axe (t=0..1 sur n points), pas une onde continue -> chaque
    anneau lit comme un renflement net plutôt qu'une ondulation lisse. Retourne n
    multiplicateurs de rayon >=1 (1.0 entre les anneaux, 1+depth au pic). `freq` =
    nb d'anneaux sur toute la longueur, `sharp` (>1) resserre chaque anneau. Phase en
    SINUS (pas cosinus) : nul en t=0 ET t=1 -> aucun anneau ne coïncide avec la toute
    base (qui reçoit déjà son propre bourrelet d'implantation, cf. `root_bulge`) ni la
    pointe fine, évite qu'un anneau ne s'y additionne et gonfle démesurément."""
    n = max(1, n)
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        bump = max(0.0, math.sin(math.pi * freq * t)) ** sharp
        out.append(1.0 + depth * bump)
    return out


def curl_offset(n, amount=0.0, power=1.6):
    """Courbure/torsion progressive de pointe (cornes qui s'enroulent, griffes,
    queues) : décalage latéral croissant de 0 (base) à `amount` (pointe), le long
    d'un axe perpendiculaire au tracé principal -> à ajouter à une coordonnée hors
    plan des points d'une loi de forme (ex. `log_spiral`). `power` >1 concentre la
    courbure vers la pointe plutôt qu'un arc régulier."""
    n = max(1, n)
    return [amount * (i / (n - 1)) ** power if n > 1 else 0.0 for i in range(n)]


def axis_flex(n, dip=0.0, tip=0.0, dip_pos=0.4, sharp=1.0):
    """Flèche verticale non-linéaire le long d'un axe de loft (n points, t=0..1) —
    boucle 17 CR3 : remplace un profil de mâchoire quasi-droit par une courbe
    crocodilienne générique (museau qui PLONGE (`dip`, vers le bas) jusqu'à
    `dip_pos` puis REMONTE (`tip`, vers le haut) vers la pointe t=1 ; signe inversé
    -> mâchoire inférieure en courbe inverse). Interpolation cosinus (dérivée nulle
    aux points de contrôle 0/dip_pos/1, pas de cassure) entre 3 hauteurs (0, -dip,
    tip). `sharp` (>1) resserre la remontée finale vers la pointe (profil plus
    concentré en "bec" sur les derniers points). Retourne n décalages Z à ADDITIONNER
    aux centres d'anneaux d'un `ring_loft` (offset(t=0)=0 -> préserve l'ancrage à la
    base de l'axe, ex. jonction crâne/cou). Aucune valeur anatomique dragon ici :
    juste une courbe de flèche générique réutilisable pour tout profil de loft
    (mâchoires, becs, museaux, cous...)."""
    def cos_interp(a, b, f):
        f2 = (1 - math.cos(max(0.0, min(1.0, f)) * math.pi)) / 2
        return a + (b - a) * f2
    n = max(1, n)
    dip_pos = max(1e-4, min(1.0 - 1e-4, dip_pos))
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        if t <= dip_pos:
            z = cos_interp(0.0, -dip, t / dip_pos)
        else:
            f = ((t - dip_pos) / (1.0 - dip_pos)) ** sharp
            z = cos_interp(-dip, tip, f)
        out.append(z)
    return out


def fusiform(u, peak=0.35, power=2.0):
    """Enveloppe de renflement fusiforme ASYMÉTRIQUE (masses musculaires sur un
    membre/bras) : profil 0->1->0 sur u=0..1 (fraction locale d'une fenêtre de
    muscle), pic décalé vers `peak` (<0.5 = masse concentrée vers le DÉBUT de la
    fenêtre, ex. haut de cuisse/épaule qui s'amenuise plus progressivement vers le
    tendon distal, comme un vrai muscle plutôt qu'un renflement centré symétrique).
    `power` (>1) resserre la montée/descente autour du pic (bulge plus net, moins
    "ballon")."""
    peak = min(max(peak, 1e-4), 1 - 1e-4)
    u = min(max(u, 0.0), 1.0)
    f = u / peak if u < peak else (1 - u) / (1 - peak)
    return max(0.0, math.sin(math.pi * 0.5 * f)) ** power


def joint_bump(d, w=0.12, sharp=2.0):
    """Renflement osseux LOCAL et NET à une articulation (genou, cheville, coude/
    poignet d'aile) : gaussienne resserrée (`sharp`>1 = flancs plus raides, casse la
    silhouette au lieu d'un simple élargissement doux) en fonction de la distance
    signée `d` (fraction de segment) au point de contrôle de l'articulation. Retourne
    une enveloppe 0..1 (0 loin du joint, 1 pile dessus) à combiner en multiplicateur
    de rayon par l'appelant (ex. `1 + (r_joint - 1) * joint_bump(...)`)."""
    return math.exp(-0.5 * (d / max(w, 1e-4)) ** 2) ** sharp


def fold_indent(d, n=3, width=0.06, depth=0.05):
    """Plis de peau aux articulations (`fold_rings`) : PLUSIEURS anneaux de pincement
    (2-4, `n`) d'amplitude décroissante, décalés de part et d'autre du point de pli
    (d=0, fraction de segment) -> lit comme plusieurs plis de peau superposés qui
    s'estompent en s'éloignant, plutôt qu'un unique sillon symétrique. Retourne
    l'indentation cumulée (0..~depth) à SOUSTRAIRE du rayon, uniquement du côté
    intérieur du pli (l'appelant pondère déjà par la projection sur le côté concave)."""
    n = max(1, int(n))
    total = 0.0
    for i in range(n):
        side = 1 if i % 2 == 0 else -1
        mag = (i // 2) + 1
        off = side * mag * width * 1.15
        amp = depth * (1.0 - i / n)
        g = math.exp(-0.5 * ((d - off) / max(width * 0.55, 1e-4)) ** 2)
        total += amp * g
    return total


def catmull_rom(pts, samples=1):
    """Interpolation Catmull-Rom C1 (n>=2 points de contrôle, dimension quelconque —
    3D pour une polyligne, 1-tuple pour un profil de rayons) : boucle 22, thème
    « souder pas poser ». Contrairement à `lerp_path` (ré-échantillonnage LINÉAIRE,
    donc coudes vifs à chaque point de contrôle conservés) ou à la NURBS de `ops.tube`
    (lisse mais n'INTERPOLE pas exactement les points de contrôle intermédiaires), ceci
    PASSE par tous les points d'origine avec une tangente continue -> remplace le
    zigzag anguleux d'une spine à peu de points par une courbe fluide, sans changer
    la forme d'ensemble ni les ancrages (début/fin inchangés). `samples` = nb de
    points insérés par segment de contrôle (1 = pas d'insertion -> comportement
    inchangé, rétro-compat totale). Points d'extrémité dupliqués (clamped) pour ne
    pas extrapoler hors de la polyligne aux 2 bouts."""
    n = len(pts)
    if n < 3 or samples <= 1:
        return list(pts)
    dim = len(pts[0])

    def get(i):
        i = max(0, min(n - 1, i))
        return pts[i]

    out = []
    for i in range(n - 1):
        p0, p1, p2, p3 = get(i - 1), get(i), get(i + 1), get(i + 2)
        for st in range(samples):
            t = st / samples
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * ((2 * p1[d]) + (-p0[d] + p2[d]) * t
                       + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t2
                       + (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * t3)
                for d in range(dim)))
    out.append(tuple(pts[-1]))
    return out


def lsystem(axiom, rules, depth):
    """L-système symbolique (ramifications : bois de cerf, veines). Retourne la chaîne."""
    s = axiom
    for _ in range(depth):
        s = "".join(rules.get(c, c) for c in s)
    return s
