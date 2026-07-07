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


def reptile_scales(name='scales', base=(0.012, 0.011, 0.013), tint=(0.25, 0.05, 0.02),
                   scale=5, scale2=16, bump=1.2, rough=0.5, warp=0.3,
                   sss=0.0, sss_radius=(0.32, 0.11, 0.06)):
    """pattern.reptile_scales v2 : 2 voronoi distance-to-edge superposés (plaques + micro-
    écailles) sur coordonnées Object distordues par noise (casse la grille ; Object car les
    curves n'ont pas de Generated fiable) ; arêtes cuivre rouge, roughness basse aux bords.
    Échelles en cellules par unité monde (~scale 5 → plaques de 20 cm)."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    # --- coordonnées distordues : Object + (noise-0.5)*warp ---
    tc = n.new('ShaderNodeTexCoord')
    wn = n.new('ShaderNodeTexNoise')
    wn.inputs['Scale'].default_value = 1.2
    wn.inputs['Detail'].default_value = 4
    sub = n.new('ShaderNodeVectorMath')
    sub.operation = 'SUBTRACT'
    sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    scl = n.new('ShaderNodeVectorMath')
    scl.operation = 'SCALE'
    scl.inputs['Scale'].default_value = warp
    add = n.new('ShaderNodeVectorMath')
    add.operation = 'ADD'
    lk.new(tc.outputs['Object'], wn.inputs['Vector'])
    lk.new(wn.outputs['Color'], sub.inputs[0])
    lk.new(sub.outputs['Vector'], scl.inputs[0])
    lk.new(tc.outputs['Object'], add.inputs[0])
    lk.new(scl.outputs['Vector'], add.inputs[1])
    coord = add.outputs['Vector']
    # --- 2 couches voronoi distance-to-edge (sillons) ---
    v1 = n.new('ShaderNodeTexVoronoi')
    v1.feature = 'DISTANCE_TO_EDGE'
    v1.inputs['Scale'].default_value = scale
    lk.new(coord, v1.inputs['Vector'])
    v2 = n.new('ShaderNodeTexVoronoi')
    v2.feature = 'DISTANCE_TO_EDGE'
    v2.inputs['Scale'].default_value = scale2
    lk.new(coord, v2.inputs['Vector'])
    r1 = n.new('ShaderNodeValToRGB')
    r1.color_ramp.elements[0].position = 0.0
    r1.color_ramp.elements[1].position = 0.12
    lk.new(v1.outputs['Distance'], r1.inputs['Fac'])
    r2 = n.new('ShaderNodeValToRGB')
    r2.color_ramp.elements[0].position = 0.0
    r2.color_ramp.elements[1].position = 0.20
    lk.new(v2.outputs['Distance'], r2.inputs['Fac'])
    hsum = n.new('ShaderNodeMath')
    hsum.operation = 'MULTIPLY_ADD'   # h = r2*0.45 + r1
    hsum.inputs[1].default_value = 0.45
    lk.new(r2.outputs['Color'], hsum.inputs[0])
    lk.new(r1.outputs['Color'], hsum.inputs[2])
    bmp = n.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = bump
    lk.new(hsum.outputs['Value'], bmp.inputs['Height'])
    lk.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    # --- facteur arête : distance faible = bord de plaque → 1 ---
    edge = n.new('ShaderNodeMapRange')
    edge.inputs['From Min'].default_value = 0.0
    edge.inputs['From Max'].default_value = 0.06
    edge.inputs['To Min'].default_value = 1.0
    edge.inputs['To Max'].default_value = 0.0
    lk.new(v1.outputs['Distance'], edge.inputs['Value'])
    # --- couleur : base charbon → variation par cellule → cuivre sur arêtes ---
    cell = n.new('ShaderNodeTexVoronoi')
    cell.inputs['Scale'].default_value = scale
    lk.new(coord, cell.inputs['Vector'])
    crange = n.new('ShaderNodeMapRange')
    crange.inputs['To Min'].default_value = 0.0
    crange.inputs['To Max'].default_value = 0.18
    lk.new(cell.outputs['Color'], crange.inputs['Value'])
    mix1 = n.new('ShaderNodeMix')
    mix1.data_type = 'RGBA'
    mix1.inputs['A'].default_value = (*base, 1)
    mix1.inputs['B'].default_value = (tint[0] * 0.35, tint[1] * 0.35, tint[2] * 0.35, 1)
    lk.new(crange.outputs['Result'], mix1.inputs['Factor'])
    efac = n.new('ShaderNodeMath')
    efac.operation = 'MULTIPLY'      # cuivre net mais borné sur les arêtes
    efac.inputs[1].default_value = 0.85
    lk.new(edge.outputs['Result'], efac.inputs[0])
    mix2 = n.new('ShaderNodeMix')
    mix2.data_type = 'RGBA'
    mix2.inputs['B'].default_value = (*tint, 1)
    lk.new(mix1.outputs['Result'], mix2.inputs['A'])
    lk.new(efac.outputs['Value'], mix2.inputs['Factor'])
    lk.new(mix2.outputs['Result'], bsdf.inputs['Base Color'])
    # --- roughness plus basse sur les arêtes (reflets cuivrés) ---
    rrange = n.new('ShaderNodeMapRange')
    rrange.inputs['From Min'].default_value = 0.0
    rrange.inputs['From Max'].default_value = 1.0
    rrange.inputs['To Min'].default_value = rough
    rrange.inputs['To Max'].default_value = 0.22
    lk.new(edge.outputs['Result'], rrange.inputs['Value'])
    lk.new(rrange.outputs['Result'], bsdf.inputs['Roughness'])
    _set(bsdf, 'Roughness', rough)
    _set(bsdf, 'Specular Tint', (0.85, 0.4, 0.22, 1.0))
    _set(bsdf, 'Specular IOR Level', 0.35)
    _set(bsdf, 'Anisotropic', 0.25)
    _set(bsdf, 'Sheen Weight', 0.08)
    if sss > 0:  # I4 : diffusion sous-cutanée → chair vivante, pas plastique
        _set(bsdf, 'Subsurface Weight', sss)
        _set(bsdf, 'Subsurface Radius', sss_radius)
        _set(bsdf, 'Subsurface Scale', 0.05)
    return mat


def membrane(name='membrane', color=(0.09, 0.015, 0.012), rough=0.55, transmission=0.3):
    """pattern.membrane_skin : peau fine, transmission rouge visible à contre-jour."""
    mat, nt, bsdf = _new(name)
    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Roughness', rough)
    _set(bsdf, 'Transmission Weight', transmission)
    _set(bsdf, 'Subsurface Weight', 0.35)
    _set(bsdf, 'Subsurface Radius', (0.25, 0.05, 0.03))
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


def rock(name='rock', color=(0.07, 0.055, 0.042), scale=3.0, bump=1.2,
         burnt=(0.012, 0.008, 0.006), ember=(0.28, 0.08, 0.02)):
    """pattern.rock v2 : sol cendré brun-gris chaud, zones brûlées sombres par noise
    large, micro-relief marqué, discrète remontée braise dans les creux."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    # micro-relief
    noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale * 4
    noise.inputs['Detail'].default_value = 12
    noise.inputs['Roughness'].default_value = 0.7
    bmp = n.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = bump
    lk.new(noise.outputs['Fac'], bmp.inputs['Height'])
    lk.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    # grandes zones brûlées sombres
    burn = n.new('ShaderNodeTexNoise')
    burn.inputs['Scale'].default_value = scale * 0.5
    burn.inputs['Detail'].default_value = 5
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.38
    ramp.color_ramp.elements[1].position = 0.62
    lk.new(burn.outputs['Fac'], ramp.inputs['Fac'])
    mix1 = n.new('ShaderNodeMix')
    mix1.data_type = 'RGBA'
    mix1.inputs['A'].default_value = (*color, 1)
    mix1.inputs['B'].default_value = (*burnt, 1)
    lk.new(ramp.outputs['Color'], mix1.inputs['Factor'])
    # légère lueur braise/reflet orangé dans les creux du micro-relief
    eband = n.new('ShaderNodeMapRange')
    eband.inputs['From Min'].default_value = 0.72
    eband.inputs['From Max'].default_value = 0.95
    eband.inputs['To Min'].default_value = 0.0
    eband.inputs['To Max'].default_value = 0.25
    lk.new(noise.outputs['Fac'], eband.inputs['Value'])
    mix2 = n.new('ShaderNodeMix')
    mix2.data_type = 'RGBA'
    mix2.inputs['B'].default_value = (*ember, 1)
    lk.new(mix1.outputs['Result'], mix2.inputs['A'])
    lk.new(eband.outputs['Result'], mix2.inputs['Factor'])
    lk.new(mix2.outputs['Result'], bsdf.inputs['Base Color'])
    _set(bsdf, 'Roughness', 0.85)
    return mat
