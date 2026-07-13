"""bx.ops — primitives géométriques AI-friendly (coordonnées monde, un appel = une forme)."""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

from . import core


_FLAT_BEVEL_CACHE = {}


def _flat_bevel_obj(flat, n=12):
    """Objet-profil de bevel APLATI (ellipse squashée, coords locales) réutilisé comme
    `curve.bevel_object` — remplace le cercle rond par défaut de `bevel_depth` par une
    section anisotrope (large/mince) : donne des tubes en PLAQUE (cornes-lames, écailles
    dorsales plates) au lieu de tiges rondes, sans dupliquer la logique de `tube()` —
    même mécanisme de rayon par point (`p.radius`) continue de s'appliquer, il scale
    juste un profil non-circulaire. Caché par ratio (peu de valeurs distinctes en
    pratique) pour ne pas créer un nouvel objet caché par appel."""
    key = round(flat, 4)
    cached = _FLAT_BEVEL_CACHE.get(key)
    if cached is not None and cached.name in bpy.data.objects:
        return cached
    cu = bpy.data.curves.new(f'_bevel_flat_{key}', 'CURVE')
    cu.dimensions = '2D'
    sp = cu.splines.new('POLY')
    sp.points.add(n - 1)
    for i, p in enumerate(sp.points):
        a = 2 * math.pi * i / n
        p.co = (math.cos(a), flat * math.sin(a), 0.0, 1.0)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new(f'_bevel_flat_{key}', cu)
    core.link(ob)
    ob.hide_render = True
    ob.hide_viewport = True
    ob.hide_select = True
    _FLAT_BEVEL_CACHE[key] = ob
    return ob


def tube(name, pts, radii, caps=True, order=4, resolution_u=12, bevel_resolution=8,
         flat=None, tilts=None):
    """Tube organique : courbe NURBS avec rayon par point (corps, membres, cornes).
    `resolution_u`/`bevel_resolution` (défauts = valeurs Blender historiques, rétro-
    compat) : baisser les deux pour un profil à beaucoup de points de contrôle (ex.
    cornes à anneaux) SANS faire exploser le nombre de sommets — un tube à N points
    de contrôle a de toute façon assez de segments pour rester lisse avec une
    résolution plus basse que le tube générique (corps/membres, peu de points).
    `flat` (boucle 22, thème « souder pas poser » — cornes/épines en PLAQUE plutôt
    qu'en cône rond, défaut None = rétro-compat, section circulaire inchangée) :
    ratio 0<flat<1 = épaisseur/largeur de la section (`_flat_bevel_obj`), le rayon par
    point continue de scaler toute la section -> une plaque qui s'amincit vers la
    pointe au lieu d'un cône. `tilts` (liste de degrés par point, défaut None = 0
    partout) : torsion progressive de la section le long de l'axe (légère torsion de
    lame), tourne le profil de bevel autour de la tangente à chaque point de contrôle."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('NURBS')
    sp.points.add(len(pts) - 1)
    for i, (p, pt, r) in enumerate(zip(sp.points, pts, radii)):
        p.co = (*pt, 1)
        p.radius = r
        if tilts is not None and i < len(tilts):
            p.tilt = math.radians(tilts[i])
    sp.use_endpoint_u = True
    sp.order_u = min(order, len(pts))
    cu.resolution_u = resolution_u
    cu.bevel_depth = 1.0
    cu.bevel_resolution = bevel_resolution
    if flat is not None:
        cu.bevel_mode = 'OBJECT'
        cu.bevel_object = _flat_bevel_obj(flat)
    cu.use_fill_caps = caps
    return core.link(bpy.data.objects.new(name, cu))


def blob(name, loc=(0, 0, 0), scale=(1, 1, 1), rot_deg=(0, 0, 0), seg=32):
    """Ellipsoïde lisse (crânes, masses musculaires, pieds)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    core.link(ob)
    ob.location, ob.scale = loc, scale
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    return core.shade_smooth(ob)


