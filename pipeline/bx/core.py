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


def world(color=(0.03, 0.04, 0.06), strength=0.4):
    w = bpy.data.worlds.new('world')
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = strength
    bpy.context.scene.world = w
    return w


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
