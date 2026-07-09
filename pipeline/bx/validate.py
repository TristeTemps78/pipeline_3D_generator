"""bx.validate — sanity checks géométriques AVANT rendu (convergence C1 des deux docs).
BVHTree en espace monde : auto-intersections, chevauchements entre objets, contact au sol.
Sortie = dicts numériques compacts, lisibles par l'orchestrateur sans dépenser un rendu."""
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

EPS = 1e-5


def _evaluated_bm(ob, world=True, triangulate=False):
    """BMesh de l'objet évalué (modifiers/courbes appliqués), transformé en espace monde.
    Le transform monde est obligatoire : sans lui, deux objets seraient comparés
    comme s'ils étaient tous deux à l'origine (faux positifs garantis).
    Passe par new_from_object → gère aussi les CURVE (tubes/cornes), pas seulement les MESH."""
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), depsgraph=deps)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    if world:
        bm.transform(ob.matrix_world)
    if triangulate and bm.faces:
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    return bm


def _tree(ob):
    bm = _evaluated_bm(ob, triangulate=True)
    tree = BVHTree.FromBMesh(bm, epsilon=EPS)
    return tree, bm


def _island_count(bm):
    """Nombre de composantes connexes. Un corps fusionné doit en avoir UNE :
    'watertight' seul ne détecte pas une tête laissée en coquille séparée."""
    parent = list(range(len(bm.verts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    bm.verts.ensure_lookup_table()
    for e in bm.edges:
        a, b = find(e.verts[0].index), find(e.verts[1].index)
        if a != b:
            parent[a] = b
    return len({find(i) for i in range(len(bm.verts))})


def geometry_report(ob):
    """Manifold/étanchéité + auto-intersections d'un objet. Compact et numérique."""
    bm = _evaluated_bm(ob)
    verts, faces = len(bm.verts), len(bm.faces)
    bad_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    loose = sum(1 for v in bm.verts if not v.link_faces)
    islands = _island_count(bm)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tree = BVHTree.FromBMesh(bm, epsilon=EPS)
    overlap = tree.overlap(tree)  # méthode du 3D Printing Toolbox (self-overlap)
    self_int = len({i for pair in overlap for i in pair})
    bm.free()
    return {
        'object': ob.name, 'verts': verts, 'faces': faces,
        'non_manifold_edges': bad_edges, 'loose_verts': loose, 'islands': islands,
        'watertight': bad_edges == 0 and loose == 0 and faces > 0,
        'single_body': islands == 1,
        'self_intersecting_tris': self_int,
    }


def pair_overlap(a, b):
    """Nombre de paires de triangles qui s'intersectent entre deux objets
    (dents vs mâchoire, griffes vs sol…). 0 = pas de collision."""
    ta, bma = _tree(a)
    tb, bmb = _tree(b)
    n = len(ta.overlap(tb))
    bma.free()
    bmb.free()
    return n


def ground_contact(ob, ground, sample_lowest=8):
    """Écart signé entre les points les plus bas de `ob` et la surface de `ground`.
    gap > 0 : flotte ; gap < 0 : traverse le sol ; |gap| <= tol : posé.
    Rayon lancé depuis très haut à l'aplomb de chaque point bas → hauteur du sol."""
    tg, bmg = _tree(ground)
    bm = _evaluated_bm(ob)
    lowest = sorted(bm.verts, key=lambda v: v.co.z)[:sample_lowest]
    gaps = []
    for v in lowest:
        hit = tg.ray_cast(Vector((v.co.x, v.co.y, v.co.z + 1000.0)), Vector((0, 0, -1)))
        if hit[0] is not None:
            gaps.append(v.co.z - hit[0].z)
    bm.free()
    bmg.free()
    if not gaps:
        return {'object': ob.name, 'status': 'no_ground_below', 'gap': None}
    gap = min(gaps)
    return {'object': ob.name, 'gap': round(gap, 4),
            'status': 'floating' if gap > 0.02 else ('clipping' if gap < -0.02 else 'grounded')}


GROUND_PARTS = ('foot', 'toe', 'claw', 'leg', 'paw', 'hoof')


def scene_report(ground_name='ground', check_pairs=None, ground_parts=GROUND_PARTS):
    """Rapport complet de la scène : étanchéité par mesh, contact sol, paires demandées.
    check_pairs : liste de (nom_a, nom_b) à tester en collision.
    ground_parts : sous-chaînes de noms testées pour le contact sol (pieds), afin de
    ne pas signaler cornes/dents comme 'flottantes' (bruit inutile pour l'orchestrateur)."""
    sc = bpy.context.scene
    meshes = [o for o in sc.objects if o.type in ('MESH', 'CURVE') and o.name != ground_name]
    ground = sc.objects.get(ground_name)
    rep = {'objects': [geometry_report(o) for o in meshes], 'ground': [], 'pairs': []}
    if ground:
        for o in meshes:
            if any(k in o.name.lower() for k in ground_parts):
                rep['ground'].append(ground_contact(o, ground))
    for a, b in (check_pairs or []):
        oa, ob_ = sc.objects.get(a), sc.objects.get(b)
        if oa and ob_:
            rep['pairs'].append({'a': a, 'b': b, 'overlapping_tris': pair_overlap(oa, ob_)})
    return rep
