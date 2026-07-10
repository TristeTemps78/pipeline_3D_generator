# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → claude.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → claude.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Boucle 15 close (SANS rendu HQ, à la demande), **EN ATTENTE DE FEEDBACK** sur les shots
fast **step_172_hero/head/legs** (+ clay tête step_168, hero post-volume step_161).
Feedback step_160 intégral dans session.json (critique visuelle + « 2h → minutes »).
Fait en boucle 15 (tout générique, défauts rétro-compatibles) :
- PERF : `scene.render` (device AUTO GPU→CPU, samples/denoise/adaptive/bounces/clamp/
  res_scale/fast_sss Burley) câblé au rendu final ; brume VOLUMÉTRIQUE RETIRÉE = LE poste
  des 2h locales (HQ hero : >20 min → **38 s** ici, piège consigné dans claude.md) ;
  lumières 5→4 bornées size 6. Le rendu HQ local de l'utilisateur doit passer à ~1-3 min
  CPU, secondes avec GPU (AUTO le prend tout seul).
- TÊTE : lois `growth_rings`/`curl_offset` (laws+GVL), cornes annelées base fondue
  (`_apply_horn_growth`, `_kera_spike`, tube res paramétrable), dents variées
  (`rscale`, `fang_girth_*`), gencives+lèvre (ridges), charnière/couronne fondues
  (face_blobs aplatis). Tête 75.9k verts (-4 %).
- ÉCAILLES : `_axis_factor` accepte les axes NORMALE `nx/ny/nz` → `mask_radial`
  (ventre plaques larges lisses / dos carènes serrées / flancs mix) + `scale_noise`
  (patchs macro). Bords **0.233 → 0.3002** (cible réf .35) à qualité complète.
- MEMBRANE : 2e génération de nervures ramifiées (`vein_branches` etc., suivent
  sag/camber/billow) ; displace membrane subdiv 2. Scène 279k verts (plafond 400k).
- Bugs corrigés au passage : veines avalées par la fusion SDF (exclude_like),
  classification wing sans hand_/vein_ (PART_TYPE_HINTS).

## Contrat boucle 16 (à recadrer selon feedback sur step_172_*)
Candidats (NEXT item 0 restant + doutes agents) : (a) BAKE générique sculpt→normal/
displacement maps + textures image (2e étage perf demandé par l'utilisateur, gros
chantier) ; (b) œil/iris reptilien gros plan (jamais validé) ; (c) plis de peau aux
articulations `fold_rings` ; (d) environnement caverne/canyon détaillé + cicatrices ;
(e) câbler mask_radial/scale_noise sur hindleg, veines mat membrane vs bone à valider ;
(f) gum/lip ridges codés en dur → resynchroniser si les dents bougent (doute agent tête).

## Restes connus hors contrat
fuse_groups head/hindleg bloqué (NEXT 2, prérequis armure spatiale) ; scene.blend s'ouvre
sur la caméra du dernier shot ; `front_extent=0.5` de root_follow_arm en dur ; le compare
--fast sous-estime les bords (denoise lisse) — toujours juger la métrique en qualité pleine.
