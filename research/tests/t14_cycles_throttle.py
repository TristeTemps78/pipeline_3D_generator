"""T14 — throttling Cycles (couche 4, research/detail_architecture.md).
Scène dragon réelle, cadrage hero, rendu --fast ×2 par config :
  A = réglages actuels (core.render nu)
  B = throttle : bounces 6 (diffuse 2, glossy 3), caustiques OFF,
      adaptive sampling threshold 0.03, use_persistent_data=True.
Verdict attendu : B1 plus rapide que A1 à qualité égale (diff pixel faible),
B2 << B1 (BVH persistant entre deux rendus d'une même session = la boucle interne).
"""
import os

import numpy as np

from _common import ROOT, RENDERS, log, timer

import bpy  # noqa: E402
from bx import core, organic, feedback  # noqa: E402

import json

SPEC = os.path.join(ROOT, 'specs', 'dragon_got.json')
RES, SAMPLES = (640, 480), 16


def throttle(on):
    cy = bpy.context.scene.cycles
    rd = bpy.context.scene.render
    if on:
        cy.max_bounces = 6
        cy.diffuse_bounces = 2
        cy.glossy_bounces = 3
        cy.caustics_reflective = cy.caustics_refractive = False
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = 0.03
        rd.use_persistent_data = True
    else:
        cy.max_bounces = 12
        cy.diffuse_bounces = 4
        cy.glossy_bounces = 4
        cy.caustics_reflective = cy.caustics_refractive = True
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = 0.01
        rd.use_persistent_data = False


def render_pair(tag):
    times, px = [], None
    for i in (1, 2):
        out = os.path.join(RENDERS, f't14_{tag}{i}.png')
        with timer() as t:
            core.render(out, res=RES, samples=SAMPLES)
        times.append(t.dt)
        if i == 1:
            img = bpy.data.images.load(out)
            px = np.array(img.pixels[:], dtype=np.float32).reshape(RES[1], RES[0], 4)[::-1, :, :3]
            bpy.data.images.remove(img)
    return times, px


with open(SPEC) as f:
    spec = json.load(f)
organic.build(spec)
hero = spec.get('scene', {}).get('hero', {})
tgt = tuple(hero.get('target', (0, 0, 2)))
core.rim_setup(target=tgt, **spec.get('scene', {}).get('rim', {}))
core.camera(tuple(hero.get('cam', (5, -6, 3))), target=tgt, lens=hero.get('lens', 70))

throttle(False)
t_base, px_base = render_pair('base')
throttle(True)
t_thr, px_thr = render_pair('thr')

diff = float(np.abs(px_base - px_thr).mean())
log('t14_cycles_throttle', {
    'res': RES, 'samples': SAMPLES,
    'baseline_s': t_base, 'throttle_s': t_thr,
    'gain_first_render': round(1 - t_thr[0] / t_base[0], 3),
    'gain_second_render': round(1 - t_thr[1] / t_base[0], 3),
    'mean_abs_pixel_diff': round(diff, 5),
    'edge_density_base': round(feedback.edge_density(px_base), 4),
    'edge_density_thr': round(feedback.edge_density(px_thr), 4),
    'verdict': 'OK' if diff < 0.02 and t_thr[1] < t_base[0] else 'À JUGER',
})
