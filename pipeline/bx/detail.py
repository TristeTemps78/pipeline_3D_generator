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
                 mask=None, scale_grad=None, distance_min=0.0,
                 index_grad=None, index_noise=(3.0, 1.4), rot_jitter=0.0,
                 store_seed=False):
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
    plafond haut, sans lui `Distance Min` seul suffit à éviter les paquets chaotiques.

    Architecture détail (T11+T12, research/detail_architecture.md) :
    `instance_ob` peut être une LISTE d'archétypes → Pick Instance par index, avec
    `index_grad` = {'axis','range'} : gradient spatial → index 0..n-1, bruit
    `index_noise` = (échelle, amplitude) ajouté AVANT l'arrondi → frontières de régions
    ditherées (pas de lignes) ; sans `index_grad`, archétype aléatoire par point.
    `rot_jitter` (rad) : rotation Z aléatoire par instance. `store_seed` : écrit
    l'attribut float 'scale_seed' (domaine INSTANCE, aléatoire 0-1) — lu côté shader
    par Attribute type Instancer pour un micro unique par écaille, à condition de NE
    PAS réaliser (T12 : l'attribut meurt au Realize Instances). `realize=False` +
    `store_seed=True` = couche MESO+MICRO complète à coût mémoire quasi nul.

    La distribution se fait sur le SEUL composant mesh de l'entrée (Separate
    Components) : plusieurs modifiers d'armure empilés sur un même objet ne se
    voient pas entre eux — sans ça, chaque entrée sème des écailles SUR les plaques
    des entrées précédentes (les masques sont des rampes clampées, pas des bandes)
    et le nombre d'instances explose de façon combinatoire (OOM constaté : 272k
    instances dès la 2e entrée, mémoire infinie à la 5e)."""
    plates = list(instance_ob) if isinstance(instance_ob, (list, tuple)) else [instance_ob]
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
    lk = ng.links.new
    # bibliothèque d'archétypes : chaque plaque devient UNE instance distincte
    if len(plates) > 1:
        geo2inst = ng.nodes.new('GeometryNodeGeometryToInstance')
        for p in plates:
            info = ng.nodes.new('GeometryNodeObjectInfo')
            info.inputs['Object'].default_value = p
            info.transform_space = 'ORIGINAL'
            lk(info.outputs['Geometry'], geo2inst.inputs['Geometry'])
        lk(geo2inst.outputs['Instances'], inst.inputs['Instance'])
        inst.inputs['Pick Instance'].default_value = True
        nmax = float(len(plates) - 1)
        if index_grad:
            # gradient spatial -> 0..n-1, bruit ajouté AVANT l'arrondi = dither
            base_idx = _axis_factor(ng, index_grad['axis'], index_grad['range'],
                                    (0.0, nmax))
            noise = ng.nodes.new('ShaderNodeTexNoise')
            noise.inputs['Scale'].default_value = index_noise[0]
            ctr = ng.nodes.new('ShaderNodeMath')
            ctr.operation = 'SUBTRACT'
            ctr.inputs[1].default_value = 0.5
            lk(noise.outputs['Fac'], ctr.inputs[0])
            amp = ng.nodes.new('ShaderNodeMath')
            amp.operation = 'MULTIPLY'
            amp.inputs[1].default_value = index_noise[1]
            lk(ctr.outputs['Value'], amp.inputs[0])
            addn = ng.nodes.new('ShaderNodeMath')
            addn.operation = 'ADD'
            lk(base_idx, addn.inputs[0])
            lk(amp.outputs['Value'], addn.inputs[1])
            clampn = ng.nodes.new('ShaderNodeClamp')
            clampn.inputs['Min'].default_value = 0.0
            clampn.inputs['Max'].default_value = nmax
            lk(addn.outputs['Value'], clampn.inputs['Value'])
            to_int = ng.nodes.new('FunctionNodeFloatToInt')
            to_int.rounding_mode = 'ROUND'
            lk(clampn.outputs['Result'], to_int.inputs['Float'])
            lk(to_int.outputs['Integer'], inst.inputs['Instance Index'])
        else:
            rnd_idx = ng.nodes.new('FunctionNodeRandomValue')
            rnd_idx.data_type = 'INT'
            rnd_idx.inputs['Min'].default_value = 0
            rnd_idx.inputs['Max'].default_value = len(plates) - 1
            rnd_idx.inputs['Seed'].default_value = seed + 31
            lk(rnd_idx.outputs['Value'], inst.inputs['Instance Index'])
    else:
        info = ng.nodes.new('GeometryNodeObjectInfo')
        info.inputs['Object'].default_value = plates[0]
        info.transform_space = 'ORIGINAL'
        lk(info.outputs['Geometry'], inst.inputs['Instance'])
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
    sepc = ng.nodes.new('GeometryNodeSeparateComponents')
    lk(n_in.outputs['Geometry'], sepc.inputs['Geometry'])
    lk(sepc.outputs['Mesh'], dist.inputs['Mesh'])
    lk(dist.outputs['Normal'], alignZ.inputs['Vector'])
    lk(alignZ.outputs['Rotation'], alignY.inputs['Rotation'])
    lk(caud.outputs['Vector'], alignY.inputs['Vector'])
    lk(dist.outputs['Points'], inst.inputs['Points'])
    lk(alignY.outputs['Rotation'], inst.inputs['Rotation'])
    lk(rnd.outputs['Value'], inst.inputs['Scale'])
    lk(n_in.outputs['Geometry'], join.inputs['Geometry'])
    tail = inst.outputs['Instances']
    if rot_jitter:
        rot = ng.nodes.new('GeometryNodeRotateInstances')
        rnd_rot = ng.nodes.new('FunctionNodeRandomValue')
        rnd_rot.data_type = 'FLOAT_VECTOR'
        rnd_rot.inputs['Min'].default_value = (0, 0, -rot_jitter)
        rnd_rot.inputs['Max'].default_value = (0, 0, rot_jitter)
        rnd_rot.inputs['Seed'].default_value = seed + 13
        lk(tail, rot.inputs['Instances'])
        lk(rnd_rot.outputs['Value'], rot.inputs['Rotation'])
        tail = rot.outputs['Instances']
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
    lk(tail, join.inputs['Geometry'])
    lk(join.outputs['Geometry'], n_out.inputs['Geometry'])
    mod = ob.modifiers.new(name, 'NODES')
    mod.node_group = ng
    for p in plates:
        p.hide_render = True
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


def archetype(name, kind='keeled', size=1.0, squash=None, **kw):
    """Plaque canonique d'une famille d'écailles (couche MESO, T11) : 'keeled'
    (carénée — kw: length/keel/lift/smooth) ou 'plate' (losange bombé). `squash`
    = (sx, sy, sz) baké DANS les vertices : Object Info en transform_space ORIGINAL
    ignore le transform objet, un scale objet serait silencieusement perdu."""
    if kind == 'plate':
        ob = scale_plate(name, size=size)
    else:
        ob = keeled_scale(name, size=size, **kw)
    if squash:
        for v in ob.data.vertices:
            v.co.x *= squash[0]
            v.co.y *= squash[1]
            v.co.z *= squash[2]
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
