"""bx.ops — primitives géométriques AI-friendly (coordonnées monde, un appel = une forme)."""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from . import core


def tube(name, pts, radii, caps=True, order=4):
    """Tube organique : courbe NURBS avec rayon par point (corps, membres, cornes)."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('NURBS')
    sp.points.add(len(pts) - 1)
    for p, pt, r in zip(sp.points, pts, radii):
        p.co = (*pt, 1)
        p.radius = r
    sp.use_endpoint_u = True
    sp.order_u = min(order, len(pts))
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 8
    cu.use_fill_caps = caps
    return core.link(bpy.data.objects.new(name, cu))


def blob(name, loc=(0, 0, 0), scale=(1, 1, 1), rot_deg=(0, 0, 0), seg=32):
    """Ellipsoïde lisse (crânes, masses musculaires, pieds)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    core.link(ob)
    ob.location, ob.scale = loc, scale
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    return core.shade_smooth(ob)


def spike(name, loc, height=0.3, radius=0.08, rot_deg=(0, 0, 0), seg=8):
    """Cône pointu (pointes dorsales, dents, griffes)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg,
                          radius1=radius, radius2=0.0, depth=height)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    core.link(ob)
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    return core.shade_smooth(ob)


def grid_surface(name, grid, thickness=None):
    """Maillage depuis une grille 2D de points [colonne][rangée] (membranes, voiles).
    `thickness` optionnel : None -> feuille simple face (legacy, ex. anciennes membranes
    fines solidifiées après coup). Sinon scalaire OU liste par RANGÉE (longueur = nb de
    rangées, diffusée sur toutes les colonnes) -> construit un volume fermé (coque) avec
    épaisseur VARIABLE par rangée, offset le long de la normale locale : permet une
    membrane épaisse à la racine (rangée 0, le long des os) et fine au bord libre
    (dernière rangée), comme une planche à voile — sans dépendre d'un Solidify à
    épaisseur constante."""
    nc, nr = len(grid), len(grid[0])
    if thickness is None:
        verts, faces = [], []
        for col in grid:
            verts.extend(col)
        for i in range(nc - 1):
            for j in range(nr - 1):
                a = i * nr + j
                faces.append((a, a + 1, a + nr + 1, a + nr))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        ob = bpy.data.objects.new(name, mesh)
        core.link(ob)
        return core.shade_smooth(ob)

    th = list(thickness) if isinstance(thickness, (list, tuple)) else [thickness] * nr
    bm = bmesh.new()
    top = [[bm.verts.new(p) for p in col] for col in grid]
    for i in range(nc - 1):
        for j in range(nr - 1):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
    bm.normal_update()
    bot = [[bm.verts.new(v.co - v.normal * th[min(j, len(th) - 1)])
            for j, v in enumerate(col)] for col in top]
    for i in range(nc - 1):
        for j in range(nr - 1):
            bm.faces.new((bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j], bot[i][j]))
    for j in range(nr - 1):  # bords colonne 0 / dernière colonne
        bm.faces.new((top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j]))
        bm.faces.new((bot[nc - 1][j], bot[nc - 1][j + 1], top[nc - 1][j + 1], top[nc - 1][j]))
    for i in range(nc - 1):  # bord rangée 0 (racine, os) / dernière rangée (bord libre)
        bm.faces.new((bot[i][0], bot[i + 1][0], top[i + 1][0], top[i][0]))
        bm.faces.new((top[i][nr - 1], top[i + 1][nr - 1], bot[i + 1][nr - 1], bot[i][nr - 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    core.link(ob)
    return core.shade_smooth(ob)


def ring_loft(name, rings, caps=True, subsurf_levels=2):
    """Volume lofté depuis des anneaux 3D successifs (même nombre de points).
    Construction type box-modeling : sections transversales → surface continue lissée."""
    m = len(rings[0])
    verts, faces = [], []
    for ring in rings:
        verts.extend(ring)
    for i in range(len(rings) - 1):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            faces.append((a, b, b + m, a + m))
    if caps:
        for ring, base in ((rings[0], 0), (rings[-1], (len(rings) - 1) * m)):
            cx = tuple(sum(p[k] for p in ring) / m for k in range(3))
            ci = len(verts)
            verts.append(cx)
            for j in range(m):
                faces.append((ci, base + j, base + (j + 1) % m))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    core.link(ob)
    core.shade_smooth(ob)
    if subsurf_levels:
        core.subsurf(ob, subsurf_levels)
    return ob


def boolean_diff(target, cutter, name=None):
    """Soustrait `cutter` de `target` (creux d'orbite oculaire, etc.) via un modifier
    Boolean évalué par le depsgraph — même schéma que `core.realize_to_mesh` (bake vers
    un nouvel objet MESH, aucun bpy.ops nécessaire, robuste en headless). `cutter` est
    consommé (retiré de la scène) après l'opération."""
    mod = target.modifiers.new('bool_diff', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter
    mod.solver = 'EXACT'
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(deps), depsgraph=deps)
    new = bpy.data.objects.new(name or target.name, me)
    core.link(new)
    new.matrix_world = target.matrix_world
    for mat in target.data.materials:
        new.data.materials.append(mat)
    old_data = target.data
    bpy.data.objects.remove(target)
    if old_data.users == 0:
        bpy.data.meshes.remove(old_data)
    cutter_data = cutter.data
    bpy.data.objects.remove(cutter)
    if cutter_data.users == 0:
        bpy.data.meshes.remove(cutter_data)
    return core.shade_smooth(new)


def plane(name, size=60, z=0):
    mesh = bpy.data.meshes.new(name)
    s = size / 2
    mesh.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    mesh.update()
    return core.link(bpy.data.objects.new(name, mesh))


def place(ob, loc=None, rot_deg=None, scale=None):
    if loc:
        ob.location = loc
    if rot_deg:
        ob.rotation_euler = Euler([math.radians(a) for a in rot_deg])
    if scale:
        ob.scale = scale
    return ob


def transform_pts(pts, loc=(0, 0, 0), rot_deg=(0, 0, 0), scale=1.0, mirror=False):
    """Transforme des points locaux (ex: sortie de loi GVL) vers le monde."""
    rot = Euler([math.radians(a) for a in rot_deg]).to_matrix()
    out = []
    for p in pts:
        v = Vector(p) * scale
        if mirror:
            v.x = -v.x
        v = rot @ v + Vector(loc)
        out.append(tuple(v))
    return out
