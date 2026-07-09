"""T8 — Inversion I1 : écailles GÉOMÉTRIQUES chevauchantes vs bruit de displacement.
Même patch bombé, deux traitements, rendu MACRO (l'écaille remplit le cadre), puis
densité de bords (Sobel) : la géo doit produire des plaques discrètes lisibles, le bruit non."""
import numpy as np

import _common as C
from bx import core, detail, feedback, ops
import bpy


def patch():
    core.reset()
    dome = ops.blob('dome', loc=(0, 0, 0), scale=(1.2, 1.2, 1.0), seg=64)
    return dome


def macro_edge(name, cam=(0, -2.4, 0.9)):
    core.clay()
    core.camera(cam, target=(0, 0, 0.55), lens=85)
    out = C.RENDERS + f'/{name}.png'
    core.render(out, res=(640, 480), samples=20)
    img = bpy.data.images.load(out)
    px = np.array(img.pixels[:], np.float32).reshape(480, 640, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    return out, round(feedback.edge_density(px), 4)


# A. bruit de displacement seul (approche actuelle)
d = patch()
detail.displace_layers(d, [{'type': 'VORONOI', 'size': 0.22, 'strength': 0.06,
                            'coords': 'OBJECT'}], subdiv=3)
noise_png, noise_edges = macro_edge('t8_displacement_noise')

# B. écailles carénées chevauchantes (inversion I1)
d = patch()
plate = detail.keeled_scale(size=1.0, length=1.6, keel=0.5, lift=0.35)
detail.armor_scales(d, plate, density=1400.0, scale=(0.11, 0.16), caudal=(0, 1, 0),
                    curvature=False)
scales_png, scales_edges = macro_edge('t8_geo_scales')

C.log('t8_geo_scales', {
    'inversion': 'I1 — les écailles SONT de la géométrie, pas du bruit',
    'displacement_noise': {'render': noise_png, 'edge_density': noise_edges},
    'geo_keeled_scales': {'render': scales_png, 'edge_density': scales_edges},
    'edge_gain_x': round(scales_edges / max(noise_edges, 1e-6), 2),
    'geo_reads_as_scales': scales_edges > noise_edges * 1.3,
})
