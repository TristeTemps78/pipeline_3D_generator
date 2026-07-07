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


def grid_surface(name, grid):
    """Maillage depuis une grille 2D de points [colonne][rangée] (membranes, voiles)."""
    verts, faces = [], []
    nc, nr = len(grid), len(grid[0])
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
