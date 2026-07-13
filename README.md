# pipeline_3D_generator

Pipeline Claude + Blender (bpy headless, aucun outil externe) : référence (texte/image/vidéo)
→ spec JSON compacte → scène 3D procédurale → rendu Cycles → critique → feedback utilisateur.
Logique inspirée de BlenderFusion : décomposition object-centric, spec 3D groundée, boucle edit→render.

## Démarrage
```bash
pip install bpy                                        # Blender 5.x headless
python3 pipeline/run.py forge specs/dragon_got.json    # HQ ; ajouter --fast pour itérer
```
Sorties : `renders/step_NNN.png` + `renders/scene.blend` (ouvrable dans Blender GUI).

## Carte du dépôt (rôle UNIQUE par fichier .md)
- `CLAUDE.md` — PERMANENT : but, directives, règles, pièges, commandes, modules (relu à chaque session, en 1er).
- `HANDOFF.md` — ÉTAT COURANT + contrat de la boucle suivante (relu à chaque session, en 2e — seul fichier d'état).
- `NEXT.md` — BACKLOG long terme (lu seulement au cadrage d'une boucle).
- `pipeline/orchestrator.md` — protocole d'orchestration et règles d'économie de tokens.
- `pipeline/state/session.json` — historique intégral des feedbacks utilisateur.
- `pipeline/bx/` — abstraction Blender AI-friendly (aucun bpy hors de ce dossier).
- `pipeline/gvl/` — Growth Vocabulary Library : lois de croissance + vocabulaire compact.
- `specs/` — une créature = un JSON (source de vérité éditable).
- `.claude/agents/` — ref-analyst, shape-smith, look-dev, render-critic.
