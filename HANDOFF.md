# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → claude.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → claude.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Boucle 19 CLOSE, **EN ATTENTE DE FEEDBACK** sur **step_297_hero/head/legs/eye/teeth/wing** (HQ).
Lignée A/B : step_182 → step_218 → step_231 → step_297.
PROCESS : render-critic DÉSORMAIS ACTIF (5 rounds cette boucle : 3 complets + 2 vérifications
ciblées) — verdict final PRÉSENTABLE avec restes assumés listés ci-dessous. Les rapports
distinguent « implémenté » de « lit à l'écran » (fautes F1/F2/F5 de l'audit traitées).

Fait en boucle 19 (audit → 3 chantiers Sonnet + 3 rounds look + fixes orchestrateur) :
- ANATOMIE (A) : loft `_anatomical_tube` (sections elliptiques, repère sans torsion) pour
  limb/wing si spec porte `muscles`/`joints`/`folds` — lois GVL fusiform/joint_bump/fold_indent.
  Cuisse+mollet+genou LISENT au shot legs (recadré exprès). Plis de peau : implémentés mais
  noyés dans le bruit de surface. Bras d'aile : atténué par la fusion SDF torse.
- CHAMPS ANATOMIQUES (B) : attribut `axis_uv` (u curviligne, v angle) écrit sur spine/limb/
  head, consommé par shaders (`reptile_scales axis_uv`) et armure (`layout:"rows"` quinconce,
  tailles par zone) ; arbre de veines hiérarchique depuis les doigts d'aile (vein_levels…),
  membrane mottle_* + vein_radial_* — veines lisibles en close-up, STYLISÉES au hero (reste).
- LISIBILITÉ (C) : dents courbées/jitter/tronquées par seed + gencive continue (matériau gum) ;
  cornes rings ×1.8 + tip_wear + stries axis_uv ; ŒIL — bug critique corrigé (globe sans
  rotation propre : iris aligné axes MONDE = invisible par construction) + fente nette,
  catchlight ; dewlap rééchantillonné ; shots vérification `eye`/`teeth`/`wing` + `frame_match`
  générique + `fill_lights` par shot (run.py).
- LOOK (3 rounds sur verdicts critic) : bug teinte `micro` (chaque écaille poussée cuivre) ;
  crâne/armor sur matériau `scales` générique — recette sombre propagée (tint .05/.02/.014,
  edge_copper .22, patina pointiness) ; gum() posait Coat Roughness .05 CODÉ EN DUR dès wet>0
  (tube caoutchouc insensible à wet — wet=0 désormais) ; exposition +, legs recadrée+éclairée.
- Scène ~327k verts, validate OK. Maps rebakées post-anatomie.

## Contrat prochaine boucle (À CADRER après feedback utilisateur)
Restes ASSUMÉS de boucle 19 (déjà connus, ne pas les redécouvrir) :
1. Veines membrane stylisées « craquelures » au hero, pas organiques (vein_radial_* à retravailler).
2. Grain écailles fin type bruit, 2 échelles peu distinctes — edge_density .19 vs cible .348 ;
   vraie voie = faire consommer `axis_uv` par bake.py (surface.layers) + rebake.
3. Pad de pied/toes pâle crème — attribut axis_uv ajouté sur footpad SANS effet (cause ailleurs,
   à déboguer : toes absents du registre groups → .001 dupliqués hors groupe ?).
4. Plis de peau (folds) ne lisent pas — porter par displace_targets plutôt que rayon.
5. Patte encore un peu plus chaude que le buste (R/B 1.29 vs corps) ; mâchoire inf. arrondie
   vs profil crocodilien réf ; ébréchage dents subtil à 640.
6. Anatomie bras d'aile mangée par fuse SDF (exclure l'avant-bras de la fusion ou voxel local).

## Restes connus hors contrat
copper_fraction peu fiable (rig compare à sa propre key quasi-blanche — juger luminance
p5/p50/p95, réf .082/.185/.715 ; rendu .049/.145/.652) ; compare --fast sous-estime les bords ;
~472 mesh non-manifold préexistants sans effet ; scene.blend s'ouvre sur la caméra du dernier
shot ; fuse_groups head/hindleg bloqué (cf. NEXT).
