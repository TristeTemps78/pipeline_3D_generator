# AGENTS.md — pipeline_3D_generator

> **Ce fichier est un pointeur.** La source de vérité vit dans `CLAUDE.md` (directives
> permanentes, budget de lecture, pièges appris) — **ne pas la dupliquer ni la contredire ici.**

Pipeline « sculpteur » : modèles 3D premium via Blender headless (bpy), gratuit/illimité.

## Par où commencer (ordre imposé, budget de lecture serré)
1. **`CLAUDE.md`** — directives permanentes + carte du projet. À lire en premier.
2. **`HANDOFF.md`** — **fichier d'état** : boucle en cours, dernier feedback, contrat, restes.
   C'est le seul autre fichier à lire au boot. **Sert aussi de registre de coordination.**
3. `NEXT.md` — backlog long terme (au cadrage d'une boucle seulement).
4. `pipeline/orchestrator.md` — protocole d'orchestration (délègue à des agents Sonnet).

## Protocole multi-agents (obligatoire)
- **Réservation via `HANDOFF.md`** (pas de TASKS.md ici) : y noter `🔒 in-progress — @<agent>`
  sur la boucle/tâche en cours **et committer avant d'écrire**. Voir `../WORKFLOW.md`.
- Ne jamais forcer un verrou posé par un autre agent.
- Concurrence sur ce repo → `git worktree` + branche `agent/<agent>/<tâche>`.
- Respecter le budget de lecture de `CLAUDE.md` (gros fichiers : Grep ciblé, jamais Read complet).

## Contraintes dures
- `model: sonnet` imposé dans le frontmatter de `.claude/agents/*.md` (économie) — vérifier qu'il y reste.
- Purger `renders/` sauf jalons référencés ; garder les 2 derniers `.blend` ouvrables.
- Rendu HQ = long → une seule fois en fin de boucle (une pause >5 min casse le cache de prompt).

## Fin de session
Mettre à jour `HANDOFF.md` (état + restes), committer, pousser.
