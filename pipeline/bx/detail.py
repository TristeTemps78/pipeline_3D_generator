"""bx.detail — micro-détail géométrique sans sculpt (convergences C4+C5 des deux docs).
C4 : couches de Displace (macro plis / écailles moyennes / micro rides) sur mesh subdivisé.
C5 : écailles explicites par Geometry Nodes — Distribute Points on Faces + Instance on
Points, densité pilotée par la courbure (Edge Angle). Tout est numérique, piloté par la spec."""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import core, materials, ops


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
    """Position OU normale (Object space, == monde ici car objets à l'origine) ->
    composante d'axe choisie -> Map Range clampé [frm]->[to]. Retourne la sortie
    'Result'. Axes 'x'/'y'/'z' : le long d'une région (cou vs museau, cranio-caudal).
    Axes 'nx'/'ny'/'nz' (RADIAL, générique) : composante de la NORMALE de surface —
    'nz' proche de +1 = face qui regarde le haut (dos), proche de -1 = regarde le bas
    (ventre). Ne dépend PAS de la position le long de la pièce ni d'un centre de tube
    à calculer : marche sur n'importe quelle section (corps, cou, queue) sans
    connaître la courbe de la spine — c'est la façon la moins chère d'obtenir une
    variation dorsale/ventrale cohérente sur un tube organique."""
    axis = axis.lower()
    if axis.startswith('n'):
        src = ng.nodes.new('GeometryNodeInputNormal')
        out_socket = src.outputs['Normal']
        idx = {'x': 0, 'y': 1, 'z': 2}[axis[1]]
    else:
        src = ng.nodes.new('GeometryNodeInputPosition')
        out_socket = src.outputs['Position']
        idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    sep = ng.nodes.new('ShaderNodeSeparateXYZ')
    ng.links.new(out_socket, sep.inputs['Vector'])
    mr = ng.nodes.new('ShaderNodeMapRange')
    mr.clamp = clamp
    mr.inputs['From Min'].default_value = frm[0]
    mr.inputs['From Max'].default_value = frm[1]
    mr.inputs['To Min'].default_value = to[0]
    mr.inputs['To Max'].default_value = to[1]
    ng.links.new(sep.outputs[idx], mr.inputs['Value'])
    return mr.outputs['Result']


def _near_factor(ng, locs, radius=0.15, falloff=0.12):
    """Masque de proximité générique (boucle 18, T1 : « couronnes orbitales/
    maxillaires ») : distance MINIMALE de chaque point de surface à un point OU une
    liste de points (approxime un segment/ligne — ex. une ligne de mâchoire — en
    donnant plusieurs points échantillonnés le long de celle-ci, sans dépendre de la
    topologie de la pièce) -> facteur 1.0 dans `radius`, dégradé LINÉAIRE à 0.0 sur
    `falloff` au-delà. Mêmes coordonnées que `_axis_factor` (Position node, locales
    == monde si l'objet est à l'origine, cf. pitfall claude.md). Réutilisable pour
    toute zone circulaire/allongée (orbite, arête de mâchoire, griffe...)."""
    pts = locs if isinstance(locs[0], (list, tuple)) else [locs]
    pos = ng.nodes.new('GeometryNodeInputPosition')
    lk = ng.links.new
    dist_out = None
    for p in pts:
        const = ng.nodes.new('FunctionNodeInputVector')
        const.vector = tuple(p)
        sub = ng.nodes.new('ShaderNodeVectorMath')
        sub.operation = 'SUBTRACT'
        lk(pos.outputs['Position'], sub.inputs[0])
        lk(const.outputs['Vector'], sub.inputs[1])
        length = ng.nodes.new('ShaderNodeVectorMath')
        length.operation = 'LENGTH'
        lk(sub.outputs['Vector'], length.inputs[0])
        d = length.outputs['Value']
        if dist_out is None:
            dist_out = d
        else:
            mn = ng.nodes.new('ShaderNodeMath')
            mn.operation = 'MINIMUM'
            lk(dist_out, mn.inputs[0])
            lk(d, mn.inputs[1])
            dist_out = mn.outputs['Value']
    mr = ng.nodes.new('ShaderNodeMapRange')
    mr.clamp = True
    mr.inputs['From Min'].default_value = radius
    mr.inputs['From Max'].default_value = radius + max(falloff, 1e-4)
    mr.inputs['To Min'].default_value = 1.0
    mr.inputs['To Max'].default_value = 0.0
    lk(dist_out, mr.inputs['Value'])
    return mr.outputs['Result']