def spike(name, loc, height=0.3, radius=0.08, rot_deg=(0, 0, 0), seg=8):
    """Cône pointu (pointes dorsales, dents, griffes)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg,
                          radius1=radius, radius2=0.0, depth=height)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    core.link(ob)
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    return core.shade_smooth(ob)


def grid_surface(name, grid, thickness=None):
    """Maillage depuis une grille 2D de points [colonne][rangée] (membranes, voiles).
    `thickness` optionnel : None -> feuille simple face (legacy, ex. anciennes membranes
    fines solidifiées après coup). Sinon scalaire OU liste par RANGÉE (longueur = nb de
    rangées, diffusée sur toutes les colonnes) -> construit un volume fermé (coque) avec
    épaisseur VARIABLE par rangée, offset le long de la normale locale : permet une
    membrane épaisse à la racine (rangée 0, le long des os) et fine au bord libre
    (dernière rangée), comme une planche à voile — sans dépendre d'un Solidify à
    épaisseur constante."""
    nc, nr = len(grid), len(grid[0])
    if thickness is None:
        verts, faces = [], []
        for col in grid:
            verts.extend(col)
        for i in range(nc - 1):
            for j in range(nr - 1):
                a = i * nr + j
                faces.append((a, a + 1, a + nr + 1, a + nr))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        ob = bpy.data.objects.new(name, mesh)
        core.link(ob)
        return core.shade_smooth(ob)

    th = list(thickness) if isinstance(thickness, (list, tuple)) else [thickness] * nr
    bm = bmesh.new()
    top = [[bm.verts.new(p) for p in col] for col in grid]
    for i in range(nc - 1):
        for j in range(nr - 1):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
    bm.normal_update()
    bot = [[bm.verts.new(v.co - v.normal * th[min(j, len(th) - 1)])
            for j, v in enumerate(col)] for col in top]
    for i in range(nc - 1):
        for j in range(nr - 1):
            bm.faces.new((bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j], bot[i][j]))
    for j in range(nr - 1):  # bords colonne 0 / dernière colonne
        bm.faces.new((top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j]))
        bm.faces.new((bot[nc - 1][j], bot[nc - 1][j + 1], top[nc - 1][j + 1], top[nc - 1][j]))
    for i in range(nc - 1):  # bord rangée 0 (racine, os) / dernière rangée (bord libre)
        bm.faces.new((bot[i][0], bot[i + 1][0], top[i + 1][0], top[i][0]))
        bm.faces.new((top[i][nr - 1], top[i + 1][nr - 1], bot[i + 1][nr - 1], bot[i][nr - 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    core.link(ob)
    return core.shade_smooth(ob)


def ring_loft(name, rings, caps=True, subsurf_levels=2):
    """Volume lofté depuis des anneaux 3D successifs (même nombre de points).
    Construction type box-modeling : sections transversales → surface continue lissée."""
    m = len(rings[0])
    verts, faces = [], []
    for ring in rings:
        verts.extend(ring)
    for i in range(len(rings) - 1):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            faces.append((a, b, b + m, a + m))
    if caps:
        for ring, base in ((rings[0], 0), (rings[-1], (len(rings) - 1) * m)):
            cx = tuple(sum(p[k] for p in ring) / m for k in range(3))
            ci = len(verts)
            verts.append(cx)
            for j in range(m):
                faces.append((ci, base + j, base + (j + 1) % m))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    core.link(ob)
    core.shade_smooth(ob)
    if subsurf_levels:
        core.subsurf(ob, subsurf_levels)
    return ob


def boolean_diff(target, cutter, name=None, bevel_width=0.0, bevel_segments=2,
                  bevel_angle=35.0):
    """Soustrait `cutter` de `target` (creux d'orbite oculaire, etc.) via un modifier
    Boolean évalué par le depsgraph — même schéma que `core.realize_to_mesh` (bake vers
    un nouvel objet MESH, aucun bpy.ops nécessaire, robuste en headless). `cutter` est
    consommé (retiré de la scène) après l'opération.
    `bevel_width` (boucle 22, feedback « orbite = trou découpé net » ; défaut 0.0 =
    rétro-compat, arête vive inchangée) : adoucit l'arête de coupe vive qu'un booléen
    crée forcément — Bevel modifier limité par ANGLE (`bevel_angle`°, ne mord pas les
    arêtes déjà douces de la surface d'origine) empilé APRÈS le Boolean, baké dans le
    même mesh évalué -> un creux à bord arrondi au lieu d'un trou aux bords nets,
    sans 2e objet ni post-traitement séparé."""
    mod = target.modifiers.new('bool_diff', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter
    mod.solver = 'EXACT'
    if bevel_width > 0:
        bev = target.modifiers.new('bool_diff_bevel', 'BEVEL')
        bev.width = bevel_width
        bev.segments = bevel_segments
        bev.limit_method = 'ANGLE'
        bev.angle_limit = math.radians(bevel_angle)
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(deps), depsgraph=deps)
    new = bpy.data.objects.new(name or target.name, me)
    core.link(new)
    new.matrix_world = target.matrix_world
    for mat in target.data.materials:
        new.data.materials.append(mat)
    old_data = target.data
    bpy.data.objects.remove(target)
    if old_data.users == 0:
        bpy.data.meshes.remove(old_data)
    cutter_data = cutter.data
    bpy.data.objects.remove(cutter)
    if cutter_data.users == 0:
        bpy.data.meshes.remove(cutter_data)
    return core.shade_smooth(new)


def boolean_union(name, objs):
    """Soude plusieurs objets MESH en UN SEUL mesh continu par booléen UNION exact
    (boucle 22, thème « souder pas poser » — remplace des primitives qui se touchent/
    se pénètrent juste visuellement par une VRAIE surface fusionnée). Solveur EXACT
    (pas de voxel/remesh : piège connu, un fuse voxel gonfle ×3 les tubes fins, cf.
    CLAUDE.md) — chaîne un modifier Boolean UNION par objet supplémentaire sur le
    premier (host), puis bake en un seul mesh évalué (même schéma que `boolean_diff`).
    Tous les objets sources (y compris `objs[0]`) sont CONSOMMÉS. Les objets CURVE
    doivent être convertis en MESH par l'appelant d'abord (`core.realize_to_mesh`) —
    le modifier Boolean n'opère que sur des meshes.
    BUG mesuré (boucle 22) : par défaut (`material_mode='INDEX'`) le modifier Boolean
    NE fusionne PAS les listes de matériaux des opérandes -- il garde tel quel le
    `material_index` (entier LOCAL) de chaque face, interprété contre la liste de
    slots du seul HOST -> avec des objets à 1 slot chacun (`materials.assign`, le cas
    courant), TOUTES les faces valent index 0 et pointent donc sur le matériau du
    host, quel que soit le matériau d'origine de l'opérande (mesuré : membrane tissu
    -> rendu entièrement couleur os). Fix : `material_mode='TRANSFER'` (option native
    du modifier depuis 3.x, non documentée en évidence) fait exactement ce qu'il faut
    -- transfère/ajoute les matériaux réels des opérandes et remappe les faces vers
    la bonne liste combinée."""
    host, rest = objs[0], objs[1:]
    for i, o in enumerate(rest):
        mod = host.modifiers.new(f'bool_union_{i}', 'BOOLEAN')
        mod.operation = 'UNION'
        mod.object = o
        mod.solver = 'EXACT'
        mod.material_mode = 'TRANSFER'
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(host.evaluated_get(deps), depsgraph=deps)
    new = bpy.data.objects.new(name, me)
    core.link(new)
    new.matrix_world = host.matrix_world
    old_data = host.data
    bpy.data.objects.remove(host)
    if old_data.users == 0:
        bpy.data.meshes.remove(old_data)
    for o in rest:
        o_data = o.data
        bpy.data.objects.remove(o)
        if o_data.users == 0:
            bpy.data.meshes.remove(o_data)
    return core.shade_smooth(new)


def plane(name, size=60, z=0):
    mesh = bpy.data.meshes.new(name)
    s = size / 2
    mesh.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    mesh.update()
    return core.link(bpy.data.objects.new(name, mesh))


def frame_init(tangent):
    """Premier repère orthonormal (right/up) perpendiculaire à `tangent`, à partir
    d'une référence monde stable (Z, ou Y si `tangent` est quasi vertical). Public
    (chantier B, texture/rangées pilotées par l'anatomie) : partagé par
    `_anatomical_tube` (bx.organic) et `bx.detail.write_axis_uv`/`armor_rows`, plutôt
    que dupliqué — un seul repère transporté pour toute pièce tubulaire."""
    ref = Vector((0.0, 0.0, 1.0))
    if abs(tangent.dot(ref)) > 0.9:
        ref = Vector((0.0, 1.0, 0.0))
    right = tangent.cross(ref)
    if right.length < 1e-6:
        right = Vector((1.0, 0.0, 0.0))
    right.normalize()
    up = tangent.cross(right).normalized()
    return right, up


def frame_step(prev_tangent, prev_right, tangent):
    """Transport du repère (right/up) d'un segment au suivant par rotation MINIMALE
    (rotation-minimizing frame) : évite la torsion visible qu'un recalcul depuis une
    référence monde fixe provoquerait à chaque changement d'angle notable."""
    axis = prev_tangent.cross(tangent)
    sina = axis.length
    cosa = max(-1.0, min(1.0, prev_tangent.dot(tangent)))
    if sina < 1e-8:
        right = Vector(prev_right)
    else:
        axis = axis / sina
        angle = math.atan2(sina, cosa)
        right = Quaternion(axis, angle) @ prev_right
    right = right - tangent * right.dot(tangent)
    if right.length < 1e-6:
        right, _ = frame_init(tangent)
    else:
        right.normalize()
    up = tangent.cross(right).normalized()
    return right, up


def sample_path_frames(path_pts, n=48):
    """Échantillonne une polyligne monde `path_pts` en `n` points à ABSCISSE
    CURVILIGNE réelle (arc-length, pas un simple index de segment) + repère
    transporté (right/up, rotation-minimizing, cf. `frame_step`) à chaque
    échantillon. Retourne (positions, rights, ups, tangents, longueur_totale) —
    brique GÉNÉRIQUE partagée par `detail.write_axis_uv` (attribut shader `axis_uv`)
    et `detail.armor_rows` (rangées d'écailles qui suivent la courbure) : une seule
    implémentation du repère transporté pour tout ce qui a besoin de savoir
    « où je suis le long de l'axe » et « quel est le haut/le côté ici »."""
    pv = [Vector(p) for p in path_pts]
    seg_len = [(pv[i + 1] - pv[i]).length for i in range(len(pv) - 1)]
    total = sum(seg_len) or 1e-6
    cum = [0.0]
    for l in seg_len:
        cum.append(cum[-1] + l)
    positions, rights, ups, tangents = [], [], [], []
    right = up = prev_tan = None
    for i in range(n):
        u = i / max(1, n - 1)
        d = u * total
        j = 0
        while j < len(seg_len) - 1 and d > cum[j + 1]:
            j += 1
        f = (d - cum[j]) / max(seg_len[j], 1e-9)
        p = pv[j].lerp(pv[j + 1], f)
        tan = (pv[j + 1] - pv[j]).normalized() if seg_len[j] > 1e-9 else Vector((0, 0, -1))
        if right is None:
            right, up = frame_init(tan)
        else:
            right, up = frame_step(prev_tan, right, tan)
        prev_tan = tan
        positions.append(p)
        rights.append(right.copy())
        ups.append(up.copy())
        tangents.append(tan.copy())
    return positions, rights, ups, tangents, total


def transform_pts(pts, loc=(0, 0, 0), rot_deg=(0, 0, 0), scale=1.0, mirror=False):
    """Transforme des points locaux (ex: sortie de loi GVL) vers le monde."""
    rot = Euler([math.radians(a) for a in rot_deg]).to_matrix()
    out = []
    for p in pts:
        v = Vector(p) * scale
        if mirror:
            v.x = -v.x
        v = rot @ v + Vector(loc)
        out.append(tuple(v))
    return out
