"""T11 — couche 2 MESO : bibliothèque d'archétypes d'écailles + Pick Instance par index
+ bruit de frontière, sur un tube (proxy du cou). Comparé à l'armure actuelle
(1 archétype ×N) à densité/espacement égaux :
  A = armor_scales actuel (1 keeled_scale)
  B = 4 archétypes (carénée triangulaire, plate losange, cornillon, scute large)
      index = gradient spatial Z + bruit AVANT arrondi (frontières ditherées),
      jitter taille + rotation par instance.
Métrique : edge_density (clay, même cadrage). Verdict aussi à l'œil sur les 2 PNG."""
import os

import numpy as np

from _common import RENDERS, log, timer

import bpy  # noqa: E402
from bx import core, detail, feedback, ops  # noqa: E402

RES, SAMPLES = (720, 540), 14
CAM, TGT = (2.4, -1.6, 1.7), (0, 0, 1.0)


def make_tube():
    core.reset()
    tube = ops.tube('neck', [(0, -2.2, 1), (0, -0.8, 1), (0, 0.8, 1), (0, 2.2, 1)],
                    [0.34, 0.5, 0.5, 0.34])
    return core.realize_to_mesh(tube)


def render(name):
    core.clay()
    core.camera(CAM, target=TGT, lens=60)
    out = os.path.join(RENDERS, f'{name}.png')
    core.render(out, res=RES, samples=SAMPLES)
    img = bpy.data.images.load(out)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(RES[1], RES[0], 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    return out, round(feedback.edge_density(px), 4)


def archetypes():
    """4 plaques canoniques ~taille 1, +Y caudal, à instancier (hide_render géré après)."""
    keeled = detail.keeled_scale('arch_keeled', size=1.0, length=1.6, keel=0.5,
                                 lift=0.19, smooth=False)
    plate = detail.scale_plate('arch_plate', size=1.0)
    plate.scale = (1.0, 1.0, 0.45)          # losange plat
    horn = detail.keeled_scale('arch_horn', size=0.8, length=1.1, keel=1.05,
                               lift=0.32, smooth=False)  # cornillon : carène haute
    scute = detail.scale_plate('arch_scute', size=1.0)
    scute.scale = (1.55, 1.15, 0.3)         # scute large de flanc
    return [keeled, plate, horn, scute]


def multi_armor(ob, archs, density=900.0, scale=(0.10, 0.15), distance_min=0.075,
                seed=3, caudal=(0, 1, 0), noise_amp=1.4, name='multi_armor'):
    """armor_scales généralisé : Instance on Points en mode Pick Instance.
    Index = Map Range(Z) 0..len-1 + (noise-0.5)*noise_amp, arrondi/clampé →
    régions par archétype à frontières ditherées. Jitter : scale aléatoire (déjà)
    + rotation Z aléatoire ±10° via Rotate Instances."""
    n = len(archs)
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    n_in, n_out = ng.nodes.new('NodeGroupInput'), ng.nodes.new('NodeGroupOutput')
    lk = ng.links.new

    dist = ng.nodes.new('GeometryNodeDistributePointsOnFaces')
    dist.distribute_method = 'POISSON'
    dist.inputs['Distance Min'].default_value = distance_min
    dist.inputs['Density Max'].default_value = density
    dist.inputs['Seed'].default_value = seed

    # bibliothèque : chaque archétype devient UNE instance distincte
    geo2inst = ng.nodes.new('GeometryNodeGeometryToInstance')
    for a in archs:
        info = ng.nodes.new('GeometryNodeObjectInfo')
        info.inputs['Object'].default_value = a
        info.transform_space = 'ORIGINAL'
        lk(info.outputs['Geometry'], geo2inst.inputs['Geometry'])
        a.hide_render = True

    inst = ng.nodes.new('GeometryNodeInstanceOnPoints')
    inst.inputs['Pick Instance'].default_value = True
    lk(geo2inst.outputs['Instances'], inst.inputs['Instance'])

    # index spatial : Z -> 0..n-1, bruit AVANT arrondi = dither des frontières
    pos = ng.nodes.new('GeometryNodeInputPosition')
    sep = ng.nodes.new('ShaderNodeSeparateXYZ')
    lk(pos.outputs['Position'], sep.inputs['Vector'])
    mr = ng.nodes.new('ShaderNodeMapRange')
    mr.clamp = True
    mr.inputs['From Min'].default_value = 0.5   # bas du tube (z)
    mr.inputs['From Max'].default_value = 1.5   # haut du tube
    mr.inputs['To Min'].default_value = 0.0
    mr.inputs['To Max'].default_value = float(n - 1)
    lk(sep.outputs['Z'], mr.inputs['Value'])
    noise = ng.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    sub = ng.nodes.new('ShaderNodeMath')
    sub.operation = 'SUBTRACT'
    sub.inputs[1].default_value = 0.5
    lk(noise.outputs['Fac'], sub.inputs[0])
    amp = ng.nodes.new('ShaderNodeMath')
    amp.operation = 'MULTIPLY'
    amp.inputs[1].default_value = noise_amp
    lk(sub.outputs['Value'], amp.inputs[0])
    add = ng.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    lk(mr.outputs['Result'], add.inputs[0])
    lk(amp.outputs['Value'], add.inputs[1])
    clamp = ng.nodes.new('ShaderNodeClamp')
    clamp.inputs['Min'].default_value = 0.0
    clamp.inputs['Max'].default_value = float(n - 1)
    lk(add.outputs['Value'], clamp.inputs['Value'])
    to_int = ng.nodes.new('FunctionNodeFloatToInt')
    to_int.rounding_mode = 'ROUND'
    lk(clamp.outputs['Result'], to_int.inputs['Float'])
    lk(to_int.outputs['Integer'], inst.inputs['Instance Index'])

    # orientation cohérente Z<-normale puis Y<-caudal (comme armor_scales)
    alignZ = ng.nodes.new('FunctionNodeAlignEulerToVector')
    alignZ.axis = 'Z'
    alignY = ng.nodes.new('FunctionNodeAlignEulerToVector')
    alignY.axis = 'Y'
    alignY.pivot_axis = 'Z'
    caud = ng.nodes.new('FunctionNodeInputVector')
    caud.vector = caudal
    lk(dist.outputs['Normal'], alignZ.inputs['Vector'])
    lk(alignZ.outputs['Rotation'], alignY.inputs['Rotation'])
    lk(caud.outputs['Vector'], alignY.inputs['Vector'])

    rnd = ng.nodes.new('FunctionNodeRandomValue')
    rnd.data_type = 'FLOAT'
    rnd.inputs['Min'].default_value, rnd.inputs['Max'].default_value = scale
    rnd.inputs['Seed'].default_value = seed + 7

    lk(n_in.outputs['Geometry'], dist.inputs['Mesh'])
    lk(dist.outputs['Points'], inst.inputs['Points'])
    lk(alignY.outputs['Rotation'], inst.inputs['Rotation'])
    lk(rnd.outputs['Value'], inst.inputs['Scale'])

    # jitter rotation Z ±10° par instance
    rot = ng.nodes.new('GeometryNodeRotateInstances')
    rnd_rot = ng.nodes.new('FunctionNodeRandomValue')
    rnd_rot.data_type = 'FLOAT_VECTOR'
    rnd_rot.inputs['Min'].default_value = (0, 0, -0.175)
    rnd_rot.inputs['Max'].default_value = (0, 0, 0.175)
    rnd_rot.inputs['Seed'].default_value = seed + 13
    lk(inst.outputs['Instances'], rot.inputs['Instances'])
    lk(rnd_rot.outputs['Value'], rot.inputs['Rotation'])

    real = ng.nodes.new('GeometryNodeRealizeInstances')
    join = ng.nodes.new('GeometryNodeJoinGeometry')
    lk(rot.outputs['Instances'], real.inputs['Geometry'])
    lk(n_in.outputs['Geometry'], join.inputs['Geometry'])
    lk(real.outputs['Geometry'], join.inputs['Geometry'])
    lk(join.outputs['Geometry'], n_out.inputs['Geometry'])
    mod = ob.modifiers.new(name, 'NODES')
    mod.node_group = ng
    return ob


# A — armure actuelle (1 archétype)
tube = make_tube()
plate = detail.keeled_scale('plate', size=1.0, length=1.6, keel=0.5, lift=0.19, smooth=False)
with timer() as ta:
    detail.armor_scales(tube, plate, density=900.0, scale=(0.10, 0.15), seed=3,
                        caudal=(0, 1, 0), distance_min=0.075)
    out_a, ed_a = render('t11_single')

# B — 4 archétypes + pick instance + dither
tube = make_tube()
with timer() as tb:
    multi_armor(tube, archetypes(), density=900.0, scale=(0.10, 0.15),
                distance_min=0.075, seed=3)
    out_b, ed_b = render('t11_multi')

log('t11_archetypes', {
    'edge_density_single': ed_a, 'edge_density_multi': ed_b,
    'time_single_s': ta.dt, 'time_multi_s': tb.dt,
    'renders': [out_a, out_b],
    'verdict': 'OK' if ed_b >= ed_a * 0.95 else 'À JUGER (œil)',
})
