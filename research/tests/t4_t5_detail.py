"""T4+T5 — Convergences C4 (Displace en couches) et C5 (écailles Geometry Nodes),
appliquées au quadrupède fusionné de T2 (chaîne complète : fuse → detail).
Mesures : le displace change réellement la géométrie (déplacement moyen des verts),
le mesh reste étanche/1 île ; les geonodes instancient bien (delta de faces) ; rendus."""
import numpy as np

import _common as C
from bx import core, detail, fuse, validate
from t2_voxel_fuse import quadruped_parts


def evaluated_verts(ob):
    import bpy
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), depsgraph=deps)
    n = len(me.verts) if hasattr(me, 'verts') else len(me.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get('co', co)
    bpy.data.meshes.remove(me)
    return co.reshape(-1, 3)


core.reset()
body = fuse.voxel_fuse([fuse.join_to_mesh(quadruped_parts(), 'raw')],
                       target_res=220, name='body')
base = validate.geometry_report(body)
v_before = evaluated_verts(body)

# --- T4 : trois couches de displace (macro plis / écailles / micro rides) ---
with C.timer() as t4:
    detail.displace_layers(body, [
        {'type': 'CLOUDS', 'size': 1.6, 'strength': 0.10, 'coords': 'OBJECT'},   # plis macro
        {'type': 'VORONOI', 'size': 0.35, 'strength': 0.05, 'coords': 'OBJECT'},  # écailles moy.
        {'type': 'CLOUDS', 'size': 0.12, 'strength': 0.015, 'coords': 'OBJECT'},  # micro rides
    ], subdiv=1)
after_disp = validate.geometry_report(body)
v_after = evaluated_verts(body)
# déplacement réel : distance moyenne au vertex le plus proche du mesh de base
sample = v_after[np.random.default_rng(0).choice(len(v_after), 400, replace=False)]
d = np.sqrt(((sample[:, None, :] - v_before[None, ::7, :]) ** 2).sum(-1)).min(1)
disp_stats = {'mean_offset': round(float(d.mean()), 4), 'max_offset': round(float(d.max()), 4)}
render_disp = C.clay_render('t4_displace_layers')

# --- T5 : écailles explicites par Geometry Nodes -----------------------------
plate = detail.scale_plate()
with C.timer() as t5:
    detail.scales(body, plate, density=140.0, scale=(0.05, 0.12), curvature=True)
after_scales = validate.geometry_report(body)
render_scales = C.clay_render('t5_geonodes_scales', cam_loc=(6.5, -5, 3.5))

added = after_scales['faces'] - after_disp['faces']
C.log('t4_t5_detail', {
    't4_displace': {'seconds': t4.dt, 'faces_before': base['faces'],
                    'faces_after': after_disp['faces'], **disp_stats,
                    'still_watertight': after_disp['watertight'],
                    'still_single_body': after_disp['single_body'],
                    'geometry_changed': disp_stats['mean_offset'] > 0.01,
                    'render': render_disp},
    't5_scales': {'seconds': t5.dt, 'faces_added_by_instances': added,
                  'approx_instances': added // 5,  # 5 faces par plaque d'écaille
                  'instancing_works': added > 1000, 'render': render_scales},
})
