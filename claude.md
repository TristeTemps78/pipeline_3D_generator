# Pipeline 3D — Claude + Blender (bpy headless)

## État actuel
Cible fixée par l'utilisateur : `references/drogon_*.png` (Drogon qualité film, extrait du mp4). Écart couleur mesuré et **halvé** cette boucle (clay→cuivre-SSS-rim). Tête rendue côte-à-côte avec la réf : step_027. Prochains écarts mesurés : densité de bords 0.15 vs 0.24 réf (→ écailles GÉO sur cou/tête), reliefs crâniens osseux, cuivre à tempérer (part 0.79 vs 0.42).

## Inversions testées (research/inversions.md — « fais le contraire »)
Consigne utilisateur : inverser mes hypothèses, noter, tester. 4 inversions gagnantes câblées :
- **I1** écailles = GÉOMÉTRIE, pas bruit (`detail.keeled_scale`+`armor_scales`) : ×162 densité de bords vs voronoi (t8).
- **I2** réf CÔTE À CÔTE à chaque rendu (`feedback.compare_sheet` + `edge_density`/`color_stats`) : plus de rendu orphelin. Cmd `run.py compare <spec> <ref>`.
- **I4** matériau SSS cuivré (`materials.reptile_scales(sss=…)`) : écart couleur 0.524→0.238 (t9).
- **I7** contre-jour rim (`core.rim_setup`) : révèle bords d'écailles/membrane sur fond noir.
À venir : I3 macro par région, I5 optimiseur IoU, I6 masques de densité par groupe de vertex.

## Architecture (stable)
- `pipeline/bx/` : core (dont `clay()` : validation géométrie, lumière uniforme, matériaux neutres), ops (tube, blob, spike, grid_surface, **ring_loft** = volumes par sections), organic (builders : ground, spine+crête, head lofté, wing, limb+orteils griffus), materials (ignorés en clay).
- **Étapes validées (research/convergence.md, testées sous bpy 5.0.1) :**
  - `bx/validate.py` — sanity checks BVH AVANT rendu (C1) : étanchéité, îles, auto-intersections, chevauchements de paires, contact sol (pieds). Sortie numérique, coût rendu nul.
  - `bx/fuse.py` — corps continu étanche. **`voxel_fuse` = voie par défaut** (join + Remesh VOXEL + Laplacian préservant le volume) : bat le modifier Skin (non-manifold + auto-intersections) au banc d'essai. `voxel_size = clamp(diag_bbox/target_res)`. `skin_body` conservé comme blockout léger.
  - `bx/detail.py` — micro-détail sans sculpt (C4/C5) : `displace_layers` (3 couches macro/écailles/rides) + `scales` (geonodes Distribute+Instance, densité pilotée par la courbure Edge Angle).
  - `bx/feedback.py` — boucle compressée (C2/C3) : `contact_sheet` (4 vues → 1 PNG via numpy), `silhouette`/`iou` (score de proportion, cible > 0.85), `proportions`.
- Étapes fuse/detail pilotées par la spec (champs optionnels `fuse` / `detail`) → n'affectent que les specs qui les déclarent. Démo bout-en-bout : `specs/creature_fused_demo.json`.
- `pipeline/gvl/` : lois (+ **superellipse** : sections crâniennes anguleuses) + vocabulary.json.
- Spec = source de vérité : `specs/dragon_got.json`. Cmds : `python3 pipeline/run.py forge <spec> [--fast] [--clay] [--sheet]` · `validate <spec>` (checks BVH, sans rendu) · `sheet <spec> [--fast]` (planche-contact).
- Méthode retenue : géométrie par sections loftées (pas d'assemblage de blobs), validation en clay, shaders EN DERNIER (le look feu doré des boucles 1-2 existe dans materials.py mais est désactivé tant que la géométrie n'est pas validée).
- Tête = lofts `upper`/`lower` (sections y,w,h surchargeables dans la spec), mâchoire ouverte `gape`°, dents = tubes courbes, cornes = spirale log pitch -35 (balayage arrière).

## Réalisé
- v1 blockout ; boucle 2 (tête blobs + shaders feu) rejetée par l'utilisateur : pieds moches, tête/gueule/dents/yeux/écailles pas crédibles, trop sombre.
- Boucle 3 : refonte tête en lofts superellipse (crâne crocodilien continu, gueule 26°, 22 dents courbes, yeux sous arcades, narines, couronne 5 paires cornes longues arrière), pieds 3 orteils + griffes courbes, mode clay contrasté.

## À faire
- Feedback utilisateur sur clay v3 (silhouette tête validée en gros plan, à confirmer).
- Améliorations géométrie candidates : cou/épaules plus musclés (le raccord tête-cou est fin), membrane d'ailes avec doigts plus marqués, langue, commissures de gueule, écailles GÉOMÉTRIQUES (displacement) plus tard.
- Après validation géométrie : réactiver look (matériaux/lumières) progressivement.

## Prochaines actions
1. Feedback → petites éditions spec/organic inline (pas d'agents), --fast --clay, re-stop.
