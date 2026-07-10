"""bx.bake — étage générique HIGH→LOW (boucle 16, doctrine research/doctrine_bake_v1.md) :
peau continue à écailles imbriquées + plis d'articulation en normal map bakée, patine
modulée par courbure bakée, densité de bords perçue accrue SANS coût de rendu final.

Principe : un mesh LOW-poly (issu de `fuse_groups`, déjà dans la scène) reçoit un shell
HIGH-poly TEMPORAIRE (copie -> Remesh VOXEL dense -> couches Displace pilotées par
`spec['bake'][i]['surface']['layers']`) ; UV auto sur le LOW ; bake Cycles
selected_to_active (normal/AO/courbure) vers des PNG dans `maps/` ; le shell est détruit.
Tout est piloté par `spec['bake']` — aucune valeur dragon en dur ici (types de pièces et
profils génériques uniquement, cf. claude.md règle 2).

`spec['bake']` = liste de groupes :
  {id, parts:[...], exclude_like:[...], voxel|target_tris, maps:{normal,ao,curvature},
   margin_px, cage_extrusion, ao_samples,
   surface:{layers:[
     {type:'scales', scale, strength, mask:{axis,range,to}},
     {type:'wrinkles', zones:[{loc,radius,freq,strength,dir,mirror}]},
     {type:'micro', kind:'STUCCI'|'CLOUDS', scale, strength},
   ]}}

PIÈGES Blender 5.0 (bpy module headless) : pas de bake_type 'DISPLACEMENT' en Cycles ;
uv.smart_project/pack_islands + object.bake fonctionnent SANS temp_override tant que
view_layer.objects.active + select_set sont posés (testé empiriquement, pas de fenêtre
nécessaire en mode bpy-module) ; images normal/AO/courbure en colorspace Non-Color ;
un REMESH voxel détruit toute correspondance de vertex group -> on APPLIQUE le remesh en
mesh réel AVANT de calculer les masques, mais les Displace de détail restent des
modifiers VIVANTS (Cycles les évalue via le depsgraph au bake, pas besoin de les figer)."""
import math
import os
import time

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from . import core, feedback

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPS_DIR = os.path.join(ROOT, 'maps')


# ---------------------------------------------------------------------------
# Rassemblement d'objets (même convention que fuse_groups/armor : registre de
# parts -> objets, filtré par motifs de nom à exclure).
# ---------------------------------------------------------------------------

def gather_group_objects(registry, group):
    exclude = group.get('exclude_like', [])
    seen, out = set(), []
    for pid in group.get('parts', []):
        for o in registry.get(pid, []):
            if o.type != 'MESH' or o.name in seen:
                continue
            if any(x in o.name for x in exclude):
                continue
            seen.add(o.name)
            out.append(o)
    return out


# ---------------------------------------------------------------------------
# UV auto sur le LOW-poly (appelée à CHAQUE construction de scène, pas
# seulement `bake` : le mesh fusionné est déterministe par spec, donc le même
# code produit la même UV à chaque `build()` -> les maps bakées restent
# alignées avec le rendu final sans rien persister sur disque).
# ---------------------------------------------------------------------------

def uv_unwrap(ob, margin_px=4, resolution=2048):
    """smart_project + pack_islands, marge en pixels convertie en ratio UV (0..1)."""
    if ob.type != 'MESH' or not ob.data.polygons:
        return ob
    ratio = max(0.0005, margin_px / max(1, resolution))
    for o in bpy.context.scene.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=ratio)
    bpy.ops.uv.pack_islands(margin=ratio)
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)
    return ob


# ---------------------------------------------------------------------------
# Shell HIGH-poly temporaire : copie monde -> Remesh VOXEL dense (APPLIQUÉ,
# nécessaire pour que les masques de vertex group calculés ensuite retombent
# sur la bonne topologie) -> couches de détail (Displace VIVANTS).
# ---------------------------------------------------------------------------

def _duplicate_world_mesh(objs, name):
    bm = bmesh.new()
    for ob in objs:
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    out_me = bpy.data.meshes.new(name)
    bm.to_mesh(out_me)
    bm.free()
    ob = bpy.data.objects.new(name, out_me)
    core.link(ob)
    return ob


