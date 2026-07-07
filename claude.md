# Pipeline 3D — Claude + Blender (bpy headless)

## État actuel
Boucle 3 (géométrie-d'abord, mode clay) rendue : step_023 (corps) + step_022 (tête gros plan). **EN ATTENTE DE FEEDBACK UTILISATEUR.** Budget tokens serré : plus de sous-agents, itérations inline courtes.

## Architecture (stable)
- `pipeline/bx/` : core (dont `clay()` : validation géométrie, lumière uniforme, matériaux neutres), ops (tube, blob, spike, grid_surface, **ring_loft** = volumes par sections), organic (builders : ground, spine+crête, head lofté, wing, limb+orteils griffus), materials (ignorés en clay).
- `pipeline/gvl/` : lois (+ **superellipse** : sections crâniennes anguleuses) + vocabulary.json.
- Spec = source de vérité : `specs/dragon_got.json`. Cmd : `python3 pipeline/run.py forge <spec> [--fast] [--clay]`.
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
