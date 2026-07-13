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
- SIMPLICITÉ/RAPIDITÉ (feedback 2026-07-13, mi-boucle 20 — l'utilisateur était PERDU) :
  boucles COURTES (1 round géométrie + 1 round look max avant de montrer), HQ et
  render-critic réservés à la présentation, réponses pédagogiques (il apprend).
  Carte de lecture du projet : `docs/ARCHITECTURE.md` (vue stacks) — à maintenir.
  Inspection pièce par pièce : `run.py part <spec> <id> --fast` (~20-30 s).

## État courant
JAMAIS ici : tout l'état (boucle en cours, dernier feedback, contrat, restes) vit dans
`HANDOFF.md` — seul fichier à lire après celui-ci. Backlog long terme : `NEXT.md`
(à lire seulement au cadrage d'une boucle). Protocole : `pipeline/orchestrator.md`.
Cible visuelle : `references/krokmou_ref.md` (Krokmou/Toothless, depuis boucle 20 ;
Drogon archivé : spec+maps+`renders/drogon_step297.blend`, réfs `references/drogon_*.png`).
PIÈGES appris : armure = Separate Components sinon OOM ; Object Info ORIGINAL ignore le
transform objet ; couronne : angle X POSITIF = bascule arrière ; transmission sur coque
fine + lumières fortes = taches blanches transmises (mettre 0 ou masquer) ; _axis_factor
(masks/grads armure) travaille en coordonnées locales == monde seulement si l'objet est
à l'origine ; détail tête : plaques trop grosses/soulevées = « gravier » qui noie la
sculpture (scale ~.02-.05 à l'échelle d'un crâne de 2u) ; VOLUME SCATTER mondial
(brume/poussière) = rendu ×30-100 sur CPU (2h chez l'utilisateur, >20 min HQ ici vs 38 s
sans) — atmosphère par dégradé+variation du fond, volume réservé GPU et jamais par défaut.

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
`forge <spec> [--fast|--clay|--sheet|--shot <id>]` (si `scene.shots` : 1 PNG par prise, cadrage auto par pièce) · `part <spec> <id> [--fast|--clay]` (UNE pièce isolée, cadrage auto, ~20-30 s — inspection rapide) · `bake <spec> [--fast]` (étage high→low : shell voxel temporaire+displacement → maps/ normal/AO/courbure, ~45 s) · `clayhero <spec> [--fast]` (géométrie, cadrage macro) · `compare <spec> <ref.png> [--fast]` (réf|rendu + deltas) · `validate <spec>` (BVH sans rendu) · `sheet <spec>`.

## Modules bx
core (clay, rim_setup, camera, world variation, render settings=`scene.render` perf GPU/samples/bounces, realize_to_mesh) · ops (tube res param, blob, spike, grid_surface, ring_loft, boolean_diff) · organic (spine/head cornes growth_rings/wing knuckle_spread+root_follow_arm+vein_branches/limb/dewlap/armure `_apply_armor`) · detail (armor_scales masks axiaux+`mask_radial` normales nx/ny/nz+`scale_noise`, keeled_scale, displace_layers) · fuse (voxel_fuse, sdf_fuse+fuse_groups — exclude_like À TENIR À JOUR pour tout nouveau motif d'objet) · validate (BVH) · feedback (compare_sheet, sheet4, part_bbox, iou) · materials (reptile_scales patine cavité + slots maps bakées normal/ao/curvature, membrane veines transmission≤.05, horn kératine ; ignorés en clay) · bake (shell high-poly temporaire, surface.layers scales/wrinkles/micro, UV auto, bake selected_to_active). GVL : `pipeline/gvl/` (lois growth_rings/curl_offset + vocabulary.json).

## Git
Toutes les branches `claude/*` = UNE lignée : `git fetch --prune`, travailler sur la plus
avancée (celle de la session), miroiter la pointe sur les autres après push (fast-forward
seulement). Commit par étape de boucle, push + état AVANT fin de session (conteneur éphémère).
