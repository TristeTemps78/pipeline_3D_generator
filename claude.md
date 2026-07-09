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

## État courant
JAMAIS ici : tout l'état (boucle en cours, dernier feedback, contrat, restes) vit dans
`HANDOFF.md` — seul fichier à lire après celui-ci. Backlog long terme : `NEXT.md`
(à lire seulement au cadrage d'une boucle). Protocole : `pipeline/orchestrator.md`.
Cible visuelle : `references/drogon_*.png`.
PIÈGES appris : armure = Separate Components sinon OOM ; Object Info ORIGINAL ignore le
transform objet ; couronne : angle X POSITIF = bascule arrière ; transmission sur coque
fine + lumières fortes = taches blanches transmises (mettre 0 ou masquer) ; _axis_factor
(masks/grads armure) travaille en coordonnées locales == monde seulement si l'objet est
à l'origine ; détail tête : plaques trop grosses/soulevées = « gravier » qui noie la
sculpture (scale ~.02-.05 à l'échelle d'un crâne de 2u).

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
Toutes les branches `claude/*` = UNE lignée : `git fetch --prune`, travailler sur la plus
avancée (celle de la session), miroiter la pointe sur les autres après push (fast-forward
seulement). Commit par étape de boucle, push + état AVANT fin de session (conteneur éphémère).
