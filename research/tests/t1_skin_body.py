"""T1 — Candidat doc 1 : corps continu par modifier Skin sur graphe d'arêtes.
Quadrupède cible (même morphologie que T2) : colonne queue→museau, 4 pattes, cou.
Mesures : étanchéité, arêtes non-manifold, tris auto-intersectés, polys, temps."""
import _common as C
from bx import core, fuse, validate


def quadruped_graph():
    """Squelette symétrique généré en code (symétrie garantie sans Mirror)."""
    verts, radii = [], []

    def V(x, y, z, r):
        verts.append((x, y, z))
        radii.append(r)
        return len(verts) - 1

    # colonne : bout de queue → museau (rayons allométriques)
    spine_pts = [(-3.2, 0, 1.05, 0.05), (-2.4, 0, 1.15, 0.12), (-1.6, 0, 1.3, 0.22),
                 (-0.8, 0, 1.42, 0.34), (0.0, 0, 1.5, 0.42), (0.8, 0, 1.52, 0.40),
                 (1.4, 0, 1.62, 0.30), (1.9, 0, 1.95, 0.20), (2.4, 0, 2.25, 0.17),
                 (2.9, 0, 2.3, 0.16), (3.5, 0, 2.2, 0.10)]
    spine = [V(x, y, z, r) for x, y, z, r in spine_pts]
    edges = [(spine[i], spine[i + 1]) for i in range(len(spine) - 1)]

    # pattes : hanche(4) et épaule(6), des deux côtés, 3 segments jusqu'au sol
    for anchor, x in [(spine[3], -0.8), (spine[6], 1.4)]:
        for side in (1, -1):
            hip = V(x, side * 0.5, 1.1, 0.22)
            knee = V(x + 0.15, side * 0.62, 0.62, 0.15)
            ankle = V(x + 0.05, side * 0.62, 0.28, 0.11)
            foot = V(x + 0.3, side * 0.62, 0.07, 0.10)
            edges += [(anchor, hip), (hip, knee), (knee, ankle), (ankle, foot)]
    return {'verts': verts, 'edges': edges, 'radii': radii,
            'root': spine[4], 'subsurf': 2, 'branch_smoothing': 0.6}


core.reset()
with C.timer() as t:
    body = fuse.skin_body(quadruped_graph(), name='skin_quadruped')
rep = validate.geometry_report(body)
render = C.clay_render('t1_skin_quadruped')
C.log('t1_skin_body', {'method': 'SKIN modifier + subsurf2 (doc 1)',
                       'build_seconds': t.dt, 'report': rep, 'render': render})
