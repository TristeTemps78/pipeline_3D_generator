"""bx.materials — shaders procéduraux paramétrés par le vocabulaire GVL."""
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _resolve(path):
    """Chemins de maps bakées (`normal_map`/`ao_map`/`curvature_map`) relatifs à la
    RACINE du dépôt (convention `maps/<spec>_<group>_<map>.png` de bx.bake) — marche
    quel que soit le cwd d'où `run.py` est invoqué, pas seulement depuis la racine."""
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def _load_data_image(path):
    """Charge une map bakée en colorspace Non-Color. Tolère l'ABSENCE du fichier
    (retourne None, avertit sur stderr) : la commande `bake` construit la scène (donc
    les matériaux, donc ces chemins) AVANT que les maps existent au premier lancement
    sur un dépôt neuf -> sans ce filet, `run.py bake` ne pourrait jamais bootstrapper.
    Rétro-compat : chemin absent/introuvable = comportement procédural pur (v2)."""
    full = _resolve(path)
    if not os.path.exists(full):
        print(f"materials: map bakée introuvable ({full}), ignorée (procédural pur)")
        return None
    img = bpy.data.images.load(full)
    img.colorspace_settings.name = 'Non-Color'
    return img


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
                   scale=5, scale2=16, bump=1.2, rough=0.5, rough_edge=0.1, warp=0.3,
                   sss=0.0, sss_radius=(0.32, 0.11, 0.06), micro=0.0,
                   edge_copper=0.68, edge_width=0.045, instance_variation=0.0,
                   patina_color=(0.15, 0.32, 0.24),
                   patina_gold=(0.6, 0.38, 0.13), patina_amount=0.0,
                   normal_map=None, normal_map_strength=1.0,
                   ao_map=None, ao_strength=0.35,
                   curvature_map=None, curvature_mix=0.6,
                   axis_uv=False, axis_uv_stretch=2.4, scale_axis=None,
                   spec_level=0.55, sheen=0.08, aniso=0.3,
                   specular_tint=(0.6, 0.46, 0.36)):
    """pattern.reptile_scales v3 (audit boucle 17, CR1 « charbon/rouge ») : 2 voronoi
    distance-to-edge superposés (plaques + micro-écailles) sur coordonnées Object
    distordues par noise (casse la grille ; Object car les curves n'ont pas de Generated
    fiable) ; `base` (creux, quasi-noir) → `tint` (arêtes, rouge-cuivre saturé) via le
    masque de cavité `edge` (Distance to Edge du voronoi macro : 0 au centre de plaque,
    1 sur le sillon) — c'est CE mélange qui doit lire « charbon + rouge », pas une teinte
    globale. Échelles en cellules par unité monde (~scale 5 → plaques de 20 cm).
    `rough_edge` : roughness sur l'arête/carène (bas = spéculaire, capte le rim dur) ;
    `rough` reste la roughness des creux (haut = mat). Contraste fort entre les deux =
    « pointes highlights » sous rim, sans bruit shader ajouté.
    `instance_variation` (0..1, défaut 0 = inchangé) : variation TEINTE/VALEUR/ROUGHNESS
    par écaille — chantier CR1 (« aucune écaille visible » car uniforme). Priorité à un
    vrai attribut d'instance si la géométrie en fournit un (`micro`>0 + `store_seed` côté
    detail.armor_scales, cf. ci-dessous) ; à défaut repli GÉNÉRIQUE sur le hash pseudo-
    aléatoire par cellule du voronoi macro déjà calculé (`cell`, même grille que les
    plaques) — fonctionne même quand les écailles sont RÉALISÉES en un seul mesh joint
    (cas actuel de `detail.armor_scales`, `realize=True` par défaut), donc sans dépendre
    d'un flag géométrie. Assombrit/éclaircit chaque écaille (valeur), élargit l'écart de
    roughness plaque à plaque (certaines plus mates, d'autres plus polies) : lu comme
    « chaque écaille est différente » à distance, condition posée par l'audit CR1.
    `micro` > 0 (T12, couche MICRO) : lit l'attribut d'instance 'scale_seed' (Attribute
    type Instancer, écrit par detail.armor_scales store_seed) → chaque écaille instanciée
    décale l'origine du voronoi micro (v2 en 4D, W par seed) et éclaircit sa base de
    `micro`×seed — variation unique par plaque SANS réaliser les instances. Sur une
    géométrie non instanciée l'attribut vaut 0 → matériau inchangé.
    `axis_uv` (chantier B, boucle 19, faute F4 : « filtre terre craquelée procédural
    ARTIFICIEL UNIFORME », « pattes = texture papier peint sans tenir compte des
    volumes ») : quand True, remplace la coordonnée Object isotrope par l'attribut
    mesh `axis_uv` (u=abscisse curviligne, v=angle de section, écrit par
    `detail.write_axis_uv` le long de l'axe anatomique réel de la pièce) ÉTIRÉ par
    `axis_uv_stretch` sur l'axe u -> cellules Voronoi ALLONGÉES le long de l'axe
    (écailles qui suivent la forme du membre/du dos, pas un bruit isotrope plaqué).
    Sans l'attribut sur le mesh (pièce non couverte par `write_axis_uv`), l'Attribute
    node renvoie (0,0,0) -> rétro-compat : `axis_uv=False` (défaut) laisse le
    comportement Object-space v3 inchangé pour tous les appelants existants.
    `normal_map`/`ao_map`/`curvature_map` (boucle 16, bx.bake) : chemins PNG optionnels
    vers des maps bakées HIGH->LOW (peau continue à écailles imbriquées + plis
    d'articulation) — None (défaut) = comportement v2 inchangé (rétro-compat totale).
    `normal_map` est CHAÎNÉ en amont du Bump procédural existant (macro bakée + micro
    shader empilés, pas un remplacement) ; `ao_map` multiplie légèrement la base color
    (creux baked plus sombres) ; `curvature_map` se MÉLANGE (`curvature_mix`) à la
    Pointiness géométrique live pour moduler la patine cavité — moins uniforme qu'une
    Pointiness seule sur un low-poly lissé après le shell de bake.
    `spec_level`/`sheen`/`aniso`/`specular_tint` (boucle 20, chantier Krokmou « peau
    satinée gris-bleu, pas de teinte cuivre ») : ces 4 réglages du Principled BSDF
    étaient câblés en dur (valeurs Drogon, reflet chaud cuivré) — désormais paramètres
    avec les MÊMES défauts (rétro-compat totale pour Drogon et les autres appelants).
    `specular_tint` neutre/froid (proche de (1,1,1)) retire la teinte chaude des
    reflets/grazing-angle même quand `edge_copper=0` (ce dernier ne masque que la
    couleur diffuse d'arête, pas le Specular Tint global du BSDF).
    `scale_axis` (P0 boucle 19 round 2, chantier « face lave uniforme ») : liste
    [[u, multiplicateur], ...] triée par `u` (0..1, abscisse le long de l'axe
    `axis_uv` — nécessite `axis_uv=True`) qui module le `Scale` Voronoi (plaques +
    micro + cellule couleur) le long de l'axe anatomique via une simple ColorRamp
    (LINEAR, interpolation piecewise générique — pas de valeur dragon en dur) :
    permet de GROSSES plaques au museau/mâchoire et des FINES près de l'œil sur le
    même matériau de tête, plutôt qu'une taille de motif uniforme façon papier
    peint. None (défaut) = comportement v3 inchangé (Scale constant)."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    # --- coordonnées distordues : base (Object, ou axis_uv anisotrope) + (noise-0.5)*warp ---
    tc = n.new('ShaderNodeTexCoord')
    base_socket = tc.outputs['Object']
    axis_u_out = None
    if axis_uv:
        attr = n.new('ShaderNodeAttribute')
        attr.attribute_type = 'GEOMETRY'
        attr.attribute_name = 'axis_uv'
        sepuv = n.new('ShaderNodeSeparateXYZ')
        lk.new(attr.outputs['Vector'], sepuv.inputs['Vector'])
        axis_u_out = sepuv.outputs['X']
        mulu = n.new('ShaderNodeMath')
        mulu.operation = 'MULTIPLY'
        mulu.inputs[1].default_value = axis_uv_stretch
        lk.new(sepuv.outputs['X'], mulu.inputs[0])
        combuv = n.new('ShaderNodeCombineXYZ')
        lk.new(mulu.outputs['Value'], combuv.inputs['X'])
        lk.new(sepuv.outputs['Y'], combuv.inputs['Y'])
        combuv.inputs['Z'].default_value = 0.0
        base_socket = combuv.outputs['Vector']
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
    lk.new(base_socket, wn.inputs['Vector'])
    lk.new(wn.outputs['Color'], sub.inputs[0])
    lk.new(sub.outputs['Vector'], scl.inputs[0])
    lk.new(base_socket, add.inputs[0])
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
    seed_fac = None
    if micro > 0:
        attr = n.new('ShaderNodeAttribute')
        attr.attribute_type = 'INSTANCER'
        attr.attribute_name = 'scale_seed'
        seed_fac = attr.outputs['Fac']
        v2.voronoi_dimensions = '4D'
        woff = n.new('ShaderNodeMath')
        woff.operation = 'MULTIPLY'
        woff.inputs[1].default_value = 61.0
        lk.new(seed_fac, woff.inputs[0])
        lk.new(woff.outputs['Value'], v2.inputs['W'])
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
    normal_img = _load_data_image(normal_map) if normal_map else None
    if normal_img:
        # macro bakée (peau continue + plis, bx.bake) CHAÎNÉE en amont : le Bump
        # procédural (micro shader) perturbe ensuite CE normal plutôt que le normal
        # de shading brut -> les deux échelles de détail s'additionnent au lieu de
        # s'écraser l'une l'autre.
        nm_img = n.new('ShaderNodeTexImage')
        nm_img.image = normal_img
        nmap = n.new('ShaderNodeNormalMap')
        nmap.inputs['Strength'].default_value = normal_map_strength
        lk.new(nm_img.outputs['Color'], nmap.inputs['Color'])
        lk.new(nmap.outputs['Normal'], bmp.inputs['Normal'])
    lk.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    # --- facteur arête : distance faible = bord de plaque → 1 (resserré : ne couvre
    # que le sillon réel entre écailles, pas toute la plaque — tempère le cuivre I2).
    # `edge_width` (CR1, boucle 17) : PLUS ÉTROIT que 0.045 = le rouge-cuivre ne mord
    # que sur la vraie carène/sillon (fraction cuivre proche de la réf, ~0.45 mesuré)
    # au lieu de laver toute la plaque (0.9 mesuré à edge_width=0.045 + edge_copper
    # élevé) ; PLUS LARGE = plaques presque entièrement cuivrées (look métal patiné). ---
    edge = n.new('ShaderNodeMapRange')
    edge.inputs['From Min'].default_value = 0.0
    edge.inputs['From Max'].default_value = edge_width
    edge.inputs['To Min'].default_value = 1.0
    edge.inputs['To Max'].default_value = 0.0
    lk.new(v1.outputs['Distance'], edge.inputs['Value'])
    # --- couleur : base charbon → variation par cellule → cuivre sur arêtes ---
    cell = n.new('ShaderNodeTexVoronoi')
    cell.inputs['Scale'].default_value = scale
    lk.new(coord, cell.inputs['Vector'])
    if axis_u_out is not None and scale_axis:
        # ColorRamp = fonction 1D générique (piecewise LINEAR) u -> multiplicateur de
        # Scale, réutilisée pour les 3 Voronoi (plaques/micro/cellule couleur) afin que
        # la taille du motif change de ZONE cohérente (pas juste le bump) le long de
        # l'axe anatomique -- ex. grandes plaques museau (mult bas), fines près de
        # l'œil (mult haut), sur le MÊME matériau de tête.
        sramp = n.new('ShaderNodeValToRGB')
        els = sramp.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        pts_axis = sorted(scale_axis, key=lambda p: p[0])
        u0, m0 = pts_axis[0]
        els[0].position, els[0].color = max(0.0, min(1.0, u0)), (m0, m0, m0, 1)
        for u, m in pts_axis[1:]:
            e = els.new(max(0.0, min(1.0, u)))
            e.color = (m, m, m, 1)
        sramp.color_ramp.interpolation = 'LINEAR'
        lk.new(axis_u_out, sramp.inputs['Fac'])
        for vnode, base_scale in ((v1, scale), (v2, scale2), (cell, scale)):
            smul = n.new('ShaderNodeMath')
            smul.operation = 'MULTIPLY'
            smul.inputs[1].default_value = base_scale
            lk.new(sramp.outputs['Color'], smul.inputs[0])
            lk.new(smul.outputs['Value'], vnode.inputs['Scale'])
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
    efac.operation = 'MULTIPLY'      # cuivre net mais borné et resserré sur les arêtes
    efac.inputs[1].default_value = edge_copper
    lk.new(edge.outputs['Result'], efac.inputs[0])
    var_out = mix1.outputs['Result']
    if seed_fac is not None:
        # éclaircissement par écaille : Factor = seed × micro (0 sur géométrie non instanciée)
        vfac = n.new('ShaderNodeMath')
        vfac.operation = 'MULTIPLY'
        vfac.inputs[1].default_value = micro
        lk.new(seed_fac, vfac.inputs[0])
        # (P0 boucle 19, round render-critic 2 : fix « dragon brun-cuivre uniforme »)
        # AVANT : B = base*4 + tint*0.2 -> ratio R/G/B fortement copper (~2.3/2.8) même
        # loin de toute arête -> chaque écaille à seed haut peignait TOUT le corps en
        # cuivre, noyant le masque edge_copper censé réserver le cuivre aux arêtes/
        # carènes réelles (mesuré : copper_fraction .87 contre .46 en réf). Le cuivre
        # doit rester le fait de `mix2`/`efac` (masque de cavité), pas de cette
        # variation par-écaille. Ici B garde le RATIO de `base` (mult uniforme, PAS de
        # tint) -> variation par plaque = value seulement (certaines plus claires,
        # d'autres plus sombres), jamais un virage de teinte -> base reste quasi-noire
        # même sur les écailles au seed le plus haut.
        mixv = n.new('ShaderNodeMix')
        mixv.data_type = 'RGBA'
        mixv.inputs['B'].default_value = (min(1.0, base[0] * 2.6),
                                          min(1.0, base[1] * 2.6),
                                          min(1.0, base[2] * 2.6), 1)
        lk.new(var_out, mixv.inputs['A'])
        lk.new(vfac.outputs['Value'], mixv.inputs['Factor'])
        var_out = mixv.outputs['Result']
    mix2 = n.new('ShaderNodeMix')
    mix2.data_type = 'RGBA'
    mix2.inputs['B'].default_value = (*tint, 1)
    lk.new(var_out, mix2.inputs['A'])
    lk.new(efac.outputs['Value'], mix2.inputs['Factor'])
    color_out = mix2.outputs['Result']
    # --- roughness plus basse sur les arêtes/carènes : casse le mat pour révéler le
    # relief GÉOMÉTRIQUE (plaques carénées) sous le rim, sans bruit shader ajouté ---
    rrange = n.new('ShaderNodeMapRange')
    rrange.inputs['From Min'].default_value = 0.0
    rrange.inputs['From Max'].default_value = 1.0
    rrange.inputs['To Min'].default_value = rough
    rrange.inputs['To Max'].default_value = rough_edge
    lk.new(edge.outputs['Result'], rrange.inputs['Value'])
    rough_out = rrange.outputs['Result']
    # --- variation par écaille (CR1) : teinte/valeur déjà en place ci-dessus (mix1 via
    # `cell`) ; ici on ajoute VALEUR (multiplie color_out par un gris par-cellule) et
    # ROUGHNESS (ajoute un offset par-cellule, clampé) — même source `cell` (aucun noeud
    # nouveau de bruit), gated à 0 = pas de changement pour les autres appelants. ---
    if instance_variation > 0:
        vrange = n.new('ShaderNodeMapRange')
        vrange.inputs['To Min'].default_value = 1.0 - instance_variation * 0.6
        vrange.inputs['To Max'].default_value = 1.0 + instance_variation * 0.35
        lk.new(cell.outputs['Color'], vrange.inputs['Value'])
        vgrey = n.new('ShaderNodeCombineColor')
        lk.new(vrange.outputs['Result'], vgrey.inputs['Red'])
        lk.new(vrange.outputs['Result'], vgrey.inputs['Green'])
        lk.new(vrange.outputs['Result'], vgrey.inputs['Blue'])
        vmul = n.new('ShaderNodeMix')
        vmul.data_type = 'RGBA'
        vmul.blend_type = 'MULTIPLY'
        vmul.inputs['Factor'].default_value = 1.0
        lk.new(color_out, vmul.inputs['A'])
        lk.new(vgrey.outputs['Color'], vmul.inputs['B'])
        color_out = vmul.outputs['Result']
        rvrange = n.new('ShaderNodeMapRange')
        rvrange.inputs['To Min'].default_value = -instance_variation * 0.18
        rvrange.inputs['To Max'].default_value = instance_variation * 0.18
        lk.new(cell.outputs['Color'], rvrange.inputs['Value'])
        radd = n.new('ShaderNodeMath')
        radd.operation = 'ADD'
        lk.new(rough_out, radd.inputs[0])
        lk.new(rvrange.outputs['Result'], radd.inputs[1])
        rclamp = n.new('ShaderNodeClamp')
        rclamp.inputs['Min'].default_value = 0.04
        rclamp.inputs['Max'].default_value = 0.95
        lk.new(radd.outputs['Value'], rclamp.inputs['Value'])
        rough_out = rclamp.outputs['Result']
    # --- patine métal usé (I14) : masque de cavité via Geometry Pointiness (0 = creux
    # concave, 1 = arête convexe) — pas de valeur dragon en dur, marche sur n'importe
    # quelle géométrie carénée. Creux -> vert-de-gris frotté sombre ; arêtes exposées ->
    # reflet doré chaud + roughness abaissée (dépose métallique frottée par le vol/le
    # combat). `patina_amount` 0 (défaut) = comportement v2 inchangé (rétro-compat). ---
    if patina_amount > 0:
        geo = n.new('ShaderNodeNewGeometry')
        cavity_src = geo.outputs['Pointiness']
        curvature_img = _load_data_image(curvature_map) if curvature_map else None
        if curvature_img:
            # courbure bakée (bx.bake, shell HIGH-poly) MÉLANGÉE à la Pointiness live du
            # low-poly : capte les plis/imbrications d'écailles du shell détruit après
            # bake, que la Pointiness seule (mesh lissé par le remesh voxel) ne voit
            # plus -> patine moins uniforme qu'avec la seule géométrie basse résolution.
            curv_img = n.new('ShaderNodeTexImage')
            curv_img.image = curvature_img
            curv_mix = n.new('ShaderNodeMix')
            curv_mix.data_type = 'FLOAT'
            curv_mix.inputs['Factor'].default_value = curvature_mix
            lk.new(cavity_src, curv_mix.inputs['A'])
            lk.new(curv_img.outputs['Color'], curv_mix.inputs['B'])
            cavity_src = curv_mix.outputs['Result']
        cav = n.new('ShaderNodeMapRange')
        cav.inputs['From Min'].default_value = 0.55
        cav.inputs['From Max'].default_value = 0.22
        cav.inputs['To Min'].default_value = 0.0
        cav.inputs['To Max'].default_value = 1.0
        lk.new(cavity_src, cav.inputs['Value'])
        cavf = n.new('ShaderNodeMath')
        cavf.operation = 'MULTIPLY'
        cavf.inputs[1].default_value = patina_amount
        lk.new(cav.outputs['Result'], cavf.inputs[0])
        mix_cav = n.new('ShaderNodeMix')
        mix_cav.data_type = 'RGBA'
        mix_cav.inputs['B'].default_value = (*patina_color, 1)
        lk.new(color_out, mix_cav.inputs['A'])
        lk.new(cavf.outputs['Value'], mix_cav.inputs['Factor'])
        color_out = mix_cav.outputs['Result']
        edg = n.new('ShaderNodeMapRange')
        edg.inputs['From Min'].default_value = 0.68
        edg.inputs['From Max'].default_value = 0.92
        edg.inputs['To Min'].default_value = 0.0
        edg.inputs['To Max'].default_value = 1.0
        lk.new(cavity_src, edg.inputs['Value'])
        edgf = n.new('ShaderNodeMath')
        edgf.operation = 'MULTIPLY'
        edgf.inputs[1].default_value = patina_amount
        lk.new(edg.outputs['Result'], edgf.inputs[0])
        mix_gold = n.new('ShaderNodeMix')
        mix_gold.data_type = 'RGBA'
        mix_gold.inputs['B'].default_value = (*patina_gold, 1)
        lk.new(color_out, mix_gold.inputs['A'])
        lk.new(edgf.outputs['Value'], mix_gold.inputs['Factor'])
        color_out = mix_gold.outputs['Result']
        rough_gold = n.new('ShaderNodeMix')
        rough_gold.data_type = 'FLOAT'
        rough_gold.inputs['B'].default_value = 0.14
        lk.new(rough_out, rough_gold.inputs['A'])
        lk.new(edgf.outputs['Value'], rough_gold.inputs['Factor'])
        rough_out = rough_gold.outputs['Result']
    ao_img_data = _load_data_image(ao_map) if ao_map else None
    if ao_img_data:
        # AO bakée (bx.bake) assombrit LÉGÈREMENT la base color dans les creux d'auto-
        # occlusion (racines d'écailles, plis) -> `ao_strength` borne l'effet (jamais un
        # noir plat, juste une variation supplémentaire que la Pointiness seule ne capte
        # pas sur un mesh low-poly lissé).
        ao_img = n.new('ShaderNodeTexImage')
        ao_img.image = ao_img_data
        ao_range = n.new('ShaderNodeMapRange')
        ao_range.inputs['To Min'].default_value = 1.0 - ao_strength
        ao_range.inputs['To Max'].default_value = 1.0
        lk.new(ao_img.outputs['Color'], ao_range.inputs['Value'])
        ao_mul = n.new('ShaderNodeMix')
        ao_mul.data_type = 'RGBA'
        ao_mul.blend_type = 'MULTIPLY'
        ao_mul.inputs['Factor'].default_value = 1.0
        lk.new(color_out, ao_mul.inputs['A'])
        lk.new(ao_range.outputs['Result'], ao_mul.inputs['B'])
        color_out = ao_mul.outputs['Result']
    lk.new(color_out, bsdf.inputs['Base Color'])
    lk.new(rough_out, bsdf.inputs['Roughness'])
    _set(bsdf, 'Roughness', rough)
    _set(bsdf, 'Specular Tint', (*specular_tint, 1.0))
    _set(bsdf, 'Specular IOR Level', spec_level)
    _set(bsdf, 'Anisotropic', aniso)
    _set(bsdf, 'Sheen Weight', sheen)
    if sss > 0:  # I4 : diffusion sous-cutanée → chair vivante, pas plastique
        _set(bsdf, 'Subsurface Weight', sss)
        _set(bsdf, 'Subsurface Radius', sss_radius)
        _set(bsdf, 'Subsurface Scale', 0.05)
    return mat


def membrane(name='membrane', color=(0.09, 0.015, 0.012), edge_color=None, rough=0.55,
            transmission=0.3, sss=0.35, sss_radius=(0.25, 0.05, 0.03),
            vein_scale=0.0, vein_strength=0.35, vein_dark=(0.02, 0.004, 0.006),
            vein_width=0.05, vein_bump=None,
            wrinkle_scale=0.0, wrinkle_strength=0.12, glow=0.0,
            edge_grad_min=0.15, edge_grad_max=1.4,
            mottle_scale=0.0, mottle_strength=0.0, mottle_dark=None,
            vein_radial_n=0, vein_radial_strength=0.0, vein_radial_width=0.32,
            vein_radial_taper=0.5, vein_radial_dark=None, vein_radial_bump=0.35,
            vein_radial_plane='yz'):
    """pattern.membrane_skin v2 : peau fine vascularisée. Réseau de veines procédural
    (2 Voronoi distance-to-edge superposés, coords Object) -> bump fin + assombrissement
    le long des sillons ; dégradé de couleur racine (`color`, près du corps) -> bord
    (`edge_color`, translucide chaud) via la distance au coin proche de la bbox objet
    (Texture Coordinate Generated, 0..1 par objet — proxy générique attache->bord libre,
    aucune valeur dragon en dur) ; micro-plis via bruit étiré anisotrope (bump).
    `vein_width` (T18, largeur de la bande de sillon en position de ColorRamp, défaut
    0.05 = comportement historique) et `vein_bump` (T18, force du Bump dédiée au réseau
    de veines, défaut None -> `vein_strength*0.5` comme avant, rétro-compat) DÉCOUPLENT
    la lisibilité géométrique (relief qui accroche même sous forte lumière/rim) de la
    lisibilité colorimétrique (`vein_strength`, assombrissement) — un plafond membrane
    lisse malgré des veines contrastées en couleur venait d'un bump trop faible pour
    créer une ombre propre sous les lumières dures existantes (aucun changement de scène).
    `vein_scale`/`wrinkle_scale` à 0 (défaut) = géométrie shader v1 inchangée (rétro-
    compat). Transmission BORNÉE à 0.05 (piège : coque fine + lumières fortes = taches
    blanches transmises, cf. claude.md) -> simuler la translucidité via `sss`/`glow`.
    `edge_grad_min`/`edge_grad_max` (P0 boucle 19 round 2 : « membrane orange uniforme,
    pas juste le bord ») bornent la distance (Generated Length, proxy bbox objet) où le
    dégradé racine->bord SE TERMINE. Défauts (0.15/1.4) historiques calibrés sur une
    aile dont l'origine objet est proche du CENTRE de la bbox — sur une aile dont
    l'origine est près de l'ÉPAULE (un coin, donc la longueur peut dépasser 1 sur une
    grande diagonale), un `From Max` trop bas fait basculer la PLUPART de la surface
    vers `edge_color` bien avant le bord réel -> voile chaud uniforme au lieu d'un
    liseré. Augmenter `edge_grad_max` resserre `edge_color` sur le vrai bord libre.
    `mottle_scale`/`mottle_strength`/`mottle_dark` (P0 boucle 19 round 3, « voile
    APLAT cuivre/orange uniforme ~40% du cadre ») : bruit à GRANDE échelle (peu de
    cellules sur toute la voile) qui assombrit/désature par TACHES douces le dégradé
    racine->bord existant — casse l'aplat sans ajouter de motif géométrique nouveau ;
    `mottle_scale=0` (défaut) = inchangé (rétro-compat totale).
    `vein_radial_*` (P0 boucle 19 round 3, « veines invisibles au hero, filaments
    géométriques isolés ») : réseau de veines DIRECTIONNEL lisible à l'échelle du plan
    large — contrairement au Voronoi isotrope ci-dessus (cellules abstraites), calcule
    un ANGLE polaire dans le plan de la voile (deux axes de `Generated`, coordonnée
    BBOX-NORMALISÉE 0..1 de l'objet -- PAS `Object` : sur un mesh construit en
    coordonnées MONDE avec un objet à transform identité loin de l'origine, `Object`
    est un décalage quasi constant sur toute la voile -> angle quasi identique
    partout, aucune raie visible ; `Generated` reste 0..1 relatif à la bbox propre de
    CET objet quelle que soit sa position monde, même trick que `edge_grad` ci-
    dessus) choisis par `vein_radial_plane` (ex. 'yz' — l'axe non listé est
    l'épaisseur/normale de la membrane, quasi-constant), origine ~racine (coin bbox
    min, cf. convention `edge_grad_min/max`), puis une onde SINUS périodique de cet
    angle (`vein_radial_n` = nombre de rayons) -> lignes
    RADIALES qui rayonnent depuis la racine vers le bord, une par intervalle
    angulaire, espacées régulièrement sur TOUTE la surface (pas 2-3 taches isolées).
    Largeur (`vein_radial_width`, position ColorRamp) RÉTRÉCIE progressivement vers
    le bord via `vein_radial_taper` (0..1, fraction de la largeur conservée au bord
    le plus éloigné, module par le même `grad` root->tip que le dégradé de couleur) —
    veines plus larges près du corps, plus fines et nombreuses en apparence vers le
    bord libre, jamais un balai de traits uniformes. `vein_radial_bump` alimente un
    Bump dédié (accroche le relief même si `vein_radial_strength` couleur est faible).
    `vein_radial_n=0` (défaut) = inchangé (rétro-compat totale)."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    edge_color = edge_color if edge_color is not None else color
    transmission = min(transmission, 0.05)
    tc = n.new('ShaderNodeTexCoord')
    # --- gradient racine -> bord libre (proxy générique bbox objet) ---
    glen = n.new('ShaderNodeVectorMath')
    glen.operation = 'LENGTH'
    lk.new(tc.outputs['Generated'], glen.inputs[0])
    grad = n.new('ShaderNodeMapRange')
    grad.inputs['From Min'].default_value = edge_grad_min
    grad.inputs['From Max'].default_value = edge_grad_max
    lk.new(glen.outputs['Value'], grad.inputs['Value'])
    mixc = n.new('ShaderNodeMix')
    mixc.data_type = 'RGBA'
    mixc.inputs['A'].default_value = (*color, 1)
    mixc.inputs['B'].default_value = (*edge_color, 1)
    lk.new(grad.outputs['Result'], mixc.inputs['Factor'])
    color_out = mixc.outputs['Result']
    grad_out = grad.outputs['Result']
    if mottle_scale > 0 and mottle_strength > 0:
        # taches douces à grande échelle (peu de cellules sur toute la voile) :
        # contraste renforcé (MapRange resserré autour de 0.5) pour lire comme des
        # PANNEAUX/plaques de valeur plutôt qu'un bruit fin superposé.
        mn = n.new('ShaderNodeTexNoise')
        mn.inputs['Scale'].default_value = mottle_scale
        mn.inputs['Detail'].default_value = 2.0
        mn.inputs['Roughness'].default_value = 0.55
        lk.new(tc.outputs['Generated'], mn.inputs['Vector'])
        mcontrast = n.new('ShaderNodeMapRange')
        mcontrast.clamp = True
        mcontrast.inputs['From Min'].default_value = 0.32
        mcontrast.inputs['From Max'].default_value = 0.68
        lk.new(mn.outputs['Fac'], mcontrast.inputs['Value'])
        mfac = n.new('ShaderNodeMath')
        mfac.operation = 'MULTIPLY'
        mfac.inputs[1].default_value = mottle_strength
        lk.new(mcontrast.outputs['Result'], mfac.inputs[0])
        mdark = mottle_dark if mottle_dark is not None else tuple(c * 0.4 for c in color)
        mmix = n.new('ShaderNodeMix')
        mmix.data_type = 'RGBA'
        mmix.inputs['B'].default_value = (*mdark, 1)
        lk.new(color_out, mmix.inputs['A'])
        lk.new(mfac.outputs['Value'], mmix.inputs['Factor'])
        color_out = mmix.outputs['Result']
    normal_out = None
    if vein_scale > 0:
        v1 = n.new('ShaderNodeTexVoronoi')
        v1.feature = 'DISTANCE_TO_EDGE'
        v1.inputs['Scale'].default_value = vein_scale
        lk.new(tc.outputs['Object'], v1.inputs['Vector'])
        v2 = n.new('ShaderNodeTexVoronoi')
        v2.feature = 'DISTANCE_TO_EDGE'
        v2.inputs['Scale'].default_value = vein_scale * 2.6
        lk.new(tc.outputs['Object'], v2.inputs['Vector'])
        vmin = n.new('ShaderNodeMath')
        vmin.operation = 'MINIMUM'
        lk.new(v1.outputs['Distance'], vmin.inputs[0])
        lk.new(v2.outputs['Distance'], vmin.inputs[1])
        vramp = n.new('ShaderNodeValToRGB')
        vramp.color_ramp.elements[0].position = 0.0
        vramp.color_ramp.elements[1].position = max(0.001, vein_width)
        lk.new(vmin.outputs['Value'], vramp.inputs['Fac'])
        veinfac = n.new('ShaderNodeMath')
        veinfac.operation = 'MULTIPLY'
        veinfac.inputs[1].default_value = vein_strength
        lk.new(vramp.outputs['Color'], veinfac.inputs[0])
        mixv = n.new('ShaderNodeMix')
        mixv.data_type = 'RGBA'
        mixv.inputs['B'].default_value = (*vein_dark, 1)
        lk.new(color_out, mixv.inputs['A'])
        lk.new(veinfac.outputs['Value'], mixv.inputs['Factor'])
        color_out = mixv.outputs['Result']
        bmpv = n.new('ShaderNodeBump')
        bmpv.inputs['Strength'].default_value = vein_bump if vein_bump is not None else vein_strength * 0.5
        lk.new(vramp.outputs['Color'], bmpv.inputs['Height'])
        normal_out = bmpv.outputs['Normal']
    if vein_radial_n > 0 and vein_radial_strength > 0:
        # veines DIRECTIONNELLES (rayons depuis la racine) : angle polaire dans le
        # plan de la voile (2 des 3 axes Object -- le 3e, quasi constant, est
        # l'épaisseur/normale) -> onde sinus périodique = N raies régulières sur
        # TOUTE la surface, largeur RÉTRÉCIE vers le bord via `grad_out` (même
        # dégradé root->tip que la couleur).
        sepr = n.new('ShaderNodeSeparateXYZ')
        lk.new(tc.outputs['Generated'], sepr.inputs['Vector'])
        axis_out = {'x': sepr.outputs['X'], 'y': sepr.outputs['Y'], 'z': sepr.outputs['Z']}
        a0 = axis_out[vein_radial_plane[0]]
        a1 = axis_out[vein_radial_plane[1]]
        ang = n.new('ShaderNodeMath')
        ang.operation = 'ARCTAN2'
        lk.new(a1, ang.inputs[0])
        lk.new(a0, ang.inputs[1])
        angmul = n.new('ShaderNodeMath')
        angmul.operation = 'MULTIPLY'
        angmul.inputs[1].default_value = vein_radial_n
        lk.new(ang.outputs['Value'], angmul.inputs[0])
        angsin = n.new('ShaderNodeMath')
        angsin.operation = 'SINE'
        lk.new(angmul.outputs['Value'], angsin.inputs[0])
        angabs = n.new('ShaderNodeMath')
        angabs.operation = 'ABSOLUTE'
        lk.new(angsin.outputs['Value'], angabs.inputs[0])
        # largeur effective = vein_radial_width au corps -> ×vein_radial_taper au bord
        wtaper = n.new('ShaderNodeMapRange')
        wtaper.inputs['To Min'].default_value = max(0.002, vein_radial_width)
        wtaper.inputs['To Max'].default_value = max(0.002, vein_radial_width * vein_radial_taper)
        lk.new(grad_out, wtaper.inputs['Value'])
        rramp = n.new('ShaderNodeMapRange')
        rramp.clamp = True
        rramp.inputs['From Min'].default_value = 0.0
        lk.new(wtaper.outputs['Result'], rramp.inputs['From Max'])
        rramp.inputs['To Min'].default_value = 1.0
        rramp.inputs['To Max'].default_value = 0.0
        lk.new(angabs.outputs['Value'], rramp.inputs['Value'])
        rfac = n.new('ShaderNodeMath')
        rfac.operation = 'MULTIPLY'
        rfac.inputs[1].default_value = vein_radial_strength
        lk.new(rramp.outputs['Result'], rfac.inputs[0])
        rdark = vein_radial_dark if vein_radial_dark is not None else vein_dark
        rmix = n.new('ShaderNodeMix')
        rmix.data_type = 'RGBA'
        rmix.inputs['B'].default_value = (*rdark, 1)
        lk.new(color_out, rmix.inputs['A'])
        lk.new(rfac.outputs['Value'], rmix.inputs['Factor'])
        color_out = rmix.outputs['Result']
        bmpr = n.new('ShaderNodeBump')
        bmpr.inputs['Strength'].default_value = vein_radial_bump
        lk.new(rramp.outputs['Result'], bmpr.inputs['Height'])
        if normal_out is not None:
            lk.new(normal_out, bmpr.inputs['Normal'])
        normal_out = bmpr.outputs['Normal']
    if wrinkle_scale > 0:
        mp = n.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (wrinkle_scale, wrinkle_scale * 3.2, wrinkle_scale)
        lk.new(tc.outputs['Object'], mp.inputs['Vector'])
        wn = n.new('ShaderNodeTexNoise')
        wn.inputs['Detail'].default_value = 3.0
        lk.new(mp.outputs['Vector'], wn.inputs['Vector'])
        bmpw = n.new('ShaderNodeBump')
        bmpw.inputs['Strength'].default_value = wrinkle_strength
        lk.new(wn.outputs['Fac'], bmpw.inputs['Height'])
        if normal_out is not None:
            lk.new(normal_out, bmpw.inputs['Normal'])
        normal_out = bmpw.outputs['Normal']
    if normal_out is not None:
        lk.new(normal_out, bsdf.inputs['Normal'])
    lk.new(color_out, bsdf.inputs['Base Color'])
    _set(bsdf, 'Roughness', rough)
    _set(bsdf, 'Transmission Weight', transmission)
    _set(bsdf, 'Subsurface Weight', sss)
    _set(bsdf, 'Subsurface Radius', sss_radius)
    if glow > 0:
        _set(bsdf, 'Emission Color', (*edge_color, 1))
        _set(bsdf, 'Emission Strength', glow)
    return mat


