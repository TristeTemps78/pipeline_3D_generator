"""T6+T7 — Convergences C2 (planche-contact 1 PNG) et C3 (score IoU de silhouette).
T6 : 4 vues clay assemblées en un seul PNG via numpy → vérifie dimensions & coût unique.
T7 : IoU témoin — identique→1.0, corps déformé→<1, cible doc 2 : >0.85 acte le blocage."""
import numpy as np

import _common as C
from bx import core, feedback, fuse, ops
from t2_voxel_fuse import quadruped_parts


def build_body(scale_z=1.0):
    core.reset()
    body = fuse.voxel_fuse([fuse.join_to_mesh(quadruped_parts(), 'raw')],
                           target_res=200, name='body')
    body.scale = (1, 1, scale_z)
    ops.grid_surface('ground', [[(x, y, 0) for y in (-6, 0, 6)] for x in (-6, 0, 6)])
    core.clay()
    return body


# --- T6 : planche-contact 4 vues → 1 PNG ------------------------------------
build_body()
sheet, views = feedback.contact_sheet(
    C.RENDERS + '/t6_contact_sheet.png', res=(384, 288), samples=10,
    target=(0, 0, 1.5))
import bpy
img = bpy.data.images.load(sheet)
sheet_dims = tuple(img.size)  # attendu 768 x 576 (2×2 de 384×288)
bpy.data.images.remove(img)

# --- T7 : IoU témoin ---------------------------------------------------------
build_body(scale_z=1.0)
ref_mask = feedback.silhouette(axis='side', res=(384, 288), target=(0, 0, 1.5))
iou_identical = feedback.iou(ref_mask, ref_mask)
props_ref = feedback.proportions(ref_mask)

build_body(scale_z=1.9)  # créature étirée verticalement → forme différente
tall_mask = feedback.silhouette(axis='side', res=(384, 288), target=(0, 0, 1.5))
iou_distorted = feedback.iou(ref_mask, tall_mask)
props_tall = feedback.proportions(tall_mask)

C.log('t6_t7_feedback', {
    't6_contact_sheet': {
        'views': views, 'stitched_png': sheet, 'dims': sheet_dims,
        'expected_dims': [768, 576], 'single_png': True,
        'pass': list(sheet_dims) == [768, 576]},
    't7_iou': {
        'iou_identical': round(iou_identical, 4),
        'iou_distorted_1.9x_tall': round(iou_distorted, 4),
        'proportions_ref': props_ref, 'proportions_tall': props_tall,
        'metric_discriminates': iou_identical > 0.99 and iou_distorted < 0.85,
        'pass': iou_identical > 0.99 and iou_distorted < iou_identical},
})
