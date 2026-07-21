"""OUTIL b26 : SOUDE les 4 pattes dans la cage du corps -> UNE SEULE PEAU (doctrine
CLAUDE.md « corps/tete/membres = une cage subsurf continue »). IMPRIME le nouveau
body_cage, n'ecrit pas la spec.

Methode (celle d'un modeleur, au niveau vertex, sans booleen) :
1. la cage corps ne porte que la moitie +X (mirror_x) -> on CUIT le miroir : anneau
   ferme de 8 points (haut, 3 pts +X, bas, 3 pts -X). La pose des pattes etant
   ASYMETRIQUE (marche), un miroir de modifier ne peut plus servir ;
2. pour chaque patte on supprime DEUX quads voisins du dessous du corps -> trou
   hexagonal (6 sommets de bord), exactement le cardinal d'un anneau de patte ;
3. on jette l'anneau de HANCHE de la patte (il flottait dans le volume) et on ponte
   le trou sur l'anneau de GENOU -> la cuisse devient la transition, et le subsurf
   fabrique tout seul le conge d'attache ;
4. appariement des deux boucles par force brute (6 rotations x 2 sens, on garde la
   somme de distances minimale) : aucune convention d'ordre a maintenir a la main.
"""
import json
import math

STEP_HIP = 6      # 6 points par anneau de patte
REFINE = 1        # passes de raffinement AVANT percage : plus le trou est
#                   petit, plus le ventre reste HAUT (la cuisse ne rend plus
#                   en entonnoir qui comble le vide sous le corps)
SUBSURF = 1       # cage 4x plus dense -> un niveau de subsurf suffit
LEG_IDS = ['leg_front_far', 'leg_front_near', 'leg_hind_far', 'leg_hind_near']

# Repose b26 : les pattes « far » etaient a x=-0.1 (sous l'axe du ventre) — invisible de
# profil mais faux de face. On les ecarte sur le flanc. La patte avant gauche etait
# plantee sous la MACHOIRE (pose de marche de la ref). Round 2 : la reculer par
# cisaillement en Y donnait une CUISSE DIAGONALE qui bouche le vide entre patte et
# poitrail -> IoU -0.09. La ref a bien ce vide ET cette patte avancee (tete basse, pose
# a l'affut) : on la laisse OU ELLE EST, la soudure se fait sous le cou.
SCALE = 1.0     # (1.18 essaye : -0.005, la patte n'etait pas trop fine)
LEG_FIX = {
    'leg_front_far': {'dx': -0.32, 'scale_xy': SCALE},
    'leg_front_near': {'dx': -0.07, 'scale_xy': SCALE},
    'leg_hind_far': {'dx': -0.34, 'scale_xy': SCALE},
    'leg_hind_near': {'dx': -0.06, 'scale_xy': SCALE},
}


def _mir(v):
    return [-v[0], v[1], v[2]]


def full_rings(half):
    """20 anneaux x 5 pts (moitie +X) -> 20 anneaux FERMES de 8 pts."""
    rings = []
    for i in range(0, len(half), 5):
        p = half[i:i + 5]
        rings.append([p[0], p[1], p[2], p[3], p[4], _mir(p[3]), _mir(p[2]), _mir(p[1])])
    return rings


def _mid(a, b):
    return [(a[k] + b[k]) / 2.0 for k in range(3)]