def bone(name='bone', color=(0.06, 0.05, 0.045), rough=0.35):
    mat, nt, bsdf = _new(name)
    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Roughness', rough)
    return mat


def enamel(name='enamel', color=(0.85, 0.82, 0.75), root_color=(0.32, 0.24, 0.17),
           rough=0.22, sss=0.12, root_frac=0.32):
    """Émail dentaire (feedback boucle 18 pt3 : dents « uniformes », matériau `bone`
    trop plat) : blanc cassé légèrement translucide (SSS léger), racine plus sombre
    près de la gencive. Le gradient racine->couronne est piloté par la coordonnée
    UV.U générée AUTOMATIQUEMENT par Blender le long d'un tube-courbe (u=0 au premier
    point de contrôle -> u=1 au dernier, cf. test empirique `ops.tube`) plutôt qu'un
    axe Z objet/monde : générique et ORIENTATION-INDÉPENDANT, alors qu'un gradient Z
    s'inverserait entre dents du haut (pointent vers le bas) et du bas (pointent vers
    le haut) sur un matériau partagé. Suppose seulement que l'appelant construit ses
    points racine->pointe dans cet ordre (déjà le cas dans `bx.organic.head`)."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    uvmap = n.new('ShaderNodeUVMap')
    sep = n.new('ShaderNodeSeparateXYZ')
    lk.new(uvmap.outputs['UV'], sep.inputs['Vector'])
    mr = n.new('ShaderNodeMapRange')
    mr.clamp = True
    mr.inputs['From Min'].default_value = 0.0
    mr.inputs['From Max'].default_value = max(0.05, root_frac)
    mr.inputs['To Min'].default_value = 0.0   # racine (u bas) sombre
    mr.inputs['To Max'].default_value = 1.0   # couronne (u haut) claire
    lk.new(sep.outputs['X'], mr.inputs['Value'])
    mix = n.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (*root_color, 1)
    mix.inputs['B'].default_value = (*color, 1)
    lk.new(mr.outputs['Result'], mix.inputs['Factor'])
    lk.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    _set(bsdf, 'Roughness', rough)
    if sss > 0:
        _set(bsdf, 'Subsurface Weight', sss)
        _set(bsdf, 'Subsurface Radius', (0.25, 0.22, 0.18))
    return mat


def horn(name='horn', color=(0.07, 0.045, 0.025), rough=0.3, stripe_scale=28,
         stripe_strength=0.22, aniso=0.4, var=0.14, spec_level=0.6,
         axis_uv=False, axis_uv_stripes=22):
    """pattern.horn v1 : kératine striée générique (cornes/griffes/épines osseuses) —
    bandes fines (Wave texture le long de l'axe local Z, cornes/griffes/pointes étant
    des tubes/cônes effilés le long de cet axe en coordonnées Object) en bump, reflet
    anisotrope (fibres de kératine) + légère variation cellule à cellule (Voronoi) qui
    casse l'uniformité plastique du `bone` plat. Aucune valeur dragon en dur : marche
    sur n'importe quelle géométrie tube/cône effilée.
    `spec_level` (T18, défaut 0.6 = valeur historique) : Specular IOR Level — sur un
    doigt d'aile fin sous les lumières de bord (rim ~5200) 0.6 sature en un reflet
    métal/chrome qui écrase la couleur kératine ; baissable depuis la spec sans
    toucher aux lumières.
    `axis_uv` (boucle 19 chantier C, fix diagnostiqué : le Wave ci-dessus utilise les
    coordonnées OBJECT, valides seulement si l'axe local Z de l'objet EST l'axe de la
    corne — faux pour `bx.organic.head` où les tubes-courbes sont construits avec des
    points déjà en MONDE sur un objet à transform identité : l'axe Z « Object » est en
    réalité l'axe Z MONDE, qui ne coïncide avec l'axe de la corne que si elle pointe
    pile vers le haut. Une corne inclinée/balayée voit alors ses bandes couper de
    travers au lieu de courir le long de sa longueur.) Quand True, remplace le Wave
    par l'attribut mesh `axis_uv` (u=abscisse le long de l'axe RÉEL de la pièce,
    v=angle autour de la section, écrit par `detail.write_axis_uv` sur la position
    MONDE réelle des sommets, cf. `bx.organic.head`) : les stries varient avec v
    (angle, PAS u) -> restent LONGITUDINALES (parallèles à l'axe) quelle que soit
    l'orientation de la corne dans l'espace. Sans l'attribut sur le mesh, l'Attribute
    node renvoie (0,0,0) -> rétro-compat totale (défaut False, comportement Wave
    Object inchangé pour tous les appelants existants, ex. griffes/wing_bone)."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    if axis_uv:
        attr = n.new('ShaderNodeAttribute')
        attr.attribute_type = 'GEOMETRY'
        attr.attribute_name = 'axis_uv'
        sepuv = n.new('ShaderNodeSeparateXYZ')
        lk.new(attr.outputs['Vector'], sepuv.inputs['Vector'])
        vmul = n.new('ShaderNodeMath')
        vmul.operation = 'MULTIPLY'
        vmul.inputs[1].default_value = axis_uv_stripes
        lk.new(sepuv.outputs['Y'], vmul.inputs[0])
        vsin = n.new('ShaderNodeMath')
        vsin.operation = 'SINE'
        lk.new(vmul.outputs['Value'], vsin.inputs[0])
        bmp = n.new('ShaderNodeBump')
        bmp.inputs['Strength'].default_value = stripe_strength
        lk.new(vsin.outputs['Value'], bmp.inputs['Height'])
        lk.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
        tc = n.new('ShaderNodeTexCoord')  # coordonnée cellule ci-dessous (variation)
    else:
        tc = n.new('ShaderNodeTexCoord')
        wave = n.new('ShaderNodeTexWave')
        wave.bands_direction = 'Z'
        wave.inputs['Scale'].default_value = stripe_scale
        wave.inputs['Distortion'].default_value = 0.8
        wave.inputs['Detail'].default_value = 2.0
        lk.new(tc.outputs['Object'], wave.inputs['Vector'])
        bmp = n.new('ShaderNodeBump')
        bmp.inputs['Strength'].default_value = stripe_strength
        lk.new(wave.outputs['Fac'], bmp.inputs['Height'])
        lk.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    cell = n.new('ShaderNodeTexVoronoi')
    cell.inputs['Scale'].default_value = 6.0
    lk.new(tc.outputs['Object'], cell.inputs['Vector'])
    vfac = n.new('ShaderNodeMath')
    vfac.operation = 'MULTIPLY'
    vfac.inputs[1].default_value = var
    lk.new(cell.outputs['Distance'], vfac.inputs[0])
    varmix = n.new('ShaderNodeMix')
    varmix.data_type = 'RGBA'
    varmix.inputs['A'].default_value = (*color, 1)
    varmix.inputs['B'].default_value = (color[0] * 0.55, color[1] * 0.55, color[2] * 0.55, 1)
    lk.new(vfac.outputs['Value'], varmix.inputs['Factor'])
    lk.new(varmix.outputs['Result'], bsdf.inputs['Base Color'])
    _set(bsdf, 'Roughness', rough)
    _set(bsdf, 'Anisotropic', aniso)
    _set(bsdf, 'Anisotropic Rotation', 0.05)
    _set(bsdf, 'Specular IOR Level', spec_level)
    return mat


def eye(name='eye', color=(0.9, 0.45, 0.08), glow=2.0):
    mat, nt, bsdf = _new(name)
    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Emission Color', (*color, 1))
    _set(bsdf, 'Emission Strength', glow)
    _set(bsdf, 'Roughness', 0.1)
    return mat


def eye_globe(name='eye', sclera_color=(0.045, 0.022, 0.016), iris_color=(0.55, 0.22, 0.045),
             iris_color2=None, pupil_color=(0.012, 0.009, 0.007), pupil_width=0.16, iris_r=0.5,
             rough=0.08, clearcoat=0.55, glow=0.12, pupil_length=1.0, pupil_edge=0.015,
             catchlight=0.0, catchlight_pos=(0.55, 0.4), catchlight_size=0.045,
             catchlight_soft=0.02, spec_level=0.5):
    """EyeBuilder (boucle 17 CR3, feedback B) : matériau GÉNÉRIQUE pour un globe
    oculaire ISOLÉ en un seul objet + un seul matériau — remplace l'empilement de 3
    disques (sclère/iris/pupille plaqués) sur un matériau émissif plat par un
    gradient NODAL calculé directement sur la sphère (Texture Coordinate 'Object' :
    coordonnées locales d'un blob unitaire, cf. `bx.organic.head` — convention X local
    = normale de la calotte/axe de vue, Y = horizontal du visage, Z = vertical).
    `pupil_width` (0..1, plus petit = plus fin) compresse l'axe Y avant de calculer la
    distance au centre -> ellipse verticale (fente de reptile) au lieu d'un disque.
    `iris_r` (0..1) = rayon où l'iris cède la place à la sclère. ColorRamp à arrêts
    RAPPROCHÉS aux frontières (pupille/iris, iris/sclère) -> transitions nettes sans
    changer le mode d'interpolation (reste LINEAR, pas de flou de bord constant).
    DEUX distances séparées (fix boucle 20, bug « bille de verre sans iris lisible ») :
    l'anneau iris/sclère (rond, `dist_round`) et le trou de pupille + son liseré
    (fente verticale squishée, `dist_slit`) sont calculés indépendamment puis
    superposés par Mix — auparavant une SEULE distance squishée pilotait tout le
    dégradé, écrasant le disque iris en une fine bande verticale.
    Très spéculaire (`rough` bas, défaut proche du mouillé) + `clearcoat` -> le globe
    ACCROCHE la lumière (reflet net) au lieu du flat-color mort de l'ancien matériau
    uniforme ; `glow` (défaut faible, PAS l'ancien plein-émissif ~2.0) ajoute une once
    de vie sans revenir à un œil qui a l'air de briller de l'intérieur.
    `iris_color2` (feedback boucle 18 pt2 : « disques dorés plats » à travers
    l'ouverture des paupières) : iris à DEUX tons — `iris_color` vif près de la
    pupille, `iris_color2` (défaut = `iris_color` assombri) sur l'anneau externe
    avant la sclère -> même à travers une petite ouverture de paupière, l'œil montre
    au moins deux teintes + un bord net vers la sclère sombre au lieu d'un aplat
    uniforme. `iris_r` réduit par défaut (plateau iris plus étroit) pour laisser plus
    de place à la sclère visible dans l'ouverture.
    `pupil_length` (P0 boucle 19 round 2, feedback render-critic « pupille = tache
    floue en losange ») : DIVISE l'axe Z avant le calcul de distance (comme
    `pupil_width` divise Y) -> >1.0 allonge la fente VERTICALEMENT sans l'élargir
    (fente fine ET haute, pas juste fine). `pupil_edge` resserre encore l'écart de
    ColorRamp pupille->liseré (défaut 0.03 avant -> `pupil_edge` ~0.015) pour un bord
    de fente NET plutôt qu'un flou de transition large.
    `catchlight` (0..1, défaut 0 = off) : point de lumière PONCTUEL fixe en espace
    Object (indépendant de l'éclairage de scène, donc jamais une barre plate = la
    forme d'une area light réfléchie) — petit disque net (`catchlight_size`/
    `catchlight_soft`) mélangé en blanc sur la Base Color ET boosté en Emission à cet
    endroit seul, positionné par `catchlight_pos` (Y, Z local)."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    tc = n.new('ShaderNodeTexCoord')
    sep = n.new('ShaderNodeSeparateXYZ')
    lk.new(tc.outputs['Object'], sep.inputs['Vector'])
    # --- distance RONDE (Y,Z bruts, sphère unitaire) : pilote l'ANNEAU iris/sclère
    # comme un DISQUE CIRCULAIRE (fix boucle 20, bug « bille de verre sans iris
    # lisible » — cf. docstring : l'ancien code pilotait TOUT le dégradé pupille->
    # iris->sclère depuis la distance SQUISHÉE (pupil_width/pupil_length), écrasant
    # le disque iris rond en une fine bande verticale quasi invisible dès qu'on
    # s'écartait de l'axe horizontal de quelques degrés). ---
    y2r = n.new('ShaderNodeMath')
    y2r.operation = 'MULTIPLY'
    lk.new(sep.outputs['Y'], y2r.inputs[0])
    lk.new(sep.outputs['Y'], y2r.inputs[1])
    z2r = n.new('ShaderNodeMath')
    z2r.operation = 'MULTIPLY'
    lk.new(sep.outputs['Z'], z2r.inputs[0])
    lk.new(sep.outputs['Z'], z2r.inputs[1])
    dsumr = n.new('ShaderNodeMath')
    dsumr.operation = 'ADD'
    lk.new(y2r.outputs['Value'], dsumr.inputs[0])
    lk.new(z2r.outputs['Value'], dsumr.inputs[1])
    dist_round = n.new('ShaderNodeMath')
    dist_round.operation = 'SQRT'
    lk.new(dsumr.outputs['Value'], dist_round.inputs[0])

    ir = max(0.20, min(iris_r, 0.45))
    outer2 = iris_color2 if iris_color2 is not None else tuple(c * 0.55 for c in iris_color)
    ramp = n.new('ShaderNodeValToRGB')
    els = ramp.color_ramp.elements
    while len(els) > 1:
        els.remove(els[-1])
    els[0].position, els[0].color = 0.0, (*iris_color, 1)

    def stop(pos, color):
        e = els.new(max(0.0, min(1.0, pos)))
        e.color = (*color, 1)

    stop(ir * 0.72, iris_color)               # tenu jusqu'à l'anneau externe
    stop(ir, outer2)                          # DEUX TONS : anneau externe plus sombre
    stop(min(0.94, ir + 0.06), sclera_color)  # bord net iris/sclère
    stop(1.0, sclera_color)
    ramp.color_ramp.interpolation = 'LINEAR'
    lk.new(dist_round.outputs['Value'], ramp.inputs['Fac'])
    color_out = ramp.outputs['Color']

    # --- distance FENTE (squishée Y/pupil_width, Z/pupil_length) : pilote SEULEMENT
    # le trou de pupille (ellipse verticale) + son liseré clair, superposés en Mix
    # PAR-DESSUS le disque iris rond ci-dessus — la fente reste fine/haute, mais ne
    # dévore plus tout l'iris environnant. ---
    ydiv = n.new('ShaderNodeMath')
    ydiv.operation = 'DIVIDE'
    ydiv.inputs[1].default_value = max(0.02, pupil_width)
    lk.new(sep.outputs['Y'], ydiv.inputs[0])
    zdiv = n.new('ShaderNodeMath')
    zdiv.operation = 'DIVIDE'
    zdiv.inputs[1].default_value = max(0.02, pupil_length)
    lk.new(sep.outputs['Z'], zdiv.inputs[0])
    y2 = n.new('ShaderNodeMath')
    y2.operation = 'MULTIPLY'
    lk.new(ydiv.outputs['Value'], y2.inputs[0])
    lk.new(ydiv.outputs['Value'], y2.inputs[1])
    z2 = n.new('ShaderNodeMath')
    z2.operation = 'MULTIPLY'
    lk.new(zdiv.outputs['Value'], z2.inputs[0])
    lk.new(zdiv.outputs['Value'], z2.inputs[1])
    dsum = n.new('ShaderNodeMath')
    dsum.operation = 'ADD'
    lk.new(y2.outputs['Value'], dsum.inputs[0])
    lk.new(z2.outputs['Value'], dsum.inputs[1])
    dist_slit = n.new('ShaderNodeMath')
    dist_slit.operation = 'SQRT'
    lk.new(dsum.outputs['Value'], dist_slit.inputs[0])

    amber_hi = tuple(min(1.0, c * 1.5 + 0.05) for c in iris_color)
    edge = max(0.006, pupil_edge)
    pupil_r = 0.15
    pupil_map = n.new('ShaderNodeMapRange')
    pupil_map.clamp = True
    pupil_map.inputs['From Min'].default_value = pupil_r
    pupil_map.inputs['From Max'].default_value = pupil_r + edge
    pupil_map.inputs['To Min'].default_value = 1.0
    pupil_map.inputs['To Max'].default_value = 0.0
    lk.new(dist_slit.outputs['Value'], pupil_map.inputs['Value'])
    mix_pupil = n.new('ShaderNodeMix')
    mix_pupil.data_type = 'RGBA'
    mix_pupil.inputs['B'].default_value = (*pupil_color, 1)
    lk.new(color_out, mix_pupil.inputs['A'])
    lk.new(pupil_map.outputs['Result'], mix_pupil.inputs['Factor'])
    color_out = mix_pupil.outputs['Result']

    # liseré clair juste hors du trou (catch-light iris/pupille), même forme de fente
    ring_up = n.new('ShaderNodeMapRange')
    ring_up.clamp = True
    ring_up.inputs['From Min'].default_value = pupil_r
    ring_up.inputs['From Max'].default_value = pupil_r + edge
    ring_up.inputs['To Min'].default_value = 0.0
    ring_up.inputs['To Max'].default_value = 1.0
    lk.new(dist_slit.outputs['Value'], ring_up.inputs['Value'])
    ring_down = n.new('ShaderNodeMapRange')
    ring_down.clamp = True
    ring_down.inputs['From Min'].default_value = pupil_r + edge
    ring_down.inputs['From Max'].default_value = pupil_r + edge + 0.05
    ring_down.inputs['To Min'].default_value = 1.0
    ring_down.inputs['To Max'].default_value = 0.0
    lk.new(dist_slit.outputs['Value'], ring_down.inputs['Value'])
    ring_fac = n.new('ShaderNodeMath')
    ring_fac.operation = 'MINIMUM'
    lk.new(ring_up.outputs['Result'], ring_fac.inputs[0])
    lk.new(ring_down.outputs['Result'], ring_fac.inputs[1])
    mix_ring = n.new('ShaderNodeMix')
    mix_ring.data_type = 'RGBA'
    mix_ring.inputs['B'].default_value = (*amber_hi, 1)
    lk.new(color_out, mix_ring.inputs['A'])
    lk.new(ring_fac.outputs['Value'], mix_ring.inputs['Factor'])
    color_out = mix_ring.outputs['Result']
    emission_out = color_out
    if catchlight > 0:
        cy, cz = catchlight_pos
        dy = n.new('ShaderNodeMath')
        dy.operation = 'SUBTRACT'
        dy.inputs[1].default_value = cy
        lk.new(sep.outputs['Y'], dy.inputs[0])
        dz = n.new('ShaderNodeMath')
        dz.operation = 'SUBTRACT'
        dz.inputs[1].default_value = cz
        lk.new(sep.outputs['Z'], dz.inputs[0])
        dy2 = n.new('ShaderNodeMath')
        dy2.operation = 'MULTIPLY'
        lk.new(dy.outputs['Value'], dy2.inputs[0])
        lk.new(dy.outputs['Value'], dy2.inputs[1])
        dz2 = n.new('ShaderNodeMath')
        dz2.operation = 'MULTIPLY'
        lk.new(dz.outputs['Value'], dz2.inputs[0])
        lk.new(dz.outputs['Value'], dz2.inputs[1])
        cdsum = n.new('ShaderNodeMath')
        cdsum.operation = 'ADD'
        lk.new(dy2.outputs['Value'], cdsum.inputs[0])
        lk.new(dz2.outputs['Value'], cdsum.inputs[1])
        cdist = n.new('ShaderNodeMath')
        cdist.operation = 'SQRT'
        lk.new(cdsum.outputs['Value'], cdist.inputs[0])
        cmap = n.new('ShaderNodeMapRange')
        cmap.clamp = True
        cmap.inputs['From Min'].default_value = max(0.001, catchlight_size)
        cmap.inputs['From Max'].default_value = max(0.002, catchlight_size + catchlight_soft)
        cmap.inputs['To Min'].default_value = 1.0
        cmap.inputs['To Max'].default_value = 0.0
        lk.new(cdist.outputs['Value'], cmap.inputs['Value'])
        cfac = n.new('ShaderNodeMath')
        cfac.operation = 'MULTIPLY'
        cfac.inputs[1].default_value = catchlight
        lk.new(cmap.outputs['Result'], cfac.inputs[0])
        cmix = n.new('ShaderNodeMix')
        cmix.data_type = 'RGBA'
        cmix.inputs['B'].default_value = (1, 1, 1, 1)
        lk.new(color_out, cmix.inputs['A'])
        lk.new(cfac.outputs['Value'], cmix.inputs['Factor'])
        color_out = cmix.outputs['Result']
        ecmix = n.new('ShaderNodeMix')
        ecmix.data_type = 'RGBA'
        ecmix.inputs['B'].default_value = (1, 1, 1, 1)
        lk.new(emission_out, ecmix.inputs['A'])
        lk.new(cfac.outputs['Value'], ecmix.inputs['Factor'])
        emission_out = ecmix.outputs['Result']
    lk.new(color_out, bsdf.inputs['Base Color'])
    _set(bsdf, 'Roughness', rough)
    _set(bsdf, 'Coat Weight', clearcoat)
    _set(bsdf, 'Clearcoat', clearcoat)
    _set(bsdf, 'Coat Roughness', 0.03)
    _set(bsdf, 'Clearcoat Roughness', 0.03)
    # `spec_level` (boucle 20, chantier Krokmou : iris délavé/blanchi sous fond studio
    # blanc très lumineux) : Specular IOR Level du BSDF, défaut 0.5 = comportement
    # historique. Sous un dôme monde très lumineux, la réflexion diélectrique blanche
    # s'AJOUTE (additif, pas un mélange) à la couleur diffuse de l'iris sur toute la
    # calotte visible -> désature/blanchit un iris pourtant saturé en Base Color.
    # Baisser `spec_level` réduit cette réflexion SANS toucher au catchlight (nodal,
    # indépendant de l'éclairage réel de la scène).
    _set(bsdf, 'Specular IOR Level', spec_level)
    # Emission = LA MÊME rampe (pas `iris_color` constant) : bug diagnostiqué boucle 18
    # pt2 (test isolé sphère+lampe) -> une émission plate uniforme sur TOUTE la sphère
    # noyait la sclère sombre sous un glow ambré constant en éclairage faible, rendant
    # l'œil entier « disque doré plat » même quand la Base Color variait correctement.
    # Brancher la rampe fait retomber l'émission à ~0 sur la sclère (couleur quasi
    # noire) et ne glow que pupille/iris, sans changer `glow` (force globale) ; le
    # catchlight (si actif) s'ajoute PAR-DESSUS pour un point net visible même en
    # éclairage faible (indépendant de la forme/position des lumières de scène).
    lk.new(emission_out, bsdf.inputs['Emission Color'])
    _set(bsdf, 'Emission Strength', glow)
    return mat


def gum(name='gum', color=(0.32, 0.05, 0.06), rough=0.38, sss=0.22,
        sss_radius=(0.22, 0.07, 0.05), spec_level=0.7, wet=0.35):
    """Gencive : chair humide (feedback boucle 19 chantier C, « dents sans gencives
    crédibles ») — teinte rouge/rose sombre distincte de la peau écailleuse, SSS
    légère (chair vivante) + spécularité plus haute que la peau + léger coat
    (`wet`) pour une brillance HUMIDE nette sous les lumières fortes, sans
    géométrie propre (assigné au bourrelet continu `_lip_bourrelet` en base des
    dents, cf. `bx.organic.head`)."""
    mat, nt, bsdf = _new(name)
    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Roughness', rough)
    _set(bsdf, 'Specular IOR Level', spec_level)
    if sss > 0:
        _set(bsdf, 'Subsurface Weight', sss)
        _set(bsdf, 'Subsurface Radius', sss_radius)
    if wet > 0:
        _set(bsdf, 'Coat Weight', wet)
        _set(bsdf, 'Coat Roughness', 0.05)
        _set(bsdf, 'Clearcoat', wet)
        _set(bsdf, 'Clearcoat Roughness', 0.05)
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


def ice(name='ice', color=(0.72, 0.85, 0.98), deep=(0.16, 0.34, 0.52),
        transmission=0.35, sss=0.55, sss_radius=(0.06, 0.12, 0.18),
        rough_clear=0.06, rough_frost=0.52, frost_scale=6.0, frost_bias=0.42,
        fracture_scale=14.0, fracture_bump=0.35, ior=1.31, spec_level=0.72):
    """pattern.ice v1 (b28, type GLACE) : glace NATURELLE, pas du verre.

    Trois choses distinguent la glace vraie d'un cristal de synthese, et aucune n'est
    la transparence :
    1. elle est LAITEUSE — la diffusion sous la surface (bulles d'air, micro-fractures)
       domine la transmission. D'ou `sss` fort et `transmission` modere : pousser la
       transmission au-dela de ~0.5 sur des pointes fines rejoue le piege CLAUDE.md
       (taches blanches transmises sous des rim fortes) et donne du plastique ;
    2. sa rugosite est TACHETEE : plages polies (rough_clear) et plages givrees
       (rough_frost) melangees par un bruit — c'est ce contraste qui la fait lire ;
    3. elle est BLEUE EN PROFONDEUR seulement : la teinte vient de l'epaisseur
       traversee, donc `deep` n'apparait que la ou le trajet est long (approxime ici
       par le rayon de diffusion, plus long dans le bleu).
    Marche sur n'importe quelle geometrie facettee (cf. `crystal()` cote generateurs)."""
    mat, nt, bsdf = _new(name)
    n, lk = nt.nodes, nt.links
    tc = n.new('ShaderNodeTexCoord')

    # --- givre tachete : melange de rugosite pilote par un bruit large
    frost = n.new('ShaderNodeTexNoise')
    frost.inputs['Scale'].default_value = frost_scale
    frost.inputs['Detail'].default_value = 4.0
    lk.new(tc.outputs['Object'], frost.inputs['Vector'])
    fmap = n.new('ShaderNodeMapRange')
    fmap.inputs['From Min'].default_value = frost_bias
    fmap.inputs['From Max'].default_value = frost_bias + 0.22
    fmap.inputs['To Min'].default_value = rough_clear
    fmap.inputs['To Max'].default_value = rough_frost
    fmap.clamp = True
    lk.new(frost.outputs['Fac'], fmap.inputs['Value'])
    lk.new(fmap.outputs['Result'], bsdf.inputs['Roughness'])

    # --- micro-fractures internes : voronoi en bump, tres fin
    frac = n.new('ShaderNodeTexVoronoi')
    frac.feature = 'DISTANCE_TO_EDGE'
    frac.inputs['Scale'].default_value = fracture_scale
    lk.new(tc.outputs['Object'], frac.inputs['Vector'])
    bmp = n.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = fracture_bump
    bmp.inputs['Distance'].default_value = 0.02
    lk.new(frac.outputs['Distance'], bmp.inputs['Height'])
    lk.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])

    _set(bsdf, 'Base Color', (*color, 1))
    _set(bsdf, 'Transmission Weight', transmission)
    _set(bsdf, 'IOR', ior)
    _set(bsdf, 'Subsurface Weight', sss)
    _set(bsdf, 'Subsurface Radius', sss_radius)
    _set(bsdf, 'Subsurface Scale', 0.12)
    _set(bsdf, 'Specular IOR Level', spec_level)
    for key in ('Subsurface Color', 'Subsurface Tint'):
        _set(bsdf, key, (*deep, 1))
    return mat