def armor_scales(ob, instance_ob, density=800.0, scale=(0.06, 0.10), seed=1,
                 caudal=(0, -1, 0), curvature=True, realize=True, name='armor',
                 mask=None, mask_radial=None, mask_near=None, mask_near_avoid=None,
                 scale_grad=None, distance_min=0.0,
                 index_grad=None, index_noise=(3.0, 1.4), rot_jitter=0.0,
                 store_seed=False, scale_noise=None):
    """Écailles-armure chevauchantes (inversion I1). Différence clé avec `scales` :
    densité élevée pour que les plaques se TOUCHENT/chevauchent, et orientation COHÉRENTE
    — Z aligné à la normale de surface puis Y aligné à la direction caudale `caudal`
    (double Align Euler to Vector) : toutes les écailles pointent vers la queue comme
    une vraie peau de reptile. Densité modulée par la courbure (dos dense, ventre clair).

    `mask` optionnel = {'axis','range','to'} : masque positionnel (0..1 clampé) qui
    multiplie la densité — restreint les écailles à une région (ex: cou) sans toucher
    au reste du maillage (évite de dupliquer la géométrie du corps).
    `mask_radial` optionnel = même forme que `mask` mais `axis` peut être 'nx'/'ny'/'nz'
    (composante de la NORMALE, cf. `_axis_factor`) : variation DORSALE/VENTRALE générique
    sans connaître le centre local du tube — se MULTIPLIE avec `mask` (combinable, zones
    cranio-caudales × dorsal/ventral). Typiquement `{'axis':'nz','range':(-0.5,0.6),
    'to':(0,1)}` : dos (nz haut) dense, ventre (nz bas) clairsemé, ou l'inverse selon `to`.
    `scale_grad` optionnel = {'axis','range','scale_lo','scale_hi'} : fait varier la
    taille d'écaille en continu le long d'un axe (ex: grandes au cou, fines au museau) ;
    `axis` accepte aussi 'nz' pour opposer grandes plaques ventrales / petites carènes
    dorsales sans zone explicite.
    `scale_noise` optionnel = (échelle_basse_freq, amplitude 0..1) : bruit multiplicatif
    sur la taille finale de l'instance (indépendant de `scale_grad`) — casse l'uniformité
    en patchs organiques d'écailles plus grosses/petites (pas de bande nette, une texture).
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
    for m in (mask, mask_radial):
        if not m:
            continue
        mfac = _axis_factor(ng, m['axis'], m['range'], m.get('to', (0.0, 1.0)))
        if dens_factor is not None:
            mul = ng.nodes.new('ShaderNodeMath')
            mul.operation = 'MULTIPLY'
            lk(dens_factor, mul.inputs[0])
            lk(mfac, mul.inputs[1])
            dens_factor = mul.outputs['Value']
        else:
            dens_factor = mfac
    if mask_near:
        # UNION des zones de proximité (orbite OU ligne de mâchoire...) : MAXIMUM
        # entre elles, puis ce résultat se MULTIPLIE avec le reste (curvature/mask/
        # mask_radial) comme un masque de plus, cohérent avec la combinatoire existante.
        near_factor = None
        for nm in mask_near:
            nfac = _near_factor(ng, nm['loc'], nm.get('radius', 0.15), nm.get('falloff', 0.12))
            if near_factor is None:
                near_factor = nfac
            else:
                mx = ng.nodes.new('ShaderNodeMath')
                mx.operation = 'MAXIMUM'
                lk(near_factor, mx.inputs[0])
                lk(nfac, mx.inputs[1])
                near_factor = mx.outputs['Value']
        if dens_factor is not None:
            mul = ng.nodes.new('ShaderNodeMath')
            mul.operation = 'MULTIPLY'
            lk(dens_factor, mul.inputs[0])
            lk(near_factor, mul.inputs[1])
            dens_factor = mul.outputs['Value']
        else:
            dens_factor = near_factor
    if mask_near_avoid:
        # INVERSE de `mask_near` (boucle 18, T1 : « couronnes » englouties par
        # l'armure fine environnante) : éclaircit (réduit la densité) autour des
        # mêmes zones plutôt que de les réserver -> laisse de la place visuelle aux
        # grosses plaques d'une AUTRE entrée d'armure ciblant la même zone, sans
        # créer de trou net (dégradé via le même `falloff`).
        avoid_factor = None
        for nm in mask_near_avoid:
            nfac = _near_factor(ng, nm['loc'], nm.get('radius', 0.15), nm.get('falloff', 0.12))
            if avoid_factor is None:
                avoid_factor = nfac
            else:
                mx = ng.nodes.new('ShaderNodeMath')
                mx.operation = 'MAXIMUM'
                lk(avoid_factor, mx.inputs[0])
                lk(nfac, mx.inputs[1])
                avoid_factor = mx.outputs['Value']
        inv = ng.nodes.new('ShaderNodeMath')
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        lk(avoid_factor, inv.inputs[1])
        if dens_factor is not None:
            mul = ng.nodes.new('ShaderNodeMath')
            mul.operation = 'MULTIPLY'
            lk(dens_factor, mul.inputs[0])
            lk(inv.outputs['Value'], mul.inputs[1])
            dens_factor = mul.outputs['Value']
        else:
            dens_factor = inv.outputs['Value']
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
    scale_out = rnd.outputs['Value']
    if scale_noise:
        freq, amp = scale_noise
        noise = ng.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = freq
        nmr = ng.nodes.new('ShaderNodeMapRange')
        nmr.inputs['From Min'].default_value = 0.0
        nmr.inputs['From Max'].default_value = 1.0
        nmr.inputs['To Min'].default_value = 1.0 - amp
        nmr.inputs['To Max'].default_value = 1.0 + amp
        lk(noise.outputs['Fac'], nmr.inputs['Value'])
        nmul = ng.nodes.new('ShaderNodeMath')
        nmul.operation = 'MULTIPLY'
        lk(scale_out, nmul.inputs[0])
        lk(nmr.outputs['Result'], nmul.inputs[1])
        scale_out = nmul.outputs['Value']
    lk(scale_out, inst.inputs['Scale'])
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


def write_axis_uv(ob, path_world, name='axis_uv', n_samples=40, chunk=20000):
    """Écrit un attribut vertex `axis_uv` (Vector, domaine POINT) GÉNÉRIQUE
    (chantier B, boucle 19, faute F4 : « texture appliquée en calque global
    uniforme au lieu de varier selon l'anatomie ») : u = abscisse curviligne
    normalisée 0..1 le long de `path_world` (polyligne monde, ex. `pts` de
    spine/limb), v = angle 0..1 autour de la section locale (repère transporté
    rotation-minimizing, `ops.sample_path_frames` — même repère que
    `_anatomical_tube`). Dérivé UNIQUEMENT de la position monde du sommet par
    rapport à l'échantillon de chemin le plus proche (nearest-neighbour vectorisé
    numpy) : ne dépend d'AUCUN attribut de construction -> reste valide même après
    une fusion SDF qui reconstruit entièrement la topologie (`fuse.sdf_fuse`).
    Exposé aux shaders (Attribute node domaine GEOMETRY, nom 'axis_uv', cf.
    `materials.reptile_scales axis_uv=True`) pour orienter/étirer le motif
    d'écailles le long de l'axe anatomique plutôt qu'un bruit isotrope."""
    if ob.type != 'MESH' or not path_world or len(path_world) < 2:
        return ob
    verts = ob.data.vertices
    n_v = len(verts)
    if n_v == 0:
        return ob
    positions, rights, ups, _, _ = ops.sample_path_frames(path_world, n_samples)
    samp = np.array([(p.x, p.y, p.z) for p in positions])
    rmat = np.array([(r.x, r.y, r.z) for r in rights])
    umat = np.array([(u.x, u.y, u.z) for u in ups])
    mw = np.array(ob.matrix_world)
    co = np.empty(n_v * 3, dtype=np.float64)
    verts.foreach_get('co', co)
    co = co.reshape(n_v, 3)
    pos = co @ mw[:3, :3].T + mw[:3, 3]
    out_uv = np.zeros((n_v, 3), dtype=np.float64)
    for start in range(0, n_v, chunk):
        end = min(n_v, start + chunk)
        blk = pos[start:end]
        d2 = ((blk[:, None, :] - samp[None, :, :]) ** 2).sum(axis=2)
        idx = d2.argmin(axis=1)
        offset = blk - samp[idx]
        x = (offset * rmat[idx]).sum(axis=1)
        y = (offset * umat[idx]).sum(axis=1)
        out_uv[start:end, 0] = idx / max(1, n_samples - 1)
        out_uv[start:end, 1] = (np.arctan2(y, x) / (2 * np.pi)) % 1.0
    attr = ob.data.attributes.get(name) or ob.data.attributes.new(name, 'FLOAT_VECTOR', 'POINT')
    attr.data.foreach_set('vector', out_uv.ravel())
    ob.data.update()
    return ob