def catmull_clark(verts, faces):
    """Une passe de Catmull-Clark EXACTE (points de face/arete + repositionnement des
    sommets). C'est LA difference avec un raffinement lineaire : CC conserve la surface
    limite — subdiviser la cage une fois puis subsurf N-1 rend EXACTEMENT la meme forme
    qu'un subsurf N sur la cage grossiere. Un raffinement lineaire, lui, gonfle le corps
    vers le polygone de controle (essaye en round 3 : IoU -0.02 avant meme les pattes)."""
    fp = [_centroid([verts[i] for i in f]) for f in faces]
    ef, ei = {}, {}
    for fi, f in enumerate(faces):
        for k in range(len(f)):
            e = (min(f[k], f[(k + 1) % len(f)]), max(f[k], f[(k + 1) % len(f)]))
            ef.setdefault(e, []).append(fi)
    new = [None] * len(verts)
    out = [list(v) for v in verts]
    off_f = len(out)
    out.extend([list(p) for p in fp])
    off_e = len(out)
    for e, fs in ef.items():
        a, b = verts[e[0]], verts[e[1]]
        pts = [a, b] + [fp[i] for i in fs]
        ei[e] = len(out)
        out.append(_centroid(pts))
    # repositionnement des sommets d'origine
    adj_f, adj_e = {}, {}
    for e, fs in ef.items():
        for v in e:
            adj_e.setdefault(v, []).append(_mid(verts[e[0]], verts[e[1]]))
            for i in fs:
                adj_f.setdefault(v, []).append(fp[i])
    for vi, v in enumerate(verts):
        F = _centroid(adj_f[vi])
        R = _centroid(adj_e[vi])
        n = len(set(tuple(p) for p in adj_e[vi])) or 4
        new[vi] = [(F[k] + 2 * R[k] + (n - 3) * v[k]) / n for k in range(3)]
    for vi, p in enumerate(new):
        out[vi] = p
    nf = []
    for fi, f in enumerate(faces):
        m = len(f)
        for k in range(m):
            prev = (min(f[k - 1], f[k]), max(f[k - 1], f[k]))
            nxt = (min(f[k], f[(k + 1) % m]), max(f[k], f[(k + 1) % m]))
            nf.append([f[k], ei[nxt], off_f + fi, ei[prev]])
    return out, nf


def refine(rings):
    """Subdivision LINEAIRE de la grille (anneaux x points) : le trou d'attache d'une
    patte fait 2 quads de la cage — sur la cage grossiere il vaut un quart de ventre et
    la cuisse rend en JUPE (round 1 : IoU -0.08). Une passe de raffinement le divise
    par 4 sans changer la forme (des milieux d'aretes ne bougent pas la surface limite
    du Catmull-Clark de facon perceptible)."""
    fine = []
    for r in rings:
        row = []
        for j in range(len(r)):
            row.extend([r[j], _mid(r[j], r[(j + 1) % len(r)])])
        fine.append(row)
    out = [fine[0]]
    for a, b in zip(fine, fine[1:]):
        out.append([_mid(a[j], b[j]) for j in range(len(a))])
        out.append(b)
    return out


def _centroid(pts):
    n = len(pts)
    return [sum(p[k] for p in pts) / n for k in range(3)]


def _fix_leg(verts, fix):
    """Deplacement lateral, cisaillement en Y (haut recule, pied fixe) et epaississement
    autour de l'axe de la patte : souder fait perdre l'anneau de hanche, donc la patte
    rend PLUS FINE qu'avant (elle ne commence qu'au genou) — `scale_xy` le compense."""
    zs = [v[2] for v in verts]
    z_lo, z_hi = min(zs), max(zs)
    cx = sum(v[0] for v in verts) / len(verts)
    cy = sum(v[1] for v in verts) / len(verts)
    k = fix.get('scale_xy', 1.0)
    out = []
    for x, y, z in verts:
        t = (z - z_lo) / (z_hi - z_lo) if z_hi > z_lo else 0.0
        out.append([cx + (x - cx) * k + fix.get('dx', 0.0),
                    cy + (y - cy) * k + fix.get('shear_y', 0.0) * t, z])
    return out


def _face_normal(verts, f):
    return _newell([verts[i] for i in f])


def _newell(pts):
    nx = ny = nz = 0.0
    for i, (x1, y1, z1) in enumerate(pts):
        x2, y2, z2 = pts[(i + 1) % len(pts)]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def _loop_of(f1, f2):
    """Bord de l'union de 2 quads voisins : cycle ordonne de 6 sommets."""
    edges = []
    for f in (f1, f2):
        for k in range(len(f)):
            e = (f[k], f[(k + 1) % len(f)])
            if (e[1], e[0]) in edges:
                edges.remove((e[1], e[0]))     # arete partagee : elle disparait
            else:
                edges.append(e)
    nxt = dict(edges)
    start = edges[0][0]
    loop, v = [start], nxt[start]
    while v != start:
        loop.append(v)
        v = nxt[v]
    return loop


