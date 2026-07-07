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


def _axis_factor(ng, axis, frm, to, clamp=True):
    """Position (Object space, == monde ici car objets à l'origine) -> composante
    d'axe choisie -> Map Range clampé [frm]->[to]. Retourne la sortie 'Result'.
    Sert à moduler densité/taille d'écaille le long d'une région (cou vs museau)."""
    pos = ng.nodes.new('GeometryNodeInputPosition')
    sep = ng.nodes.new('ShaderNodeSeparateXYZ')
    ng.links.new(pos.outputs['Position'], sep.inputs['Vector'])
    mr = ng.nodes.new('ShaderNodeMapRange')
    mr.clamp = clamp
    mr.inputs['From Min'].default_value = frm[0]
    mr.inputs['From Max'].default_value = frm[1]
    mr.inputs['To Min'].default_value = to[0]
    mr.inputs['To Max'].default_value = to[1]
    idx = {'x': 0, 'y': 1, 'z': 2}[axis.lower()]
    ng.links.new(sep.outputs[idx], mr.inputs['Value'])
    return mr.outputs['Result']


def armor_scales(ob, instance_ob, density=800.0, scale=(0.06, 0.10), seed=1,
                 caudal=(0, -1, 0), curvature=True, realize=True, name='armor',
                 mask=None, scale_grad=None, distance_min=0.0):
    """Écailles-armure chevauchantes (inversion I1). Différence clé avec `scales` :
    densité élevée pour que les plaques se TOUCHENT/chevauchent, et orientation COHÉRENTE
    — Z aligné à la normale de surface puis Y aligné à la direction caudale `caudal`
    (double Align Euler to Vector) : toutes les écailles pointent vers la queue comme
    une vraie peau de reptile. Densité modulée par la courbure (dos dense, ventre clair).

    `mask` optionnel = {'axis','range','to'} : masque positionnel (0..1 clampé) qui
    multiplie la densité — restreint les écailles à une région (ex: cou) sans toucher
    au reste du maillage (évite de dupliquer la géométrie du corps).
    `scale_grad` optionnel = {'axis','range','scale_lo','scale_hi'} : fait varier la
    taille d'écaille en continu le long d'un axe (ex: grandes au cou, fines au museau).
    `distance_min` : espacement Poisson minimal entre écailles — le vrai contrôle du
    chevauchement ordonné (viser ~0.4-0.6x la longueur de plaque) ; `density` reste un
    plafond haut, sans lui `Distance Min` seul suffit à éviter les paquets chaotiques."""
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    n_in, n_out = ng.nodes.new('NodeGroupInput'), ng.nodes.new('NodeGroupOutput')
    dist = ng.nodes.new('GeometryNodeDistributePointsOnFaces')
    dist.distribute_method = 'POISSON'  # espacement régulier → tuilage propre
    dist.inputs['Distance Min'].default_value = distance_min
    dist.inputs['Density Max'].default_value = density
    dist.inputs['Seed'].default_value = seed
    inst = ng.nodes.new('GeometryNodeInstanceOnPoints')
    info = ng.nodes.new('GeometryNodeObjectInfo')
    info.inputs['Object'].default_value = instance_ob
    info.transform_space = 'ORIGINAL'
    rnd = ng.nodes.new('FunctionNodeRandomValue')
    rnd.data_type = 'FLOAT'
    rnd.inputs['Min'].default_value, rnd.inputs['Max'].default_value = scale
    rnd.inputs['Seed'].default_value = seed + 7
    if scale_grad:
        ax, rng = scale_grad['axis'], scale_grad['range']
        lo, hi = scale_grad['scale_lo'], scale_grad['scale_hi']
        out_min = _axis_factor(ng, ax, rng, (lo[0], hi[0]))
        out_max = _axis_factor(ng, ax, rng, (lo[1], hi[1]))
        lk = ng.links.new
        lk(out_min, rnd.inputs['Min'])
        lk(out_max, rnd.inputs['Max'])
    # orientation cohérente : Z←normale, puis Y←caudal
    alignZ = ng.nodes.new('FunctionNodeAlignEulerToVector')
    alignZ.axis = 'Z'
    alignY = ng.nodes.new('FunctionNodeAlignEulerToVector')
    alignY.axis = 'Y'
    alignY.pivot_axis = 'Z'
    caud = ng.nodes.new('FunctionNodeInputVector')
    caud.vector = caudal
    join = ng.nodes.new('GeometryNodeJoinGeometry')
    lk = ng.links.new
    dens_factor = None
    if curvature:
        ang = ng.nodes.new('GeometryNodeInputMeshEdgeAngle')
        mr = ng.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = -0.6
        mr.inputs['From Max'].default_value = 0.6
        mr.inputs['To Min'].default_value = density * 0.35
        mr.inputs['To Max'].default_value = density
        lk(ang.outputs['Signed Angle'], mr.inputs['Value'])
        dens_factor = mr.outputs['Result']
    if mask:
        mfac = _axis_factor(ng, mask['axis'], mask['range'], mask.get('to', (0.0, 1.0)))
        if dens_factor is not None:
            mul = ng.nodes.new('ShaderNodeMath')
            mul.operation = 'MULTIPLY'
            lk(dens_factor, mul.inputs[0])
            lk(mfac, mul.inputs[1])
            dens_factor = mul.outputs['Value']
        else:
            dens_factor = mfac
    if dens_factor is not None:
        lk(dens_factor, dist.inputs['Density Factor'])
    lk(n_in.outputs['Geometry'], dist.inputs['Mesh'])
    lk(dist.outputs['Normal'], alignZ.inputs['Vector'])
    lk(alignZ.outputs['Rotation'], alignY.inputs['Rotation'])
    lk(caud.outputs['Vector'], alignY.inputs['Vector'])
    lk(dist.outputs['Points'], inst.inputs['Points'])
    lk(alignY.outputs['Rotation'], inst.inputs['Rotation'])
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


def keeled_scale(name='keeled_scale', size=1.0, length=1.6, keel=0.5, lift=0.35, smooth=True):
    """Écaille CARÉNÉE réaliste (inversion I1) : plaque allongée cranio-caudale, arête
    centrale (keel) qui capte la lumière, bord caudal relevé (`lift`) pour chevaucher la
    voisine. C'est la géométrie qui fait « lire » l'écaille en macro, pas le bruit.
    Repère : +Y = caudal (vers la queue), Z = hauteur relief. length allonge vers l'arrière.
    `smooth=False` : ombrage plat — conserve les facettes dures de la carène/pointe pour
    que le relief se lise à distance (même matériau que la peau, sans le bruit shader)."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    w = size * 0.5
    L = size * length
    # 6 verts : pointe caudale relevée, épaules, base cranio (sous la voisine), sommet keel
    tip = bm.verts.new((0, L * 0.5, size * lift))          # bord arrière relevé
    shL = bm.verts.new((-w, 0, size * 0.05))
    shR = bm.verts.new((w, 0, size * 0.05))
    baseL = bm.verts.new((-w * 0.55, -L * 0.5, -size * 0.04))
    baseR = bm.verts.new((w * 0.55, -L * 0.5, -size * 0.04))
    crest = bm.verts.new((0, -L * 0.02, size * keel))      # sommet de l'arête
    for tri in [(baseL, baseR, crest), (baseR, shR, crest), (shR, tip, crest),
                (tip, shL, crest), (shL, baseL, crest)]:
        bm.faces.new(tri)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    core.link(ob)
    return core.shade_smooth(ob) if smooth else ob


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