def _lerp_field(pairs, u):
    """Interpolation linéaire générique le long d'une liste [(u, valeur), ...]
    triée par u, clampée aux extrémités — champ continu de taille/zone piloté par
    la spec (`armor_rows` scale_u), sans dépendre de `organic._interp_scalar`
    (évite un import croisé)."""
    if not pairs:
        return 1.0
    pairs = sorted(pairs, key=lambda p: p[0])
    if u <= pairs[0][0]:
        return pairs[0][1]
    if u >= pairs[-1][0]:
        return pairs[-1][1]
    for (u0, v0), (u1, v1) in zip(pairs, pairs[1:]):
        if u0 <= u <= u1:
            f = (u - u0) / max(u1 - u0, 1e-9)
            return v0 + f * (v1 - v0)
    return pairs[-1][1]


def armor_rows(ob, plates, path_world, mat_default, rows=20, cols=10,
              v_range=(0.08, 0.92), quincunx=0.5, u_range=(0.0, 1.0),
              scale_u=None, joint_u=None, joint_width=0.06, joint_dip=0.55,
              flank_falloff=0.45, size=(0.09, 0.14), jitter=0.15,
              rot_jitter=0.12, search_dist=None, seed=1, name='armor_rows'):
    """Rangées régulières d'écailles/plaques qui SUIVENT LA COURBURE d'un tube
    anatomique (spine/limb) — chantier B, boucle 19, faute F4 : remplace le semis
    Poisson isotrope (`armor_scales`, conservé comme fallback pour les entrées
    sans `layout`) par un motif ORDONNÉ en rangées, décalées en QUINCONCE une
    rangée sur deux, tailles en CHAMP CONTINU piloté par zone (grandes/épaisses
    au dos, petites/resserrées vers le ventre et les articulations) au lieu d'une
    densité Poisson uniforme.

    Ne dépend PAS d'un attribut Geometry Nodes : chaque rangée est un échantillon
    de `path_world` (repère transporté rotation-minimizing, `ops.sample_path_frames`
    — le MÊME repère que `organic._anatomical_tube`), projeté sur la VRAIE surface
    de `ob` par un raycast (BVH construit sur le mesh de BASE, sans modifiers) le
    long de la normale locale -> reste correct même après une fusion SDF qui
    déforme légèrement le rayon nominal du tube d'origine.

    `scale_u` : liste [(u, multiplicateur), ...] interpolée linéairement (`_lerp_field`)
    -> zone dorsale (u proche du centre du tronc) grande/épaisse, extrémités
    (queue/cou, ou hanche/cheville) petites. `joint_u` : liste de fractions u où la
    taille plonge localement (gaussienne `joint_width`/`joint_dip`) -> resserré aux
    articulations. `flank_falloff` (0..1) réduit la taille en s'éloignant du sommet
    dorsal (theta=0, haut de `v_range`) vers les bords -> grosses plaques dorsales,
    plus petites sur le flanc. `v_range` (fraction de tour complet, 0.5=dos) exclut
    par défaut une bande ventrale étroite (bords proches de 0/1) : le ventre reste
    lisse/au semis existant, cf. `claude.md` doctrine.

    Les plaques instanciées sont dupliquées/transformées en pur Python et jointes
    en UN SEUL mesh (budget : ni un objet Blender par plaque, ni un modifier GN
    Poisson supplémentaire — la géométrie de plaque est réutilisée directement)."""
    plates = list(plates) if isinstance(plates, (list, tuple)) else [plates]
    if ob.type != 'MESH' or len(path_world) < 2:
        return None
    positions, rights, ups, tangents, _ = ops.sample_path_frames(path_world, max(rows * 3, 64))
    n_samp = len(positions)
    # BVH sur le mesh de BASE (ob.data), SANS évaluer les modifiers déjà présents
    # (ex. d'autres entrées d'armure Poisson ajoutées sur le même objet) — on veut
    # la vraie surface du corps/membre, pas la géométrie instanciée par-dessus.
    bm_src = bmesh.new()
    bm_src.from_mesh(ob.data)
    bm_src.transform(ob.matrix_world)
    bvh = BVHTree.FromBMesh(bm_src)
    bm_src.free()
    if search_dist is None:
        bb = [ob.matrix_world @ Vector(v) for v in ob.bound_box]
        search_dist = max(max(v[k] for v in bb) - min(v[k] for v in bb) for k in range(3)) * 0.6
    search_dist = max(search_dist, 0.05)

    def sample_at(u):
        d = u * (n_samp - 1)
        i = max(0, min(n_samp - 2, int(d)))
        f = d - i
        idx = i if f < 0.5 else i + 1
        return positions[idx], rights[idx], ups[idx], tangents[idx]

    def scale_field(u):
        m = _lerp_field(scale_u, u) if scale_u else 1.0
        if joint_u:
            for ju in joint_u:
                d = (u - ju) / max(joint_width, 1e-4)
                m *= 1.0 - joint_dip * math.exp(-0.5 * d * d)
        return m

    rng = random.Random(seed)
    bm = bmesh.new()
    plate_bms = []
    for p in plates:
        pb = bmesh.new()
        pb.from_mesh(p.data)
        plate_bms.append(pb)
    u0, u1 = u_range
    placed = 0
    # FIX régression boucle 19 (step_238_head) : plaques flottantes près de la
    # gorge/mâchoire. Le raycast part de très loin (`search_dist` ~ 0.6x la
    # bbox) donc un manque local (trou, pli concave près d'une jonction
    # corps/tête) le laisse traverser et toucher une surface ÉLOIGNÉE et sans
    # rapport (repliée ailleurs sur le même mesh) : la plaque est bien "sur"
    # le maillage mais visuellement détachée, un trou noir tout autour.
    # Détection : le rayon local (distance p0->hit le long de `dirn`, via la
    # distance de ray_cast qu'on ignorait avant) doit varier PEU d'une colonne
    # à l'autre le long d'un même anneau/rangée (surface organique lisse) ;
    # un saut > RADIUS_JUMP (~0.15u) = échantillon aberrant -> rejeté, comme un
    # raté de raycast pur (pas de reprojection/clamp : on préfère un trou dans
    # le semis à une plaque mal posée).
    RADIUS_JUMP = 0.15
    row_col_r = [None] * cols   # dernier rayon accepté à cette colonne (rangée précédente)
    for ri in range(rows):
        u = u0 + (u1 - u0) * (ri / max(1, rows - 1))
        p0, rgt, up, tan = sample_at(u)
        offs = 0.5 if (quincunx and ri % 2 == 1) else 0.0
        prev_row_r = None   # dernier rayon accepté dans CETTE rangée (colonne précédente)
        for ci in range(cols):
            frac = ((ci + offs) / cols) % 1.0
            vfrac = v_range[0] + (v_range[1] - v_range[0]) * frac
            theta = -math.pi + vfrac * 2 * math.pi
            dirn = (up * math.cos(theta) + rgt * math.sin(theta))
            if dirn.length < 1e-6:
                continue
            dirn.normalize()
            origin = p0 + dirn * search_dist
            loc, hn, _, hit_dist = bvh.ray_cast(origin, -dirn, search_dist * 2.2)
            if loc is None:
                continue
            if hn.dot(dirn) < 0.2:   # bord/jonction quasi tangente -> évite un placement en biseau
                continue
            r_local = search_dist - hit_dist   # distance p0->surface le long de dirn (rayon local)
            ref = prev_row_r if prev_row_r is not None else row_col_r[ci]
            if ref is not None and abs(r_local - ref) > RADIUS_JUMP:
                continue   # rayon aberrant (surface éloignée sans rapport) -> pas de plaque
            prev_row_r = r_local
            row_col_r[ci] = r_local
            flank = abs(vfrac - 0.5) * 2.0
            s = size[0] + (size[1] - size[0]) * rng.random()
            s *= scale_field(u)
            s *= max(0.15, 1.0 - flank_falloff * flank)
            s *= 1.0 + jitter * (rng.random() * 2 - 1)
            tproj = tan - hn * tan.dot(hn)
            if tproj.length < 1e-6:
                tproj = rgt - hn * rgt.dot(hn)
            if tproj.length < 1e-6:
                continue
            tproj.normalize()
            xax = tproj.cross(hn)
            if xax.length < 1e-6:
                continue
            xax.normalize()
            rot = (rng.random() * 2 - 1) * rot_jitter
            c, sn = math.cos(rot), math.sin(rot)
            xax2 = xax * c + tproj * sn
            yax2 = -xax * sn + tproj * c
            xfm = Matrix((
                (xax2.x * s, yax2.x * s, hn.x * s, loc.x),
                (xax2.y * s, yax2.y * s, hn.y * s, loc.y),
                (xax2.z * s, yax2.z * s, hn.z * s, loc.z),
                (0.0, 0.0, 0.0, 1.0)))
            pk = plate_bms[int(rng.random() * len(plate_bms)) % len(plate_bms)]
            vmap = {}
            for v in pk.verts:
                vmap[v] = bm.verts.new(xfm @ v.co)
            for f in pk.faces:
                try:
                    bm.faces.new([vmap[v] for v in f.verts])
                except ValueError:
                    pass
            placed += 1
    for pb in plate_bms:
        pb.free()
    for p in plates:
        p.hide_render = True
    if placed == 0:
        bm.free()
        return None
    bm.normal_update()
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    new_ob = bpy.data.objects.new(name, mesh)
    core.link(new_ob)
    core.shade_smooth(new_ob)
    materials.assign(new_ob, mat_default)
    return new_ob
