# research/ — convergence des deux docs + bancs d'essai

Analyse des deux documents de recherche (pipeline Claude+Blender headless), extraction des
**solutions convergentes**, et **tests empiriques** de chacune sous bpy 5.0.1 avant de les
câbler dans le pipeline.

- **`convergence.md`** — analyse : ce sur quoi les deux docs convergent (adopté), leur seul
  point de divergence (fusion Skin vs Voxel Remesh, tranché par l'expérience), et les résultats.
- **`tests/`** — un test par solution, exécutable seul : `python3 research/tests/t*.py`.
  - `t1_skin_body.py` / `t2_voxel_fuse.py` — les deux candidats du corps continu (divergence).
  - `t3_bvh_checks.py` — sanity checks BVH sur cas témoins (bon/mauvais connus).
  - `t4_t5_detail.py` — displace en couches + écailles geometry-nodes sur le corps fusionné.
  - `t6_t7_feedback.py` — planche-contact 4 vues → 1 PNG + score IoU de silhouette.
- **`logs/`** — sortie JSON de chaque test (mesures numériques reproductibles).
- **`renders/`** — rendus clay produits par les tests.

## Verdict

Le gagnant du point de divergence est la **fusion Voxel Remesh + Laplacian** (doc 2) :
corps étanche, une seule île, 0 auto-intersection — là où le modifier Skin (doc 1) laisse
des arêtes non-manifold et 26 triangles auto-intersectés. Les cinq solutions convergentes
(validation BVH, planche-contact, IoU, displace, écailles geonodes) passent toutes leurs
tests témoins. Architecture câblée dans `pipeline/bx/{validate,fuse,detail,feedback}.py` et
exposée par `run.py` (`validate`, `sheet`, `forge --sheet`).
