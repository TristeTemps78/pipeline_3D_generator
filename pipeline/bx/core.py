"""bx.core — gestion scène, rendu, sauvegarde. Verbes de haut niveau, contexte-safe en headless."""
import math

import bpy
from mathutils import Vector


def reset():
    """Scène vide."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def shade_smooth(ob):
    if ob.type == 'MESH':
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def subsurf(ob, levels=2):
    m = ob.modifiers.new('subsurf', 'SUBSURF')
    m.levels = m.render_levels = levels
    return ob


def solidify(ob, thickness=0.02):
    ob.modifiers.new('solid', 'SOLIDIFY').thickness = thickness
    return ob


def mirror_x(ob):
    """Symétrie bilatérale à travers le plan X=0 (origine objet au monde)."""
    m = ob.modifiers.new('mirror', 'MIRROR')
    m.use_axis = (True, False, False)
    return ob


def sun(direction=(-0.4, 0.6, -1), energy=4.0, color=(1, 0.93, 0.82), angle_deg=2.0):
    li = bpy.data.lights.new('sun', 'SUN')
    li.energy, li.color, li.angle = energy, color, math.radians(angle_deg)
    ob = bpy.data.objects.new('sun', li)
    link(ob)
    ob.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return ob


def area_light(loc, target=(0, 0, 2), energy=800, size=6, color=(1, 1, 1)):
    li = bpy.data.lights.new('area', 'AREA')
    li.energy, li.size, li.color = energy, size, color
    ob = bpy.data.objects.new('area', li)
    link(ob)
    ob.location = loc
    aim(ob, target)
    return ob


def aim(ob, target):
    d = Vector(target) - Vector(ob.location)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def camera(loc, target=(0, 0, 2), lens=45):
    cam = bpy.data.cameras.new('cam')
    cam.lens = lens
    ob = bpy.data.objects.new('cam', cam)
    link(ob)
    ob.location = loc
    aim(ob, target)
    bpy.context.scene.camera = ob
    return ob


def world(color=(0.03, 0.04, 0.06), strength=0.4, color_top=None, volume=None):
    """Fond monde. Rétro-compatible : color/strength seuls = fond uni.
    color_top : dégradé horizon→zénith (horizon = `color`).
    volume : {'density', 'anisotropy', 'color'} → brume par volume scatter mondial."""
    w = bpy.data.worlds.new('world')
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    bg.inputs[1].default_value = strength
    if color_top:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = -0.1
        mr.inputs['From Max'].default_value = 0.6
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.inputs['A'].default_value = (*color, 1)
        mix.inputs['B'].default_value = (*color_top, 1)
        nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
        nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
        nt.links.new(mr.outputs['Result'], mix.inputs['Factor'])
        nt.links.new(mix.outputs['Result'], bg.inputs[0])
    else:
        bg.inputs[0].default_value = (*color, 1)
    if volume:
        vs = nt.nodes.new('ShaderNodeVolumeScatter')
        vs.inputs['Density'].default_value = volume.get('density', 0.01)
        vs.inputs['Anisotropy'].default_value = volume.get('anisotropy', 0.4)
        vs.inputs['Color'].default_value = (*volume.get('color', (1.0, 0.8, 0.55)), 1)
        nt.links.new(vs.outputs['Volume'], nt.nodes['World Output'].inputs['Volume'])
    bpy.context.scene.world = w
    return w


def clay():
    """Mode validation géométrie : matériaux neutres mats, éclairage uniforme lumineux.
    Yeux/narines sombres, dents/griffes/cornes claires pour la lisibilité."""
    def flat(name, c, rough=0.8):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*c, 1)
        b.inputs['Roughness'].default_value = rough
        return m
    grey = flat('clay', (0.55, 0.53, 0.5))
    dark = flat('clay_dark', (0.02, 0.02, 0.02), 0.25)
    light = flat('clay_light', (0.85, 0.82, 0.75))
    for ob in list(bpy.context.scene.objects):
        if ob.type == 'LIGHT':
            bpy.data.objects.remove(ob)
        elif ob.type in ('MESH', 'CURVE'):
            ob.data.materials.clear()
            nm = ob.name
            if 'eye' in nm or 'nostril' in nm:
                ob.data.materials.append(dark)
            elif 'tooth' in nm or 'claw' in nm or 'horn' in nm or 'dorsal' in nm:
                ob.data.materials.append(light)
            else:
                ob.data.materials.append(grey)
    world(color=(1, 1, 1), strength=0.35)
    sun(direction=(-0.4, -0.4, -1), energy=4.5, color=(1, 1, 1), angle_deg=12)
    area_light((6, 10, 6), target=(0, 1, 2.5), energy=500, size=12)


def rim_setup(key=(6, -8, 5), rim=(-7, 7, 4), target=(0, 0, 1.5),
              key_energy=700, rim_energy=2600, rim_color=(1.0, 0.72, 0.42),
              bg=(0.01, 0.011, 0.014)):
    """Éclairage dramatique de contre-jour (inversion I7) : une key douce + un RIM
    puissant chaud derrière le sujet → jantes lumineuses qui révèlent bords d'écailles
    et translucidité de membrane sur fond sombre, comme la réf Drogon. Retire les lumières
    existantes d'abord."""
    for ob in list(bpy.context.scene.objects):
        if ob.type == 'LIGHT':
            bpy.data.objects.remove(ob)
    world(color=bg, strength=0.25)
    area_light(key, target=target, energy=key_energy, size=8, color=(1.0, 0.92, 0.82))
    area_light(rim, target=target, energy=rim_energy, size=5, color=rim_color)


def render(path, res=(1152, 864), samples=48):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.device = 'CPU'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)
    return path
