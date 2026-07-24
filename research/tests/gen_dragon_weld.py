"""OUTIL b31 etape 3 : SOUDE les 4 pattes du Colosse dans la cage du corps -> UNE SEULE
PEAU (doctrine CLAUDE.md « corps/tete/membres = une cage subsurf continue »). ECRIT
specs/dragon.json (comme gen_dragon_cage.py) -- CONSOMME leg_fore/leg_hind (non idempotent :
si elles sont deja absentes de la spec, le script ABORT).

Adaptation de research/tests/gen_body_weld.py (soudure Krokmou, demi-anneaux 5 pts) a la
cage du dragon (demi-anneaux 7 pts, pattes en tubes 4 pts) :
1. On DEVELOPPE le corps (mirror cuit : demi-anneaux 7 pts -> anneaux fermes 12 pts) puis on
   le lofte + 2 capuchons ngon (museau/queue), exactement comme gen_body_weld.full_rings/build
   mais pas a pas de 5->8, ici 7->12.
2. On RAFFINE par Catmull-Clark EXACT (importe de gen_body_weld, maths pures) : le corps ET
   CHAQUE TUBE DE PATTE separement, AVANT tout percage. Les tubes de patte ne sont qu'a 4 pts
   par anneau (contre 6 pour Krokmou, deja assez dense) -> sans CC ils rendraient anguleux
   une fois soudes a subsurf 1. Apres CC un anneau de patte fait 8 pts (4 sommets d'origine +
   4 points d'arete circonferentiels intercales).
3. On DEVELOPPE le miroir des pattes (mirror_x du spec) : chaque tube de patte n'est stocke
   qu'un cote (+X) -> copie + negation de x + inversion de l'ordre des faces (normales dehors)
   donne le cote -X. 4 pattes reelles au total, sans LEG_FIX/shear (contrairement a Krokmou :
   la pose du Colosse est symetrique).
4. PERCAGE par patte : sur le corps raffine, on cherche le sommet de valence 4 (4 faces
   incidentes actuellement vivantes), normale moyenne vers le bas (z<0, cote ventre), le plus
   proche du centroide de l'anneau de bridage de la patte -> on supprime ses 4 faces + lui-meme
   -> boucle de bord de 8 sommets (equivalent 4-pts du perçage 2-quads->6-loop de Krokmou).
5. PONTAGE : anneau de bridage = le premier anneau REEL de la patte (index 1 de la chaine de
   conception, juste apres l'extension enfouie au-dessus de la hanche/l'epaule) ; l'anneau 0
   (extension enfouie) et le capuchon du haut sont JETES (jamais construits dans la sortie).
   Appariement en force brute (8 offsets x 2 sens, somme des distances^2 minimale, comme
   gen_body_weld) ; pont quad par quad (8 quads par patte).
6. Assemblage final : verts/faces compactes (les sommets non references -- pole troue, anneau
   0 jete des pattes -- sont elagues), ecrits dans body_cage {mirror_x:false, subsurf:1}.
   leg_fore/leg_hind supprimes de la spec.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from gen_body_weld import catmull_clark, _centroid, _face_normal  # noqa: E402

STEP_BODY = 7          # points par demi-anneau du corps (SECTION du dragon)
STEP_LEG = 4            # points par anneau de patte (tube_along, section carree)
REFINE = 1              # passes de CC avant percage (theoreme : CCx1 + subsurf1 == subsurf2)
SUBSURF = 1
LEG_IDS = ['leg_fore', 'leg_hind']
# Anneau de bridage = index 1 de la chaine ORIGINALE (LEG_FORE/LEG_HIND dans gen_dragon_trace,
# 7 points chacune) ; tube_along prepend UNE extension (_extend au-dessus de hanche/epaule),
# donc dans les 9 anneaux du tube c'est l'anneau d'indice 1 (0 = extension enfouie, jetee).
BRIDGE_RING = 1
# Compensation optionnelle (mission etape 7) : degonflement radial des anneaux GARDES autour
# de l'axe local de la patte, a mesurer round par round. 1.0 = pas de compensation.
LEG_KEEP_SCALE = 1.0


def _mir(v):
    return [-v[0], v[1], v[2]]


def full_rings_7(half):
    """34 anneaux x 7 pts (moitie +X) -> 34 anneaux FERMES de 12 pts (mirror cuit)."""
    rings = []
    for i in range(0, len(half), STEP_BODY):
        p = half[i:i + STEP_BODY]
        rings.append([p[0], p[1], p[2], p[3], p[4], p[5], p[6],
                      _mir(p[5]), _mir(p[4]), _mir(p[3]), _mir(p[2]), _mir(p[1])])
    return rings


def _loft(rings):
    nr, nj = len(rings), len(rings[0])
    verts = [list(v) for r in rings for v in r]
    faces = []
    for r in range(nr - 1):
        for j in range(nj):
            faces.append([r * nj + j, r * nj + (j + 1) % nj,
                          (r + 1) * nj + (j + 1) % nj, (r + 1) * nj + j])
    faces.append(list(reversed(range(nj))))
    faces.append([(nr - 1) * nj + j for j in range(nj)])
    return verts, faces


def _edge_key(a, b):
    return (a, b) if a < b else (b, a)


def _cc_with_edge_index(verts, faces):
    """Enveloppe catmull_clark (gen_body_weld) qui rejoue EXACTEMENT la meme construction
    de `ef` (ordre d'insertion des aretes) pour retrouver, sans y toucher, l'index du
    nouveau sommet-arete cree pour chaque arete d'origine -- necessaire pour reconstruire
    un anneau (8 pts) apres une passe de CC sans modifier catmull_clark lui-meme."""
    ef = {}
    for fi, f in enumerate(faces):
        for k in range(len(f)):
            e = _edge_key(f[k], f[(k + 1) % len(f)])
            ef.setdefault(e, []).append(fi)
    off_e = len(verts) + len(faces)
    ei = {e: off_e + idx for idx, e in enumerate(ef.keys())}
    out, nf = catmull_clark(verts, faces)
    return out, nf, ei


def _loop_of(faces):
    """Boucle de bord ordonnee de l'union d'un nombre QUELCONQUE de faces (generalisation
    du `_loop_of(f1, f2)` a 2 faces de gen_body_weld -- ici jusqu'a 4, valence d'un sommet
    interieur d'une grille de quads)."""
    edges = []
    for f in faces:
        for k in range(len(f)):
            e = (f[k], f[(k + 1) % len(f)])
            if (e[1], e[0]) in edges:
                edges.remove((e[1], e[0]))
            else:
                edges.append(e)
    nxt = dict(edges)
    start = edges[0][0]
    loop, v = [start], nxt[start]
    while v != start:
        loop.append(v)
        v = nxt[v]
    return loop


def _refine_leg(leg):
    """CC une passe sur le tube COMPLET (2 capuchons + 9 anneaux), puis jette le capuchon
    du haut + la rangee de quads qui relie l'anneau 0 (enfoui) a l'anneau 1 (bridage) --
    exactement les 5 premieres faces d'ORIGINE (indices 0..4 : cap + 4 quads de la rangee 0),
    donc les 20 premieres faces APRES CC (chaque face d'origine engendre exactement 4
    quads, meme ordre). Retourne (verts, faces_gardees, loop8_anneau1)."""
    verts = [list(v) for v in leg['verts']]
    faces = [list(f) for f in leg['faces']]
    out, nf, ei = _cc_with_edge_index(verts, faces)
    kept = nf[4 * 5:]     # jette cap (face 0) + rangee 0 (faces 1..4)
    ring1 = [BRIDGE_RING * STEP_LEG + j for j in range(STEP_LEG)]
    loop8 = []
    for j in range(STEP_LEG):
        a, b = ring1[j], ring1[(j + 1) % STEP_LEG]
        loop8.append(a)
        loop8.append(ei[_edge_key(a, b)])
    return out, kept, loop8


def _mirror_leg(verts, faces, loop8):
    mv = [_mir(v) for v in verts]
    mf = [list(reversed(f)) for f in faces]
    return mv, mf, list(loop8)


def _bridge(body_verts, body_faces, dead_faces, dead_verts, leg_centroid):
    """Cherche le sommet de valence 4 (faces actuellement vivantes), normale moyenne vers
    le bas, le plus proche de `leg_centroid` -> renvoie sa boucle de bord (8 sommets) et
    marque le sommet + ses 4 faces morts (in-place sur dead_faces/dead_verts)."""
    from collections import defaultdict
    vf = defaultdict(list)
    for fi, f in enumerate(body_faces):
        if fi in dead_faces:
            continue
        for vi in f:
            vf[vi].append(fi)
    cx, cy, cz = leg_centroid
    cands = []
    for vi, fis in vf.items():
        if vi in dead_verts or len(fis) != 4:
            continue
        nz = sum(_face_normal(body_verts, body_faces[fi])[2] for fi in fis)
        if nz >= 0:
            continue
        x, y, z = body_verts[vi]
        score = (x - cx) ** 2 + (y - cy) ** 2 + 0.1 * (z - cz) ** 2
        cands.append((score, vi, fis))
    cands.sort(key=lambda c: c[0])
    for score, vi, fis in cands:
        loop = _loop_of([body_faces[fi] for fi in fis])
        if len(loop) == 8:
            dead_faces.update(fis)
            dead_verts.add(vi)
            return loop
    raise RuntimeError('aucun sommet de percage valide trouve (verifier valence/normale)')


def build(spec):
    body = next(p for p in spec['parts'] if p['id'] == 'body_cage')
    for lid in LEG_IDS:
        if not any(p['id'] == lid for p in spec['parts']):
            raise SystemExit(f"ABORT : '{lid}' absent de la spec -- deja soude ? "
                              f"(ce script consomme les pattes, non idempotent)")

    verts, faces = _loft(full_rings_7(body['verts']))
    for _ in range(REFINE):
        verts, faces = catmull_clark(verts, faces)

    dead_faces, dead_verts = set(), set()
    combined_verts = [list(v) for v in verts]
    combined_faces = list(faces)   # filtre des morts a la fin (indices stables jusque-la)
    bridges = []

    for lid in LEG_IDS:
        leg = next(p for p in spec['parts'] if p['id'] == lid)
        lv, lf, loop8 = _refine_leg(leg)
        for side, tag in ((1, '_near'), (-1, '_far')):
            if side == -1:
                sv, sf, sloop = _mirror_leg(lv, lf, loop8)
            else:
                sv, sf, sloop = [list(v) for v in lv], [list(f) for f in lf], list(loop8)
            if LEG_KEEP_SCALE != 1.0:
                cx = sum(sv[i][0] for i in range(len(sv))) / len(sv)
                cz = sum(sv[i][2] for i in range(len(sv))) / len(sv)
                sv = [[cx + (x - cx) * LEG_KEEP_SCALE, y, cz + (z - cz) * LEG_KEEP_SCALE]
                      for x, y, z in sv]

            base = len(combined_verts)
            combined_verts.extend(sv)
            combined_faces.extend([[i + base for i in f] for f in sf])
            leg_loop_world = [i + base for i in sloop]

            kc = _centroid([sv[i] for i in sloop])
            hole = _bridge(combined_verts, combined_faces, dead_faces, dead_verts, kc)

            bestm = None
            n = len(hole)
            for rev in (False, True):
                order = list(reversed(leg_loop_world)) if rev else leg_loop_world
                for off in range(n):
                    c = [order[(i + off) % n] for i in range(n)]
                    d = sum(sum((combined_verts[hole[i]][k] - combined_verts[c[i]][k]) ** 2
                                for k in range(3)) for i in range(n))
                    if bestm is None or d < bestm[0]:
                        bestm = (d, c)
            c = bestm[1]
            for i in range(n):
                combined_faces.append([hole[i], hole[(i + 1) % n], c[(i + 1) % n], c[i]])
            bridges.append((lid + tag, round((bestm[0] / n) ** 0.5, 4)))

    combined_faces = [f for i, f in enumerate(combined_faces) if i not in dead_faces]

    used = sorted({vi for f in combined_faces for vi in f})
    remap = {old: new for new, old in enumerate(used)}
    out_verts = [[round(c, 4) for c in combined_verts[vi]] for vi in used]
    out_faces = [[remap[vi] for vi in f] for f in combined_faces]

    return ({"type": "cage", "id": "body_cage", "mirror_x": False, "subsurf": SUBSURF,
             "mat": body.get('mat', 'hide'), "verts": out_verts, "faces": out_faces},
            bridges)


def main():
    path = os.path.join(ROOT, 'specs', 'dragon.json')
    spec = json.load(open(path, encoding='utf-8'))
    part, bridges = build(spec)
    print(len(part['verts']), 'verts,', len(part['faces']), 'faces')
    for b in bridges:
        print('  soudure', b)
    spec['parts'] = [part if p['id'] == 'body_cage' else p for p in spec['parts']
                      if p['id'] not in LEG_IDS]
    with open(path, 'w') as f:
        json.dump(spec, f, indent=1)
    print('ecrit', path)


if __name__ == '__main__':
    main()
