"""T10 — les nodes SDF Grid (couche 1 MACRO, voie A) existent-ils et produisent-ils
un mesh en bpy 5.0.1 headless ? Test FONCTIONNEL : deux sphères qui se chevauchent
→ Mesh to SDF Grid → SDF Grid Boolean (UNION) → Grid to Mesh → verts > 0.
Sinon : voie B (proximity displacement). On sonde aussi les noms de nodes voisins
(Laplacian/offset) pour documenter ce qui est câblable."""
from _common import log

import bpy  # noqa: E402
from bx import core, ops  # noqa: E402

core.reset()

PROBE = ['GeometryNodeMeshToSDFGrid', 'GeometryNodeSDFGridBoolean',
         'GeometryNodeGridToMesh', 'GeometryNodeSDFGridFillet',
         'GeometryNodeGridLaplacianSmooth', 'GeometryNodeMeshToVolume',
         'GeometryNodeVolumeToMesh']
avail = {}
ng_probe = bpy.data.node_groups.new('probe', 'GeometryNodeTree')
for idname in PROBE:
    try:
        ng_probe.nodes.new(idname)
        avail[idname] = True
    except RuntimeError:
        avail[idname] = False
bpy.data.node_groups.remove(ng_probe)

verts = -1
error = None
if avail['GeometryNodeMeshToSDFGrid'] and avail['GeometryNodeGridToMesh']:
    try:
        a = ops.blob('a', loc=(0, 0, 0), scale=(1, 1, 1), seg=24)
        b = ops.blob('b', loc=(0.8, 0, 0), scale=(1, 1, 1), seg=24)
        ng = bpy.data.node_groups.new('sdf', 'GeometryNodeTree')
        ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        n_in, n_out = ng.nodes.new('NodeGroupInput'), ng.nodes.new('NodeGroupOutput')
        sdf_a = ng.nodes.new('GeometryNodeMeshToSDFGrid')
        sdf_b = ng.nodes.new('GeometryNodeMeshToSDFGrid')
        info = ng.nodes.new('GeometryNodeObjectInfo')
        info.inputs['Object'].default_value = b
        info.transform_space = 'RELATIVE'
        boolean = ng.nodes.new('GeometryNodeSDFGridBoolean')
        boolean.operation = 'UNION'
        to_mesh = ng.nodes.new('GeometryNodeGridToMesh')
        lk = ng.links.new
        for s in (sdf_a, sdf_b):
            if 'Voxel Size' in s.inputs:
                s.inputs['Voxel Size'].default_value = 0.05
        lk(n_in.outputs['Geometry'], sdf_a.inputs['Mesh'])
        lk(info.outputs['Geometry'], sdf_b.inputs['Mesh'])
        # en UNION l'entrée devient un multi-socket 'Grid' (comme Mesh Boolean)
        lk(sdf_a.outputs['SDF Grid'], boolean.inputs['Grid'])
        lk(sdf_b.outputs['SDF Grid'], boolean.inputs['Grid'])
        lk(boolean.outputs['Grid'], to_mesh.inputs['Grid'])
        lk(to_mesh.outputs['Mesh'], n_out.inputs['Geometry'])
        mod = a.modifiers.new('sdf', 'NODES')
        mod.node_group = ng
        deps = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(a.evaluated_get(deps), depsgraph=deps)
        verts = len(me.vertices)
    except Exception as e:  # noqa: BLE001 — on documente l'échec exact
        error = f'{type(e).__name__}: {e}'

log('t10_sdf_nodes', {
    'nodes': avail, 'union_mesh_verts': verts, 'error': error,
    'verdict': 'VOIE A OK' if verts > 0 else 'VOIE B (proximity)',
})
