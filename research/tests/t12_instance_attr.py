"""T12 — couche 3 MICRO : détail unique par instance à coût géométrique nul.
Mécanisme (convergence exacte des 2 rapports) :
  GN : Store Named Attribute (domaine INSTANCE, float 'scale_seed' aléatoire),
       instances PAS réalisées ;
  Shader : node Attribute type 'INSTANCER' → chaque écaille échantillonne le
       Voronoi/couleur à une origine différente.
Vérifications : (1) variation visible par instance au rendu (variance de teinte
sujet >> contrôle sans attribut) ; (2) coût : temps de rendu + verts évalués
instances vs réalisées."""
import os

import numpy as np

from _common import RENDERS, log, timer

import bpy  # noqa: E402
from bx import core, detail, ops  # noqa: E402

RES, SAMPLES = (720, 540), 14
CAM, TGT = (2.4, -1.6, 1.7), (0, 0, 1.0)


def make_tube():
    core.reset()
    tube = ops.tube('neck', [(0, -2.2, 1), (0, -0.8, 1), (0, 0.8, 1), (0, 2.2, 1)],
                    [0.34, 0.5, 0.5, 0.34])
    return core.realize_to_mesh(tube)


def armor_instances(ob, plate, realize, store_seed, density=900.0, scale=(0.10, 0.15),
                    distance_min=0.075, seed=3):
    """Armure minimale : Poisson + Instance on Points ; option Store Named Attribute
    domaine INSTANCE + option sortie instances vivantes (realize=False)."""
    ng = bpy.data.node_groups.new('armor_i', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    n_in, n_out = ng.nodes.new('NodeGroupInput'), ng.nodes.new('NodeGroupOutput')
    lk = ng.links.new
    dist = ng.nodes.new('GeometryNodeDistributePointsOnFaces')
    dist.distribute_method = 'POISSON'
    dist.inputs['Distance Min'].default_value = distance_min
    dist.inputs['Density Max'].default_value = density
    dist.inputs['Seed'].default_value = seed
    inst = ng.nodes.new('GeometryNodeInstanceOnPoints')
    info = ng.nodes.new('GeometryNodeObjectInfo')
    info.inputs['Object'].default_value = plate
    info.transform_space = 'ORIGINAL'
    plate.hide_render = True
    rnd = ng.nodes.new('FunctionNodeRandomValue')
    rnd.data_type = 'FLOAT'
    rnd.inputs['Min'].default_value, rnd.inputs['Max'].default_value = scale
    rnd.inputs['Seed'].default_value = seed + 7
    alignZ = ng.nodes.new('FunctionNodeAlignEulerToVector')
    alignZ.axis = 'Z'
    lk(n_in.outputs['Geometry'], dist.inputs['Mesh'])
    lk(dist.outputs['Normal'], alignZ.inputs['Vector'])
    lk(dist.outputs['Points'], inst.inputs['Points'])
    lk(alignZ.outputs['Rotation'], inst.inputs['Rotation'])
    lk(info.outputs['Geometry'], inst.inputs['Instance'])
    lk(rnd.outputs['Value'], inst.inputs['Scale'])
    tail = inst.outputs['Instances']
    if store_seed:
        store = ng.nodes.new('GeometryNodeStoreNamedAttribute')
        store.domain = 'INSTANCE'
        store.data_type = 'FLOAT'
        store.inputs['Name'].default_value = 'scale_seed'
        rnd_seed = ng.nodes.new('FunctionNodeRandomValue')
        rnd_seed.data_type = 'FLOAT'
        rnd_seed.inputs['Min'].default_value = 0.0
        rnd_seed.inputs['Max'].default_value = 1.0
        rnd_seed.inputs['Seed'].default_value = seed + 21
        lk(tail, store.inputs['Geometry'])
        lk(rnd_seed.outputs['Value'], store.inputs['Value'])
        tail = store.outputs['Geometry']
    if realize:
        real = ng.nodes.new('GeometryNodeRealizeInstances')
        lk(tail, real.inputs['Geometry'])
        tail = real.outputs['Geometry']
    join = ng.nodes.new('GeometryNodeJoinGeometry')
    lk(n_in.outputs['Geometry'], join.inputs['Geometry'])
    lk(tail, join.inputs['Geometry'])
    lk(join.outputs['Geometry'], n_out.inputs['Geometry'])
    ob.modifiers.new('armor_i', 'NODES').node_group = ng
    return ob


def seed_material(use_attr):
    """Couleur = teinte pilotée par 'scale_seed' (Instancer) + Voronoi décalé par seed.
    Contrôle (use_attr=False) : même shader, seed constant 0.5."""
    m = bpy.data.materials.new('seedmat')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.6
    if use_attr:
        attr = nt.nodes.new('ShaderNodeAttribute')
        attr.attribute_type = 'INSTANCER'
        attr.attribute_name = 'scale_seed'
        fac = attr.outputs['Fac']
    else:
        val = nt.nodes.new('ShaderNodeValue')
        val.outputs[0].default_value = 0.5
        fac = val.outputs[0]
    # teinte par instance
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.8, 0.1, 0.1, 1)
    ramp.color_ramp.elements[1].color = (0.1, 0.3, 0.9, 1)
    e = ramp.color_ramp.elements.new(0.5)
    e.color = (0.1, 0.8, 0.2, 1)
    nt.links.new(fac, ramp.inputs['Fac'])
    # micro Voronoi décalé par seed (origine unique par écaille)
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.voronoi_dimensions = '4D'
    vor.inputs['Scale'].default_value = 60.0
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 100.0
    nt.links.new(fac, mul.inputs[0])
    nt.links.new(mul.outputs['Value'], vor.inputs['W'])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['Factor'].default_value = 0.35
    nt.links.new(ramp.outputs['Color'], mix.inputs['A'])
    nt.links.new(vor.outputs['Color'], mix.inputs['B'])
    nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    return m


