# Pipeline 3D — Claude + Blender (bpy headless)

## État actuel
v1 blockout dragon GoT rendu (renders/step_006.png). **EN ATTENTE DE FEEDBACK UTILISATEUR.**

## Architecture (stable)
- `pipeline/bx/` : abstraction Blender AI-friendly (core/ops/organic/materials). Verbes : tube, blob, spike, grid_surface, + builders spec-driven (spine, head, wing, limb, ground).
- `pipeline/gvl/` : Growth Vocabulary Library. `laws.py` (spirale log, allométrie, caténaire, phyllotaxie, L-système) + `vocabulary.json` (clés compactes terme→loi).
- `specs/*.json` : source de vérité d'une créature (parties + matériaux + scène). Éditer la spec, pas le code.
- Commande : `python3 pipeline/run.py forge specs/dragon_got.json [--fast]` → renders/step_NNN.png + scene.blend.
- État session : `pipeline/state/session.json`. Protocole : `pipeline/orchestrator.md`. Agents : `.claude/agents/`.
- Env : `pip install bpy` (5.0.1), rendu Cycles CPU, ~5 s en --fast, ~1-2 min en HQ.

## Réalisé
- Pipeline complet spec→build→render fonctionnel ; 5 itérations internes (caméra frontale 3/4, ailes déployées, cornes spirale log, crête dorsale, yeux émissifs, shaders écailles voronoi/membrane/roche).

## À faire
- Intégrer feedback utilisateur sur v1.
- Réalisme : subdivisions+displacement réel des écailles, cou moins « cygne », tête plus anguleuse, muscles (blobs), texture sol, brume/atmosphère.
- Généraliser : 2e spec de créature pour valider le côté généraliste ; analyse d'image de référence → spec (agent ref-analyst).

## Prochaines actions
1. Lire feedback → traduire en éditions de spec (déléguer shape-smith / look-dev).
2. Re-render --fast pour valider, puis HQ, puis re-stop feedback.