def _mesh_surface_area(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    area = sum(f.calc_area() for f in bm.faces)
    bm.free()
    return max(area, 1e-6)


def _voxel_size_for_budget(ob, target_tris=1_800_000):
    """voxel ≈ sqrt(2·aire_réelle/tris_cible) (remesh voxel ~2 tris/voxel de surface) —
    aire RÉELLE du mesh (bmesh calc_area), pas la bbox (un corps organique fin occupe
    une fraction de sa boîte englobante -> la formule bbox surestime largement)."""
    area = _mesh_surface_area(ob)
    voxel = math.sqrt(2.0 * area / max(1, target_tris))
    corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    diag = (Vector((max(c[i] for c in corners) for i in range(3))) -
            Vector((min(c[i] for c in corners) for i in range(3)))).length
    return max(0.0015, min(diag / 30, voxel))


def _apply_remesh(ob, voxel_size):
    rm = ob.modifiers.new('bake_remesh', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel_size
    rm.use_smooth_shade = True
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), depsgraph=deps)
    old = ob.data
    ob.data = me
    ob.modifiers.clear()
    if old.users == 0:
        bpy.data.meshes.remove(old)
    core.shade_smooth(ob)
    return ob


# ---------------------------------------------------------------------------
# Masques génériques (numpy, vertex groups) : réutilisent la même sémantique
# que `detail._axis_factor` (position/normale -> Map Range) mais matérialisés
# en poids de vertex group (nécessaire pour le champ `vertex_group` du
# modifier Displace, qui n'a pas d'équivalent Geometry Nodes ici).
# ---------------------------------------------------------------------------

def _fill_vertex_group(vg, weights, levels=48):
    """Remplit un VertexGroup via des poids quantifiés (`levels` paliers) : un seul
    appel `vg.add()` par palier sur la LISTE d'indices concernés (implémenté en C côté
    Blender) au lieu d'un appel par sommet -> des centaines de milliers de sommets se
    remplissent en quelques appels au lieu d'une boucle Python par sommet."""
    idx_all = np.arange(len(weights))
    qi = np.clip(np.round(weights * levels).astype(np.int32), 0, levels)
    for lvl in range(levels + 1):
        sel = idx_all[qi == lvl]
        if len(sel):
            vg.add(sel.tolist(), lvl / levels, 'REPLACE')


def _mask_vgroup_axis(ob, mask, name_hint='mask'):
    """mask = {'axis':'x'/'y'/'z'/'nx'/'ny'/'nz','range':[a,b],'to':[lo,hi]} — axe de
    POSITION ou de NORMALE (préfixe 'n', dorsal/ventral générique, même convention que
    detail._axis_factor) -> poids de vertex group clampés."""
    me = ob.data
    n = len(me.vertices)
    axis = mask['axis'].lower()
    frm = mask.get('range', (0.0, 1.0))
    to = mask.get('to', (0.0, 1.0))
    arr = np.empty(n * 3, dtype=np.float32)
    if axis.startswith('n'):
        me.vertices.foreach_get('normal', arr)
        idx = {'x': 0, 'y': 1, 'z': 2}[axis[1]]
    else:
        me.vertices.foreach_get('co', arr)
        idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    comp = arr.reshape(-1, 3)[:, idx]
    t = np.clip((comp - frm[0]) / max(1e-6, (frm[1] - frm[0])), 0.0, 1.0)
    w = np.clip(to[0] + t * (to[1] - to[0]), 0.0, 1.0)
    vg = ob.vertex_groups.new(name=f'{name_hint}_{len(ob.vertex_groups)}')
    _fill_vertex_group(vg, w)
    return vg.name


def _mask_vgroup_radial(ob, loc, radius, name_hint='wrinkle'):
    """Chute radiale (smoothstep) 1 au centre `loc` (monde) -> 0 au-delà de `radius` —
    plis d'articulation génériques, aucune connaissance anatomique en dur."""
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    d = np.linalg.norm(co - np.array(loc, dtype=np.float32), axis=1) / max(1e-6, radius)
    t = np.clip(1.0 - d, 0.0, 1.0)
    w = t * t * (3 - 2 * t)
    vg = ob.vertex_groups.new(name=f'{name_hint}_{len(ob.vertex_groups)}')
    _fill_vertex_group(vg, w)
    return vg.name


# ---------------------------------------------------------------------------
# Couches de surface (v1 : scales / wrinkles / micro) — Displace VIVANTS
# (pas besoin de les figer avant bake : Cycles évalue le depsgraph de l'objet
# HIGH sélectionné, modifiers compris).
# ---------------------------------------------------------------------------

