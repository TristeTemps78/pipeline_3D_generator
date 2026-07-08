# Pipeline 3D — Claude + Blender (bpy headless)

## But & directives permanentes (utilisateur, 2026-07-08)
- BUT : pipeline GÉNÉRIQUE phrase/texte/vidéo → modèle 3D précis et complexe, Python+Blender
  seulement. Le dragon = banc d'essai (important en soi) ; toute mécanique nouvelle doit rester
  pilotée par la spec JSON, jamais du code spécifique dragon.
- ÉCONOMIE : l'orchestrateur délègue le gros du travail à des agents SONNET (`model: sonnet`) ;
  auto-audit régulier via `bash pipeline/audit.sh` (poids, nb fichiers, LOC) — direction claire,
  pas de boucles/hallucinations/tokens déraisonnables.
- COMPACITÉ : dossier léger — purger les renders sauf jalons référencés, logs compacts,
  claude.md court. Conseil clone local léger : `git clone --depth 1`.
- BLENDS : toujours garder les 2 derniers modèles ouvrables (`renders/scene.blend` +
  `renders/scene_prev.blend`, rotation auto dans run.py) pour le Blender local de l'utilisateur.

## État
Boucle 9 close (HQ **step_091** compare + **step_092** scène) : tête v3 — yeux enchâssés
(bourrelet sous-œil + crête sourcilière œil→cornes), dents réduites/menton massif, lèvres,
reliefs visage (mécanismes génériques head.ridges/face_blobs). Bords 0.195 (plafond des
primitives : suite = SDF/displacement, cf. HANDOFF.md). **ATTENTE : réponse au prompt
HANDOFF.md + feedback step_091/092.** Boucle 10 : ailes « planche à voile » + pose de VOL
(backlog HANDOFF). Cible : `references/drogon_*.png`. Protocole : `pipeline/orchestrator.md`.
PIÈGES : armure = Separate Components sinon OOM ; Object Info ORIGINAL ignore le transform
objet ; couronne : angle X POSITIF = bascule arrière.

## Métriques (normalisées h=512 — `run.py compare`)
Cibles réf : couleur moy (0.33,0.27,0.26) · cuivre 0.42 · bords 0.36. La PRIORITÉ utilisateur est la densité de détail (bords), pas la couleur.

## Règles
- Spec = source de vérité (`specs/dragon_got.json`). Jamais de bpy brut hors `pipeline/bx/`.
- Géométrie d'abord (clay), look ensuite. Chaque pas jugé par métrique + œil ; pas non améliorant → annulé.
- Écailles = GÉOMÉTRIE plaquée/imbriquée (`detail.armor` : mask, scale_grad, distance_min≈0.4-0.6×plaque), pas du bruit. Blobs quasi sphériques pour chair pendante = interdit (rend en œufs) : aplatir (ratio ≤0.5/2.7/0.8).
- La tête suit la fin de spine (continuité, pas de couture) ; ancres absolues (dewlap, masks, ailes) à recaler après tout déplacement de spine.
- Éditions par petits patchs ; --fast pour itérer, HQ pour présenter ; claude.md court.

## Cmds
`bash pipeline/bootstrap.sh` (conteneur neuf) puis `python3 pipeline/run.py` :
`forge <spec> [--fast|--clay|--sheet]` · `clayhero <spec> [--fast]` (géométrie, cadrage macro) · `compare <spec> <ref.png> [--fast]` (réf|rendu + deltas) · `validate <spec>` (BVH sans rendu) · `sheet <spec>`.

## Modules bx
core (clay, rim_setup, camera, realize_to_mesh) · ops (tube, blob, spike, grid_surface, ring_loft, boolean_diff) · organic (builders spine/head lofts superellipse/wing/limb/dewlap/armure via `_apply_armor`) · detail (keeled_scale, armor_scales, displace_layers, scales) · fuse (voxel_fuse défaut) · validate (BVH) · feedback (compare_sheet, contact_sheet, iou) · materials (reptile_scales SSS ; ignorés en clay). GVL : `pipeline/gvl/` (lois + vocabulary.json).

## Git
Lignée de travail : `claude/project-orchestration-dslej5` (miroir sur `claude/project-orchestration-pipeline-p5ap88` après push, cf. orchestrator.md — une seule session écrit à la fois). Commit par étape de boucle, push + état AVANT fin de session (conteneur éphémère).
