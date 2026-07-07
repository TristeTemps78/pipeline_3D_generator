# Pipeline 3D — Claude + Blender (bpy headless)

## État actuel
Boucle 2 terminée (tête refaite + look feu doré), rendu HQ = renders/step_018.png. **EN ATTENTE DE FEEDBACK UTILISATEUR.**

## Architecture (stable)
- `pipeline/bx/` : abstraction Blender (core/ops/organic/materials). Builders spec-driven : ground, spine (crête double rangée), head (crâne allongé, gueule ouverte `gape`, dents, couronne de cornes GVL), wing, limb.
- `pipeline/gvl/` : lois (spirale log, allométrie, caténaire, phyllotaxie, decay, L-système) + `vocabulary.json` (clés growth.* / pattern.*).
- `specs/dragon_got.json` : source de vérité — éditer la spec, pas le code.
- Commande : `python3 pipeline/run.py forge specs/dragon_got.json [--fast]` (~10 s fast, ~2 min HQ).
- Protocole : `pipeline/orchestrator.md`. Agents : `.claude/agents/` (ref-analyst, shape-smith, look-dev, render-critic). État : `pipeline/state/session.json`.
- Env : `pip install bpy` (5.0.1), Cycles CPU. Piège connu : coords Generated inutilisables sur curves → shaders en coords Object.

## Réalisé
- v1 blockout validé (proportions+pose). Feedback consigné : tout le reste à refaire détaillé, cible photo Drogon S7.
- Boucle 2 déléguée : shape-smith (tête prédateur : gueule 32°, dents, 5 paires de cornes, crête double jitter, cou retendu) ; look-dev (écailles 2×voronoi arêtes cuivre, brume volumétrique dorée, lumières feu, sol cendré).
- Orchestrateur : sol 300 m (bande horizon), cuivre atténué, lumières feu relevées, lens 40.

## À faire
- Feedback utilisateur boucle 2 → boucle 3.
- Pistes réalisme restantes : displacement réel (adaptive subdiv), variation d'échelle des écailles par zone (ventre/dos), fumée/braises, second plan champ de bataille, griffes ailes plus lisibles, gape ajustable si trop béant.
- Généralisation : 2e créature test + agent ref-analyst sur image.

## Prochaines actions
1. Lire feedback → répartir shape-smith / look-dev.
2. Itérer --fast (≤3), rendu HQ, re-stop feedback.
