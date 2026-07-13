---
name: audit
description: Audit précis et ÉCONOME du projet, en une passe à budget fixe. Utiliser dès que l'utilisateur demande un audit, un état des lieux, « c'est trop compliqué », « vérifie que tout est propre » ou signale un coût anormal.
---

# /audit — état des lieux complet à budget fixe

Objectif : diagnostiquer TOUT le projet sans le ré-explorer à la main. L'audit outillé
existe déjà — l'exploiter, pas le refaire.

## Ordre STRICT (et rien d'autre)
1. `bash pipeline/check.sh` — compile tout le Python, vérifie la cohérence des specs
   (builders/lois GVL/shots/matériaux), poids du dépôt, renders non référencés, agents
   sans `model:`. C'est 90 % du diagnostic pour ~0 token.
2. `git log --oneline -5`, `git status --short`, `git branch -r` — état de la lignée
   (une seule lignée attendue, pointe miroitée sur `main`).
3. Cohérence docs : HANDOFF.md (état) ne doit pas contredire CLAUDE.md (règles) ni
   `pipeline/orchestrator.md` (protocole). Ces fichiers sont déjà courts — les survoler
   suffit ; signaler toute directive présente en double (une info = UN fichier).
4. Grep CIBLÉS uniquement pour confirmer une anomalie détectée aux étapes 1-3.

## Interdits (c'est ce qui coûte)
- Lancer un rendu ou lire une image.
- Lire `bx/organic.py`, `bx/materials.py` ou une spec EN ENTIER (Grep/offset seulement).
- Spawner des agents.
- Réécrire des fichiers « au passage » : l'audit CONSTATE ; ne corriger que sur demande
  explicite de l'utilisateur (ou si le rapport est suivi d'un « corrige »).

## Livrable
Rapport court, classé par impact décroissant. Par anomalie : QUOI (1 phrase),
PREUVE (sortie de commande ou fichier:ligne), CORRECTIF proposé (1 phrase).
Terminer par : poids dépôt/.git, nb de renders versionnés, verdict global en 1 ligne.
Si tout est propre : le dire en 3 lignes, ne pas inventer des problèmes.
