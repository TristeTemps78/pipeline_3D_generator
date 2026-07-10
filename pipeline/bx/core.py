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


def realize_to_mesh(ob):
    """Convertit un objet CURVE (tube bevelé, cornes/dents/spine) en un nouvel objet MESH
    évalué — bake du profil bevel_depth/radius par point via le depsgraph (sans bpy.ops,
    robuste en headless bpy-module, même pattern que fuse.join_to_mesh). Nécessaire avant
    d'ajouter un modifier Geometry Nodes de distribution de surface (Distribute Points on
    Faces exige une entrée Mesh ; une Curve brute donne 0 point, silencieusement).
    Object.data ne peut pas changer de type (Curve->Mesh) sur le même objet : on crée un
    nouvel objet MESH au même nom/transform/matériaux et on retire l'ancien."""
    if ob.type != 'CURVE':
        return ob
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), depsgraph=deps)
    new = bpy.data.objects.new(ob.name, me)
    link(new)
    new.matrix_world = ob.matrix_world
    for mat in ob.data.materials:
        new.data.materials.append(mat)
    old_data = ob.data
    bpy.data.objects.remove(ob)
    if old_data.users == 0:
        bpy.data.curves.remove(old_data)
    return shade_smooth(new)


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


def world(color=(0.03, 0.04, 0.06), strength=0.4, color_top=None, volume=None, variation=None):
    """Fond monde. Rétro-compatible : color/strength seuls = fond uni.
    color_top : dégradé horizon→zénith (horizon = `color`).
    volume : {'density', 'anisotropy', 'color', 'noise_scale', 'noise_strength'} → brume
    par volume scatter mondial ; noise_scale>0 (défaut 0 = densité constante, rétro-
    compat) module la densité par un bruit 3D (« poussière d'or » patchy plutôt qu'un
    brouillard uniforme).
    variation : {'scale', 'strength', 'color', 'detail'} → fond non-uni générique (bruit
    Noise sur coords Generated, mixé par-dessus le dégradé/couleur de base) — casse le
    fond plat façon canyon/paroi rocheuse, aucune valeur dragon en dur."""
    w = bpy.data.worlds.new('world')
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    bg.inputs[1].default_value = strength
    base_socket = None
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
        base_socket = mix.outputs['Result']
    else:
        bg.inputs[0].default_value = (*color, 1)
    if variation:
        vtc = nt.nodes.new('ShaderNodeTexCoord')
        vn = nt.nodes.new('ShaderNodeTexNoise')
        vn.inputs['Scale'].default_value = variation.get('scale', 2.5)
        vn.inputs['Detail'].default_value = variation.get('detail', 4.0)
        nt.links.new(vtc.outputs['Generated'], vn.inputs['Vector'])
        vramp = nt.nodes.new('ShaderNodeValToRGB')
        vramp.color_ramp.elements[0].position = 0.35
        vramp.color_ramp.elements[1].position = 0.65
        nt.links.new(vn.outputs['Fac'], vramp.inputs['Fac'])
        vfac = nt.nodes.new('ShaderNodeMath')
        vfac.operation = 'MULTIPLY'
        vfac.inputs[1].default_value = variation.get('strength', 0.5)
        nt.links.new(vramp.outputs['Color'], vfac.inputs[0])
        vmix = nt.nodes.new('ShaderNodeMix')
        vmix.data_type = 'RGBA'
        vmix.inputs['B'].default_value = (*variation.get('color', (0.6, 0.3, 0.08)), 1)
        if base_socket is not None:
            nt.links.new(base_socket, vmix.inputs['A'])
        else:
            vmix.inputs['A'].default_value = (*color, 1)
        nt.links.new(vfac.outputs['Value'], vmix.inputs['Factor'])
        nt.links.new(vmix.outputs['Result'], bg.inputs[0])
    elif base_socket is not None:
        nt.links.new(base_socket, bg.inputs[0])
    if volume:
        vs = nt.nodes.new('ShaderNodeVolumeScatter')
        base_density = volume.get('density', 0.01)
        noise_scale = volume.get('noise_scale', 0.0)
        if noise_scale > 0:
            ntc = nt.nodes.new('ShaderNodeTexCoord')
            nz = nt.nodes.new('ShaderNodeTexNoise')
            nz.inputs['Scale'].default_value = noise_scale
            nz.inputs['Detail'].default_value = volume.get('noise_detail', 3.0)
            nt.links.new(ntc.outputs['Object'], nz.inputs['Vector'])
            nstr = volume.get('noise_strength', 0.6)
            nr = nt.nodes.new('ShaderNodeMapRange')
            nr.inputs['From Min'].default_value = 0.3
            nr.inputs['From Max'].default_value = 0.7
            nr.inputs['To Min'].default_value = max(0.0, 1.0 - nstr)
            nr.inputs['To Max'].default_value = 1.0 + nstr
            nt.links.new(nz.outputs['Fac'], nr.inputs['Value'])
            dmul = nt.nodes.new('ShaderNodeMath')
            dmul.operation = 'MULTIPLY'
            dmul.inputs[1].default_value = base_density
            nt.links.new(nr.outputs['Result'], dmul.inputs[0])
            nt.links.new(dmul.outputs['Value'], vs.inputs['Density'])
        else:
            vs.inputs['Density'].default_value = base_density
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
              bg=(0.01, 0.011, 0.014), key_size=8, rim_size=5,
              rim2=None, rim2_energy=450, rim2_color=(0.55, 0.68, 0.95), rim2_size=6):
    """Éclairage dramatique de contre-jour (inversion I7) : une key douce + un RIM
    puissant chaud derrière le sujet → jantes lumineuses qui révèlent bords d'écailles
    et translucidité de membrane sur fond sombre, comme la réf Drogon. Retire les lumières
    existantes d'abord. `rim_size` petit = source plus dure → highlights plus incisifs sur
    les carènes d'écailles (relief géométrique, pas de bruit shader). `rim2` optionnel :
    2e rim froide faible de l'autre côté du sujet, sépare la silhouette du fond sans
    dupliquer la chaleur du rim principal."""
    for ob in list(bpy.context.scene.objects):
        if ob.type == 'LIGHT':
            bpy.data.objects.remove(ob)
    world(color=bg, strength=0.25)
    area_light(key, target=target, energy=key_energy, size=key_size, color=(1.0, 0.92, 0.82))
    area_light(rim, target=target, energy=rim_energy, size=rim_size, color=rim_color)
    if rim2 is not None:
        area_light(rim2, target=target, energy=rim2_energy, size=rim2_size, color=rim2_color)


def render(path, res=(1152, 864), samples=48, throttle=True):
    """`throttle` (T14, research/logs/t14_cycles_throttle.json) : bounces bornés,
    caustiques off, adaptive sampling, BVH persistant — diff pixel 0.001 vs réglages
    larges sur la scène complète ; le gain vient surtout des rendus multiples d'un
    même process (contact_sheet 4 vues, boucles internes) et bornera le coût quand
    les instances ×35k arriveront."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.device = 'CPU'
    if throttle:
        cy = sc.cycles
        cy.max_bounces = 6
        cy.diffuse_bounces = 2
        cy.glossy_bounces = 3
        cy.caustics_reflective = cy.caustics_refractive = False
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = 0.03
        sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)
    return path
