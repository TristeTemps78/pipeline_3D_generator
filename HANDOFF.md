# HANDOFF — à lire EN PREMIER à la prochaine session

L'utilisateur va COLLER sa réponse au prompt ci-dessous. La traiter comme la décision
d'orientation de la boucle 10, puis reprendre le protocole (`pipeline/orchestrator.md`).

## Directives permanentes (rappel, détail dans claude.md)
Économie de tokens maximale · orchestrateur qui DÉLÈGUE aux agents SONNET (contrat chiffré,
≤3 itérations) · généricité (tout passe par la spec JSON) · dossier compact (audit.sh, purge) ·
toujours 2 blends : renders/scene.blend + scene_prev.blend.

## Backlog boucle 10 (feedback utilisateur step_088, non traité)
1. **Ailes BEAUCOUP plus grandes** : pas un tronc — volume type « planche à voile »
   (surface/épaisseur/lattes), builder `wing` à repenser.
2. **Pose de VOL** au lieu de posé sur 2 jambes (spine cambrée, pattes repliées,
   ailes déployées, sol lointain/absent).
3. Tête : itérer selon la réponse au prompt + le feedback sur step_091/092.

## Prompt posé à l'utilisateur (fin de boucle 9)
> **What's the issue we are running into?**
> We are building a generic text→3D pipeline (Python + Blender only, JSON spec as the
> single source of truth). The dragon head has gone through 3 feedback loops and still
> reads "assembled from parts" instead of sculpted.
>
> **What works:** spec-driven procedural body (lofts, blobs, booleans, GVL laws) ; the
> measured loop (edge-density/color metrics vs reference) ; scale armor as live instances
> (19.5k plates, ~0 memory cost, per-instance micro variation) ; cheap-token orchestration
> with Sonnet agents ; SDF geometry nodes validated headless (T10) but NOT wired yet.
>
> **What doesn't work:** fine organic anatomy. Eyes/lips/brow/cheeks are separate blobs and
> tubes laid onto a lofted skull — they stay lumpy, seams show, and the dense scale armor
> visually buries them. Edge-density plateaus at 0.195 vs 0.33 on the reference. Every
> visual iteration costs tokens, so brute-force retries converge too slowly.
>
> **What we need to solve:** ONE smooth, continuous, sculpted head surface where brow
> ridge, eye sockets, lips, cheeks and horn bases flow into each other (like a sculpt),
> while keeping everything parametric/generic in the JSON spec.
>
> **How can we solve this/these issues?** Options on the table: (A) wire the validated SDF
> layer — fuse skull + all face features via SDF union + fillet into one watertight sculpted
> mesh, then re-skin with armor masked by curvature ; (B) true displacement on hero zones
> (adaptive subdiv, test T13) for skin folds/wrinkles ; (C) code-driven "sculpt brushes"
> (crease/inflate along curves) on the fused mesh ; (D) another approach you prefer.
> Which direction do we take (one or a combo), and do you have reference constraints
> (budget, level of realism, timeline) that should drive the choice?
>
> **And: your feedback on the latest model** (renders/step_091.png compare, step_092.png
> full scene, renders/scene.blend openable locally) — what's good/bad on eyes, teeth/chin,
> mouth, face relief?

## Reprise technique (conteneur neuf)
`bash pipeline/bootstrap.sh` → lire claude.md → traiter la réponse collée → boucle 10.
Branche : claude/* la plus avancée (fetch --prune), miroiter après push.