def build(spec):
    body = next(p for p in spec['parts'] if p['id'] == 'body_cage')
    rings = full_rings(body['verts'])
    nr, nj = len(rings), len(rings[0])
    verts = [list(v) for r in rings for v in r]
    faces = []
    for r in range(nr - 1):
        for j in range(nj):
            faces.append([r * nj + j, r * nj + (j + 1) % nj,
                          (r + 1) * nj + (j + 1) % nj, (r + 1) * nj + j])
    faces.append(list(reversed(range(nj))))
    faces.append([(nr - 1) * nj + j for j in range(nj)])
    for _ in range(REFINE):
        verts, faces = catmull_clark(verts, faces)

    # voisinage par arete (pour choisir 2 quads accoles sous le ventre)
    ef = {}
    for fi, f in enumerate(faces):
        for k in range(len(f)):
            e = (min(f[k], f[(k + 1) % len(f)]), max(f[k], f[(k + 1) % len(f)]))
            ef.setdefault(e, []).append(fi)
    nbr = {}
    for e, fs in ef.items():
        if len(fs) == 2:
            nbr.setdefault(fs[0], []).append(fs[1])
            nbr.setdefault(fs[1], []).append(fs[0])

    dead, bridges = set(), []
    new_faces = []
    for lid in LEG_IDS:
        leg = next(p for p in spec['parts'] if p['id'] == lid)
        lverts = _fix_leg([list(v) for v in leg['verts']], LEG_FIX.get(lid, {}))
        knee = lverts[STEP_HIP:2 * STEP_HIP]
        kc = _centroid(knee)

        def score(fi):
            c = _centroid([verts[i] for i in faces[fi]])
            return (c[0] - kc[0]) ** 2 + (c[1] - kc[1]) ** 2 + 0.1 * (c[2] - kc[2]) ** 2

        cand = [fi for fi, f in enumerate(faces)
                if fi not in dead and _face_normal(verts, f)[2] < 0]
        f1 = min(cand, key=score)
        f2 = min([n for n in nbr[f1] if n not in dead and
                  _face_normal(verts, faces[n])[2] < 0], key=score)
        loop = _loop_of(faces[f1], faces[f2])
        dead.update((f1, f2))

        base = len(verts)
        verts.extend(lverts[STEP_HIP:])
        nrings = len(lverts) // STEP_HIP - 1
        for rr in range(nrings - 1):
            for jj in range(STEP_HIP):
                a = base + rr * STEP_HIP + jj
                b = base + rr * STEP_HIP + (jj + 1) % STEP_HIP
                new_faces.append([a, b, b + STEP_HIP, a + STEP_HIP])
        new_faces.append([base + (nrings - 1) * STEP_HIP + jj for jj in range(STEP_HIP)])

        kidx = [base + jj for jj in range(STEP_HIP)]
        bestm = None
        for rev in (False, True):
            order = list(reversed(kidx)) if rev else kidx
            for off in range(STEP_HIP):
                c = [order[(i + off) % STEP_HIP] for i in range(STEP_HIP)]
                d = sum(sum((verts[loop[i]][k] - verts[c[i]][k]) ** 2 for k in range(3))
                        for i in range(STEP_HIP))
                if bestm is None or d < bestm[0]:
                    bestm = (d, c)
        c = bestm[1]
        for i in range(STEP_HIP):
            new_faces.append([loop[i], loop[(i + 1) % STEP_HIP],
                              c[(i + 1) % STEP_HIP], c[i]])
        bridges.append((lid, round(math.sqrt(bestm[0] / STEP_HIP), 3)))

    faces = [f for i, f in enumerate(faces) if i not in dead] + new_faces
    return ({"type": "cage", "id": "body_cage", "mirror_x": False,
             "subsurf": SUBSURF, "mat": body.get('mat', 'scales_body'),
             "verts": [[round(c, 4) for c in v] for v in verts], "faces": faces},
            bridges)


if __name__ == '__main__':
    spec = json.load(open('specs/krokmou_cage.json', encoding='utf-8'))
    part, br = build(spec)
    print(len(part['verts']), 'verts,', len(part['faces']), 'faces')
    for b in br:
        print('  soudure', b)