def _add_displace(ob, name, tex_type='VORONOI', scale=1.0, strength=0.03, mid=0.5,
                  vertex_group=None, texture_coords='OBJECT', coords_object=None,
                  wood_type=None, turbulence=None):
    tex = bpy.data.textures.new(f'{ob.name}_{name}', tex_type)
    if hasattr(tex, 'noise_scale'):
        tex.noise_scale = scale
    if wood_type is not None and hasattr(tex, 'wood_type'):
        tex.wood_type = wood_type
    if turbulence is not None and hasattr(tex, 'turbulence'):
        tex.turbulence = turbulence
    d = ob.modifiers.new(name, 'DISPLACE')
    d.texture = tex
    d.strength = strength
    d.mid_level = mid
    d.texture_coords = texture_coords
    if coords_object is not None:
        d.texture_coords_object = coords_object
    d.direction = 'NORMAL'
    if vertex_group:
        d.vertex_group = vertex_group
    return d


def _apply_surface_layers(ob, layers):
    """Empile les couches `surface.layers` sur le shell HIGH-poly. Retourne la liste
    des objets HELPER (empties d'orientation des plis) créés, à supprimer après bake."""
    helpers = []
    for i, lay in enumerate(layers):
        typ = lay.get('type', 'scales')
        if typ in ('scales', 'micro'):
            default_kind = 'VORONOI' if typ == 'scales' else 'STUCCI'
            vgroup = _mask_vgroup_axis(ob, lay['mask'], f'{typ}{i}') if lay.get('mask') else None
            _add_displace(ob, f'{typ}{i}', tex_type=lay.get('kind', default_kind),
                          scale=lay.get('scale', 8.0), strength=lay.get('strength', 0.02),
                          mid=lay.get('mid', 0.5), vertex_group=vgroup)
        elif typ == 'wrinkles':
            for zi, z in enumerate(lay.get('zones', [])):
                locs = [z['loc']]
                dirs = [z.get('dir', (1.0, 0.0, 0.0))]
                if z.get('mirror'):
                    locs.append((-z['loc'][0], z['loc'][1], z['loc'][2]))
                    d0 = z.get('dir', (1.0, 0.0, 0.0))
                    dirs.append((-d0[0], d0[1], d0[2]))
                for si, (loc, dirv) in enumerate(zip(locs, dirs)):
                    emp = bpy.data.objects.new(f'{ob.name}_wemp{i}_{zi}_{si}', None)
                    core.link(emp)
                    emp.location = loc
                    dv = Vector(dirv)
                    if dv.length > 1e-6:
                        emp.rotation_euler = dv.to_track_quat('Z', 'Y').to_euler()
                    helpers.append(emp)
                    vgroup = _mask_vgroup_radial(ob, loc, z.get('radius', 0.6), f'wrinkle{i}_{zi}')
                    # `scale` = noise_scale WOOD littéral (même convention que scales/
                    # micro : PLUS PETIT -> bandes plus rapprochées/fines — pas un
                    # nombre de plis, calibré empiriquement ~0.02-0.05 pour des plis à
                    # l'échelle d'une articulation de quelques dizaines de cm).
                    _add_displace(ob, f'wrinkle{i}_{zi}_{si}', tex_type='WOOD',
                                 scale=z.get('scale', 0.03), strength=z.get('strength', 0.04),
                                 mid=0.5, vertex_group=vgroup, texture_coords='OBJECT',
                                 coords_object=emp, wood_type='BANDNOISE',
                                 turbulence=z.get('turbulence', 1.5))
    return helpers


# ---------------------------------------------------------------------------
# Bake Cycles selected_to_active : normal (tangent), AO, courbure (Pointiness
# -> ColorRamp -> Emission sur le HIGH, bake EMIT).
# ---------------------------------------------------------------------------

def _new_image(name, size):
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    return img


def _set_bake_target(ob, image):
    mat = bpy.data.materials.new(f'{ob.name}_baketarget_{image.name}')
    mat.use_nodes = True
    nt = mat.node_tree
    node = nt.nodes.new('ShaderNodeTexImage')
    node.image = image
    nt.nodes.active = node
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return mat


