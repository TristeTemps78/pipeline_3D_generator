"""T2 — Candidat doc 2 : primitives interpénétrées → join + Remesh VOXEL + Laplacian.
Même quadrupède cible que T1, mais assemblé façon pipeline actuel (blobs + tubes).
Mesure AVANT fusion (assemblage brut) et APRÈS, pour quantifier le saut."""
import _common as C
from bx import core, fuse, ops, validate


def quadruped_parts():
    parts = []
    # torse + hanches + épaules (blobs qui s'interpénètrent)
    parts.append(ops.blob('torso', loc=(0.3, 0, 1.45), scale=(1.3, 0.55, 0.62)))
    parts.append(ops.blob('hips', loc=(-0.8, 0, 1.4), scale=(0.7, 0.48, 0.52)))
    parts.append(ops.blob('chest', loc=(1.3, 0, 1.55), scale=(0.65, 0.5, 0.55)))
    # cou + tête + queue en tubes coniques
    parts.append(ops.tube('neck', [(1.4, 0, 1.62), (1.9, 0, 1.95), (2.4, 0, 2.25)],
                          [0.30, 0.22, 0.18]))
    # la tête doit INTERPÉNÉTRER le cou : le remesh voxel ne ponte pas les vides
    # (leçon du 1er run : gap de 5 cm → coquille séparée, détectée par `islands`)
    parts.append(ops.blob('head', loc=(2.75, 0, 2.3), scale=(0.6, 0.28, 0.3)))
    parts.append(ops.tube('tail', [(-0.9, 0, 1.42), (-1.6, 0, 1.3), (-2.4, 0, 1.15),
                                   (-3.2, 0, 1.05)], [0.3, 0.22, 0.12, 0.04]))
    # 4 pattes en tubes 3 segments
    for x in (-0.8, 1.4):
        for side in (1, -1):
            parts.append(ops.tube(f'leg_{x}_{side}',
                                  [(x, side * 0.45, 1.25), (x + 0.15, side * 0.62, 0.62),
                                   (x + 0.05, side * 0.62, 0.28), (x + 0.3, side * 0.62, 0.07)],
                                  [0.24, 0.15, 0.11, 0.10]))
    return parts


def run():
    core.reset()
    raw = fuse.join_to_mesh(quadruped_parts(), 'raw_assembly')
    before = validate.geometry_report(raw)
    with C.timer() as t:
        body = fuse.voxel_fuse([raw], target_res=220, smooth_iters=5,
                               smooth_lambda=0.5, name='voxel_quadruped')
    after = validate.geometry_report(body)
    render = C.clay_render('t2_voxel_quadruped')
    return C.log('t2_voxel_fuse', {'method': 'join + REMESH voxel + laplacian (doc 2)',
                                   'fuse_seconds': t.dt, 'before_fuse': before,
                                   'after_fuse': after, 'render': render})


if __name__ == '__main__':
    run()
