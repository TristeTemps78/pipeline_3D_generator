"""T9 — Inversion I2 (réf côte-à-côte) + I4 (matériau SSS cuivré) + I7 (rim light).
Sur le même corps : rendu CLAY vs rendu peau-cuivrée-SSS-rim, chacun comparé côte à côte
à la frame de réf Drogon. Le compare_sheet doit montrer numériquement que le cuivre+SSS
rapproche la couleur de la cible mesurée (~0.24,0.16,0.14, part cuivre ~0.43)."""
import os

import _common as C
from bx import core, feedback, fuse, materials, detail
from t2_voxel_fuse import quadruped_parts

REF = os.path.join(C.ROOT, 'references', 'drogon_body_flight.png')
CAM = (5.0, -5.0, 2.0)
TGT = (0, 0, 1.5)


def body():
    core.reset()
    b = fuse.voxel_fuse([fuse.join_to_mesh(quadruped_parts(), 'raw')],
                        target_res=200, name='body')
    return b


# A. clay (approche actuelle : gris neutre)
b = body()
core.clay()
cmp_clay = feedback.compare_sheet(C.RENDERS + '/t9_compare_clay.png', REF,
                                  CAM, TGT, res=(560, 560), samples=18, lens=60)

# B. peau cuivrée SSS + écailles carénées + rim light (inversions I1+I4+I7)
b = body()
skin = materials.reptile_scales('dragon_skin', base=(0.05, 0.028, 0.022),
                                tint=(0.42, 0.16, 0.09), scale=9, scale2=26,
                                bump=0.9, rough=0.48, sss=0.22)
materials.assign(b, skin)
plate = detail.keeled_scale(size=1.0, length=1.5, keel=0.32, lift=0.14)
detail.armor_scales(b, plate, density=900.0, scale=(0.05, 0.08), caudal=(0, -1, 0),
                    curvature=True)
materials.assign(plate, skin)
core.rim_setup(target=TGT)
cmp_skin = feedback.compare_sheet(C.RENDERS + '/t9_compare_skin.png', REF,
                                  CAM, TGT, res=(560, 560), samples=32, lens=60)


def gap(c):
    r, g = c['render']['color']['mean'], c['ref']['color']['mean']
    return round(sum((a - b) ** 2 for a, b in zip(r, g)) ** 0.5, 3)


C.log('t9_ref_compare', {
    'inversions': 'I2 réf côte-à-côte · I4 SSS cuivré · I7 rim light',
    'ref_target': cmp_clay['ref'],
    'clay': {**cmp_clay['render'], 'color_gap_L2': gap(cmp_clay)},
    'copper_skin': {**cmp_skin['render'], 'color_gap_L2': gap(cmp_skin)},
    'copper_closes_gap': gap(cmp_skin) < gap(cmp_clay),
    'copper_fraction_up': (cmp_skin['render']['color']['copper_fraction']
                           > cmp_clay['render']['color']['copper_fraction']),
    'sheets': [cmp_clay['sheet'], cmp_skin['sheet']],
})