def _curvature_material():
    """Pointiness (Geometry Info, 0=creux..1=arête) -> ColorRamp -> Emission : bakée en
    EMIT sur le HIGH -> map de courbure réutilisable comme masque de patine (matériau)."""
    mat = bpy.data.materials.new('bake_curvature')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[1].position = 0.75
    em = nt.nodes.new('ShaderNodeEmission')
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(geo.outputs['Pointiness'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return mat


def _select_for_bake(low, high):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low


def _bake(low, high, map_type, image, samples=16, margin=4, cage_extrusion=0.06,
          normal_space='TANGENT'):
    _set_bake_target(low, image)
    _select_for_bake(low, high)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.samples = samples
    cy.device = 'CPU'
    bk = sc.render.bake
    bk.use_selected_to_active = True
    bk.margin = margin
    bk.cage_extrusion = cage_extrusion
    bk.use_clear = True
    if map_type == 'NORMAL':
        bk.normal_space = normal_space
    kw = dict(type=map_type, use_selected_to_active=True, margin=margin,
             cage_extrusion=cage_extrusion)
    if map_type == 'NORMAL':
        kw['normal_space'] = normal_space
    bpy.ops.object.bake(**kw)


def _save(image, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    return path


# ---------------------------------------------------------------------------
# Entrée principale.
# ---------------------------------------------------------------------------

def run(spec, fast=False):
    entries = spec.get('bake', [])
    if not entries:
        return {'groups': []}
    spec_name = spec.get('name', 'spec')
    parts = feedback.spec_parts(spec)
    report = {'groups': []}
    for g in entries:
        t_all = time.time()
        registry = feedback.part_registry(parts)
        low_objs = gather_group_objects(registry, g)
        if not low_objs:
            report['groups'].append({'id': g.get('id', '?'), 'error': 'no objects found'})
            continue
        # rétro-compat : `low` = premier objet du groupe (v1, un seul mesh fusionné).
        low = low_objs[0]
        gid = g.get('id', low.name)

        t0 = time.time()
        high = _duplicate_world_mesh(low_objs, f'{low.name}_hipoly')
        voxel = g.get('voxel')
        target_tris = g.get('target_tris', 500_000 if fast else 1_800_000)
        if not voxel:
            voxel = _voxel_size_for_budget(high, target_tris=target_tris)
        _apply_remesh(high, voxel)
        t_shell = time.time() - t0
        tri_count = len(high.data.polygons)  # quasi tout quad/tri via remesh voxel

        t0 = time.time()
        layers = g.get('surface', {}).get('layers', [])
        helpers = _apply_surface_layers(high, layers)
        t_layers = time.time() - t0

        maps = g.get('maps', {'normal': 2048, 'ao': 1024, 'curvature': 1024})
        if fast:
            maps = {k: (512 if k == 'normal' else 256) for k in maps}
        margin = g.get('margin_px', 4)
        cage = g.get('cage_extrusion', 0.06)
        ao_samples = max(4, min(64, g.get('ao_samples', 8 if fast else 24)))

        paths = {}
        t_bake = {}
        os.makedirs(MAPS_DIR, exist_ok=True)

        t0 = time.time()
        img_n = _new_image(f'{spec_name}_{gid}_normal', maps.get('normal', 2048))
        _bake(low, high, 'NORMAL', img_n, samples=8, margin=margin, cage_extrusion=cage)
        paths['normal'] = _save(img_n, os.path.join(MAPS_DIR, f'{spec_name}_{gid}_normal.png'))
        t_bake['normal'] = time.time() - t0

        t0 = time.time()
        img_ao = _new_image(f'{spec_name}_{gid}_ao', maps.get('ao', 1024))
        _bake(low, high, 'AO', img_ao, samples=ao_samples, margin=margin, cage_extrusion=cage)
        paths['ao'] = _save(img_ao, os.path.join(MAPS_DIR, f'{spec_name}_{gid}_ao.png'))
        t_bake['ao'] = time.time() - t0

        t0 = time.time()
        curv_mat = _curvature_material()
        high.data.materials.clear()
        high.data.materials.append(curv_mat)
        img_c = _new_image(f'{spec_name}_{gid}_curvature', maps.get('curvature', 1024))
        _bake(low, high, 'EMIT', img_c, samples=8, margin=margin, cage_extrusion=cage)
        paths['curvature'] = _save(img_c, os.path.join(MAPS_DIR, f'{spec_name}_{gid}_curvature.png'))
        t_bake['curvature'] = time.time() - t0

        # nettoyage : shell + helpers supprimés, scène propre pour la suite.
        low.data.materials.clear()
        hi_data = high.data
        for emp in helpers:
            bpy.data.objects.remove(emp)
        bpy.data.objects.remove(high)
        if hi_data.users == 0:
            bpy.data.meshes.remove(hi_data)

        report['groups'].append({
            'id': gid, 'voxel': round(voxel, 5), 'tris': tri_count,
            'timings': {'shell': round(t_shell, 2), 'layers': round(t_layers, 2),
                        **{f'bake_{k}': round(v, 2) for k, v in t_bake.items()},
                        'total': round(time.time() - t_all, 2)},
            'maps': paths,
        })
    return report
