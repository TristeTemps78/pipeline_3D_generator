"""T3 — Convergence C1 : sanity checks BVH avant rendu.
Vérifie chaque check sur des cas TÉMOINS connus (bon ET mauvais) :
 1. auto-intersection : sphère propre (attendu 0) vs deux cubes fusionnés (attendu >0)
 2. chevauchement inter-objets : sphères disjointes (0) vs interpénétrées (>0)
 3. contact sol : pied posé / flottant / traversant → statuts attendus."""
import _common as C
from bx import core, fuse, ops, validate

results = {}

# --- 1. auto-intersection -----------------------------------------------
core.reset()
clean = ops.blob('clean_sphere', loc=(0, 0, 2))
rep_clean = validate.geometry_report(clean)

bad = fuse.join_to_mesh([ops.blob('a', loc=(0, 0, 2), scale=(1, 1, 1)),
                         ops.blob('b', loc=(0.8, 0, 2), scale=(1, 1, 1))], 'bad_join')
rep_bad = validate.geometry_report(bad)
results['self_intersection'] = {
    'clean_sphere_tris': rep_clean['self_intersecting_tris'],
    'overlapping_join_tris': rep_bad['self_intersecting_tris'],
    'pass': rep_clean['self_intersecting_tris'] == 0 and rep_bad['self_intersecting_tris'] > 0,
}

# --- 2. chevauchement entre objets (dents vs mâchoire…) ------------------
core.reset()
s1 = ops.blob('s1', loc=(0, 0, 2))
s2_far = ops.blob('s2_far', loc=(3, 0, 2))
s3_hit = ops.blob('s3_hit', loc=(1.2, 0, 2))
results['pair_overlap'] = {
    'separated': validate.pair_overlap(s1, s2_far),
    'interpenetrating': validate.pair_overlap(s1, s3_hit),
    'pass': validate.pair_overlap(s1, s2_far) == 0 and validate.pair_overlap(s1, s3_hit) > 0,
}

# --- 3. contact sol par lancer de rayons ---------------------------------
core.reset()
ground = ops.grid_surface('ground', [[(x, y, 0) for y in (-5, 0, 5)] for x in (-5, 0, 5)])
cases = {'grounded': 1.0, 'floating': 1.35, 'clipping': 0.7}  # sphères rayon 1
got = {}
for name, z in cases.items():
    foot = ops.blob(f'foot_{name}', loc=(0, 0, z))
    got[name] = validate.ground_contact(foot, ground)
results['ground_contact'] = {
    **got, 'pass': all(got[k]['status'] == k for k in cases),
}

results['all_pass'] = all(v['pass'] for v in results.values())
C.log('t3_bvh_checks', results)
