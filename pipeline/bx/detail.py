"""bx.detail — micro-détail géométrique sans sculpt (convergences C4+C5 des deux docs).
C4 : couches de Displace (macro plis / écailles moyennes / micro rides) sur mesh subdivisé.
C5 : écailles explicites par Geometry Nodes — Distribute Points on Faces + Instance on
Points, densité pilotée par la courbure (Edge Angle). Tout est numérique, piloté par la spec."""
import bpy

from . import core


def displace_layers(ob, layers, subdiv=2):
    """Empile des Displace pilotés par textures procédurales legacy (CLOUDS/VORONOI…).
    layers = [{'type':'CLOUDS','size':1.2,'strength':0.08,'mid':0.5,'coords':'OBJECT'}…]
    Un Subsurf SIMPLE en tête fournit la densité de vertices nécessaire au détail
    haute fréquence sans re-lisser la forme fusionnée."""
    if subdiv:
        m = ob.modifiers.new('densify', 'SUBSURF')
        m.subdivision_type = 'SIMPLE'
        m.levels = m.render_levels = subdiv
    for i, lay in enumerate(layers):
        tex = bpy.data.textures.new(f'{ob.name}_disp{i}', lay.get('type', 'CLOUDS'))
        if hasattr(tex, 'noise_scale'):
            tex.noise_scale = lay.get('size', 1.0)
        d = ob.modifiers.new(f'disp{i}', 'DISPLACE')
        d.texture = tex
        d.strength = lay.get('strength', 0.05)
        d.mid_level = lay.get('mid', 0.5)
        d.texture_coords = lay.get('coords', 'OBJECT')
        d.direction = lay.get('direction', 'NORMAL')
    return ob


def scales(ob, instance_ob, density=60.0, scale=(0.06, 0.14), seed=0,
           curvature=True, realize=True, name='scales'):
    """Écailles/ostéodermes explicites par Geometry Nodes (API interface bpy 4+/5).
    Densité modulée par l'angle d'arête signé (convexe = crêtes dorsales → dense,
    concave = plis du cou → clairsemé), orientation alignée aux normales via la
    sortie Rotation du Distribute. `instance_ob` = mesh d'écaille canonique."""
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    n_in = ng.nodes.new('NodeGroupInput')
    n_out = ng.nodes.new('NodeGroupOutput')
    dist = ng.nodes.new('GeometryNodeDistributePointsOnFaces')
    dist.distribute_method = 'RANDOM'
    dist.inputs['Seed'].default_value = seed
    inst = ng.nodes.new('GeometryNodeInstanceOnPoints')
    info = ng.nodes.new('GeometryNodeObjectInfo')
    info.inputs['Object'].default_value = instance_ob
    info.transform_space = 'ORIGINAL'
    rnd = ng.nodes.new('FunctionNodeRandomValue')
    rnd.data_type = 'FLOAT'
    rnd.inputs['Min'].default_value = scale[0]
    rnd.inputs['Max'].default_value = scale[1]
    join = ng.nodes.new('GeometryNodeJoinGeometry')

    lk = ng.links.new
    if curvature:
        ang = ng.nodes.new('GeometryNodeInputMeshEdgeAngle')
        mr = ng.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = -0.8   # concave → densité plancher
        mr.inputs['From Max'].default_value = 0.8    # convexe → densité max
        mr.inputs['To Min'].default_value = density * 0.15
        mr.inputs['To Max'].default_value = density
        lk(ang.outputs['Signed Angle'], mr.inputs['Value'])  # interpolation de domaine implicite
        lk(mr.outputs['Result'], dist.inputs['Density'])
    else:
        dist.inputs['Density'].default_value = density
    lk(n_in.outputs['Geometry'], dist.inputs['Mesh'])
    lk(dist.outputs['Points'], inst.inputs['Points'])
    lk(dist.outputs['Rotation'], inst.inputs['Rotation'])
    lk(info.outputs['Geometry'], inst.inputs['Instance'])
    lk(rnd.outputs['Value'], inst.inputs['Scale'])
    lk(n_in.outputs['Geometry'], join.inputs['Geometry'])
    if realize:
        real = ng.nodes.new('GeometryNodeRealizeInstances')
        lk(inst.outputs['Instances'], real.inputs['Geometry'])
        lk(real.outputs['Geometry'], join.inputs['Geometry'])
    else:
        lk(inst.outputs['Instances'], join.inputs['Geometry'])
    lk(join.outputs['Geometry'], n_out.inputs['Geometry'])

    mod = ob.modifiers.new(name, 'NODES')
    mod.node_group = ng
    instance_ob.hide_render = True
    return ob


def scale_plate(name='scale_plate', size=1.0):
    """Écaille canonique : plaque losange bombée low-poly, prête à instancier."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    v = [bm.verts.new(co) for co in [
        (0, -size * 0.6, 0), (size * 0.45, 0, 0), (0, size * 0.75, 0),
        (-size * 0.45, 0, 0), (0, 0, size * 0.28)]]
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 0)]:
        bm.faces.new((v[a], v[b], v[4]))
    bm.faces.new((v[0], v[3], v[2], v[1]))  # fond → plaque fermée
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    core.link(ob)
    return core.shade_smooth(ob)
