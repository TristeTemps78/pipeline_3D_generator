"""bx.fuse — corps organique continu et étanche (point de DIVERGENCE des deux docs).
Deux candidats implémentés et bancs d'essai dans research/tests/ :
  - skin_body()  : doc 1 — modifier Skin sur un graphe d'arêtes paramétrique.
  - voxel_fuse() : doc 2 — join des primitives + Remesh VOXEL + lissage préservant le volume.
Le gagnant du banc d'essai devient la voie par défaut du pipeline (voir research/convergence.md §3)."""
import bmesh
import bpy
from mathutils import Vector

from . import core


def apply_modifiers(ob):
    """Fige les modifiers sans bpy.ops.modifier_apply (robuste en headless bpy-module) :
    mesh évalué par le depsgraph → remplace la data, purge les modifiers."""
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(
        ob.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
    old = ob.data
    ob.data = me
    ob.modifiers.clear()
    if isinstance(old, bpy.types.Mesh) and old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def join_to_mesh(objs, name='joined'):
    """Fusionne des objets (MESH ou CURVE) en un seul mesh, en espace monde,
    via bmesh — pas de bpy.ops.object.join, pas de dépendance à la sélection."""
    deps = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for ob in objs:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), depsgraph=deps)
        me.transform(ob.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    out = bpy.data.objects.new(name, me)
    core.link(out)
    for ob in objs:
        bpy.data.objects.remove(ob)
    return out


def voxel_size_for(ob, target_res=200):
    """Formule doc 2 : diagonale de la bounding box monde / résolution cible, bornée.
    Invariante à l'échelle : la créature peut être re-scalée par la spec sans explosion mémoire."""
    corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(c[i] for c in corners) for i in range(3)))
    hi = Vector((max(c[i] for c in corners) for i in range(3)))
    return max(0.0005, min(0.05, (hi - lo).length / target_res))


def voxel_fuse(objs, target_res=200, smooth_iters=5, smooth_lambda=0.5,
               name='fused', apply=True):
    """Doc 2 : primitives qui s'interpénètrent → un seul manifold étanche.
    Remesh en mode VOXEL (modifier, pas l'operator : pas de blocage/crash headless),
    puis Laplacian Smooth avec préservation de volume pour fondre les jonctions
    (transitions musculaires) sans dégonfler membres et cornes."""
    ob = objs[0] if len(objs) == 1 else join_to_mesh(objs, name)
    ob.name = name
    rm = ob.modifiers.new('voxel_remesh', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel_size_for(ob, target_res)
    rm.use_smooth_shade = True
    ls = ob.modifiers.new('relax', 'LAPLACIANSMOOTH')
    ls.lambda_factor = smooth_lambda
    ls.iterations = smooth_iters
    ls.use_volume_preserve = True
    ls.use_normalized = True
    if apply:
        apply_modifiers(ob)
        core.shade_smooth(ob)
    return ob


def skin_body(graph, name='body', apply=True):
    """Doc 1 : graphe d'arêtes (squelette) → surface continue via le modifier Skin.
    graph = {'verts': [[x,y,z]…], 'edges': [[i,j]…], 'radii': [r…] ou [[rx,ry]…],
             'root': index, 'subsurf': niveaux}.
    NB : pas de Mirror ici — la symétrie est garantie par le générateur de graphe
    (code), pas besoin du modifier que doc 1 recommande pour équilibrer à la main."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in graph['verts']],
                   [tuple(e) for e in graph['edges']], [])
    ob = bpy.data.objects.new(name, me)
    core.link(ob)
    sk = ob.modifiers.new('skin', 'SKIN')
    sk.use_smooth_shade = True
    sk.branch_smoothing = graph.get('branch_smoothing', 0.5)
    radii = graph.get('radii', [0.25] * len(graph['verts']))
    for i, r in enumerate(radii):
        rx, ry = (r, r) if isinstance(r, (int, float)) else (r[0], r[1])
        ob.data.skin_vertices[0].data[i].radius = (rx, ry)
    ob.data.skin_vertices[0].data[graph.get('root', 0)].use_root = True
    core.subsurf(ob, graph.get('subsurf', 2))
    if apply:
        apply_modifiers(ob)
        core.shade_smooth(ob)
    return ob
