# Pipeline 3D — Claude + Blender (bpy headless)

## État
Boucle 6 close (rendu HQ **step_073**) : arche du cou + mandibule agrandie + couverture d'écailles corps entier (35k instances, `detail.armor` ×6 entrées + `displace_targets` rides) — bords 0.09→0.19, cuivre 0.42 ✓. **ATTENTE FEEDBACK**, candidats boucle 7 : `NEXT.md`. Cible : `references/drogon_*.png`. Feedback : `pipeline/state/session.json`. Protocole : `pipeline/orchestrator.md`. NB : --fast sous-mesure edge_density (~0.16 fast vs 0.19 HQ, juger la tendance pas l'absolu).

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
Branche unique : `claude/project-orchestration-pipeline-p5ap88` (les 2 autres branches claude/* sont à supprimer côté GitHub UI, deletes 403 en session). Commit par étape de boucle, push + état AVANT fin de session (conteneur éphémère).
