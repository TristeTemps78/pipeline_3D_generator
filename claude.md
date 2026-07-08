# Pipeline 3D — Claude + Blender (bpy headless)

## État
Boucle 7 close (HQ **step_080** compare + **step_081** scène) : architecture détail câblée (T10-T14 testés, `research/logs/`) — archétypes par région + Pick Instance dithéré, instances VIVANTES (`realize:false`) + micro par écaille (`scale_seed` → `reptile_scales(micro)`), throttle Cycles ; tête refaite (mâchoire ++, gape 30, naseaux, 2 cornes maîtresses arrière, raccord cou par armure continue y≤3.5). Bords 0.182 / cuivre 0.404. **ATTENTE FEEDBACK utilisateur** ; suite dans `NEXT.md` (boucle 8 : densités ++, SDF macro, T13). Cible : `references/drogon_*.png`. Protocole : `pipeline/orchestrator.md`. NB : --fast sous-mesure edge_density (juger la tendance). PIÈGE : jamais 2+ entrées d'armure sans Separate Components (OOM écailles-sur-écailles, fixé dans `detail.py`).

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
