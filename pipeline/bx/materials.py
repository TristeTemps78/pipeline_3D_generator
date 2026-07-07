"""bx.materials — shaders procéduraux paramétrés par le vocabulaire GVL."""
import bpy


def _new(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    return mat, nt, bsdf


def _set(node, key, value):
    """Set tolérant aux renommages d'inputs entre versions de Blender."""
    if key in node.inputs:
        node.inputs[key].default_value = value


def assign(ob, mat):
    ob.data.materials.append(mat)
    return ob


def reptile_scales(name='scales', base=(0.018, 0.017, 0.02), tint=(0.11, 0.025, 0.02),
                   scale=35, bump=0.5, rough=0.42):
    """pattern.reptile_scales : voronoi distance-to-edge → sillons; variation par cellule."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    vor = n.new('ShaderNodeTexVoronoi')
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = scale
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].position = 0.14
    bmp = n.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = bump
    cell = n.new('ShaderNodeTexVoronoi')
    cell.inputs['Scale'].default_value = scale
    mix = n.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (*base, 1)
    mix.inputs['B'].default_value = (*tint, 1)
    noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 8
    nrange = n.new('ShaderNodeMapRange')
    nrange.inputs['To Min'].default_value = 0.0
    nrange.inputs['To Max'].default_value = 0.35
    lk.new(vor.outputs['Distance'], ramp.inputs['Fac'])
    lk.new(ramp.outputs['Color'], bmp.inputs['Height'])
    lk.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    lk.new(cell.outputs['Color'], nrange.inputs['Value'])
    lk.new(nrange.outputs['Result'], mix.inputs['Factor'])
    lk.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    lk.new(noise.outputs['Fac'], bsdf.inputs['Roughness'])
    _set(bsdf, 'Roughness', rough)
    return mat


def membrane(name='membrane', color=(0.09, 0.015, 0.012), rough=0.55):
    """pattern.membrane_skin : peau fine, légère transmission rouge à contre-jour."""
    mat, nt, bsdf = _new(name)
    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Roughness', rough)
    _set(bsdf, 'Transmission Weight', 0.15)
    _set(bsdf, 'Subsurface Weight', 0.25)
    _set(bsdf, 'Subsurface Radius', (0.2, 0.04, 0.03))
    return mat


def bone(name='bone', color=(0.06, 0.05, 0.045), rough=0.35):
    mat, nt, bsdf = _new(name)
    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Roughness', rough)
    return mat


def eye(name='eye', color=(0.9, 0.45, 0.08), glow=2.0):
    mat, nt, bsdf = _new(name)
    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Emission Color', (*color, 1))
    _set(bsdf, 'Emission Strength', glow)
    _set(bsdf, 'Roughness', 0.1)
    return mat


def rock(name='rock', color=(0.055, 0.052, 0.05), scale=3.0):
    """pattern.rock : sol rocheux, bump par bruit."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 8
    bmp = n.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = 0.6
    lk.new(noise.outputs['Fac'], bmp.inputs['Height'])
    lk.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Roughness', 0.9)
    return mat
