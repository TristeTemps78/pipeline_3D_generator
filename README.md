# pipeline_3D_generator

Pipeline Claude + Blender (bpy headless, aucun outil externe) : référence (texte/image/vidéo)
→ spec JSON compacte → scène 3D procédurale → rendu Cycles → critique → feedback utilisateur.
Créature en cours : **Krokmou** (`specs/krokmou.json`) ; Drogon archivé (`specs/dragon_got.json`).

## Démarrage
```bash
bash pipeline/bootstrap.sh                            # installe bpy si absent (idempotent)
bash pipeline/check.sh                                # QA statique ~5 s (compile+specs+audit)
python3 pipeline/run.py --help                        # toutes les commandes
python3 pipeline/run.py part specs/krokmou.json head --fast   # UNE pièce, ~20-30 s
python3 pipeline/run.py forge specs/krokmou.json --fast       # toute la bête
```
Sorties : `renders/step_NNN*.png` + `renders/scene.blend` (ouvrable dans Blender GUI).
**Comment lire ce projet : `docs/ARCHITECTURE.md` (la carte pédagogique, 5 étages).**

## Carte du dépôt (rôle UNIQUE par fichier .md)
- `CLAUDE.md` — PERMANENT : but, directives, règles, pièges (auto-chargé à chaque session).
- `HANDOFF.md` — ÉTAT COURANT + contrat de la boucle suivante (relu en 2e — seul fichier d'état).
- `NEXT.md` — BACKLOG long terme (lu seulement au cadrage d'une boucle).
- `docs/ARCHITECTURE.md` — carte de lecture du code (pour l'utilisateur).
- `pipeline/orchestrator.md` — protocole de la boucle GROUND→BUILD→LOOK→CRITIQUE→FEEDBACK.
- `pipeline/state/session.json` — historique intégral des feedbacks utilisateur.
- `pipeline/bx/` — abstraction Blender AI-friendly (aucun bpy hors de ce dossier).
- `pipeline/gvl/` — Growth Vocabulary Library : lois de croissance + vocabulaire compact.
- `specs/` — une créature = un JSON (source de vérité éditable).
- `references/` + `maps/` — cibles visuelles et maps bakées (archives Drogon incluses).
- `research/` — archives : doctrine, bancs d'essai bpy (`research/tests/`), audits de boucles.
- `.claude/agents/` — ref-analyst, shape-smith, look-dev, render-critic (tous `model: sonnet`).