def build_and_render(name, realize, use_attr):
    tube = make_tube()
    plate = detail.keeled_scale('plate', size=1.0, length=1.6, keel=0.5,
                                lift=0.19, smooth=False)
    armor_instances(tube, plate, realize=realize, store_seed=True)
    mat = seed_material(use_attr)
    for ob in (tube, plate):
        ob.data.materials.clear()
        ob.data.materials.append(mat)
    core.world(color=(0.7, 0.7, 0.7), strength=0.5)
    core.sun(direction=(-0.4, -0.4, -1), energy=3.5, color=(1, 1, 1), angle_deg=10)
    core.camera(CAM, target=TGT, lens=60)
    deps = bpy.context.evaluated_depsgraph_get()
    ev = tube.evaluated_get(deps)
    nverts = len(ev.data.vertices)
    out = os.path.join(RENDERS, f'{name}.png')
    with timer() as t:
        core.render(out, res=RES, samples=SAMPLES)
    img = bpy.data.images.load(out)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(RES[1], RES[0], 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    # variance de teinte sur pixels saturés (sujet coloré) : proxy d'unicité par instance
    mx, mn = px.max(-1), px.min(-1)
    sat = (mx - mn) > 0.12
    hue_spread = 0.0
    if sat.sum() > 100:
        r, g, b = px[sat, 0], px[sat, 1], px[sat, 2]
        hue_spread = float(np.std(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)))
    return {'render': out, 'time_s': t.dt, 'evaluated_verts': nverts,
            'hue_spread': round(hue_spread, 4)}


live = build_and_render('t12_live_attr', realize=False, use_attr=True)
ctrl = build_and_render('t12_ctrl_const', realize=False, use_attr=False)
real = build_and_render('t12_realized', realize=True, use_attr=True)

log('t12_instance_attr', {
    'live_instances_attr': live, 'control_const': ctrl, 'realized_attr': real,
    'verdict': ('OK' if live['hue_spread'] > ctrl['hue_spread'] * 3
                and live['evaluated_verts'] < real['evaluated_verts'] * 0.2
                else 'À JUGER'),
})
