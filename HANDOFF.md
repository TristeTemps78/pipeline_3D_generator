# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → CLAUDE.md, backlog → NEXT.md)

Reprise : CLAUDE.md → ce fichier, puis si l'utilisateur dit « continue », exécuter le
contrat ci-dessous sans reposer de question. EXÉCUTION 100 % LOCALE (Windows) :
`bash pipeline/blender_run.sh <cmd> <spec> [flags]` (Blender installé, bpy embarqué,
part ~4 s, silh ~15 s) — wheel bpy pip impossible (ARM64/Py3.14) ; conteneur
Linux = `bootstrap.sh` puis `python3 pipeline/run.py` comme avant. Python local (hors
bpy) : numpy+PIL dispo, ImageMagick dispo.

## Où on en est — BOUCLE 24 « SCULPTEUR v1 » : JALON ATTEINT (2026-07-19)

Le test « le plafond a-t-il sauté » est POSITIF : **IoU silhouette 0.9031** (cage v8)
contre 0.3602 pour le modèle b23 — en 8 itérations de cage, une session.

P0-A RÉFÉRENCES : fait (2026-07-16), voir `references/krokmou_ref.md`. PNG LOCAUX et
GITIGNORÉS (© DreamWorks) → `silh` et le décalque ne marchent qu'en session locale.
P0-B MÉTRIQUE : ✅ FAIT (2026-07-19, commit `6b1f380`).
- Décalque corps-seul FIGÉ : `references/krokmou_silh_trace.txt` (PTS_V4 + méthode +
  régénération du masque). Pièges levés : le v2 était faux (tête décalée ~40 px — museau
  réel x=62, tête PLUS BASSE que les épaules, pose à l'affût) ; la queue PLONGE (crête
  dorsale mince jusqu'à x≈337 + corps de queue bas y≈285-300, séparés par du FOND PUR
  vérifié pixel) ; 4 pattes visibles (la réf n'est PAS une vraie ortho : pattes
  lointaines décalées en Y → pose de marche) ; dos x 208-250 INTERPOLÉ sous l'aile.
- `run.py silh <spec>` : clay → `feedback.silhouette` ortho side → IoU vs masque
  corps-seul, `keep_aspect=True` (ajout dans `feedback.iou/_bbox_normalize`, fit+padding
  centré — l'étirement carré effaçait les erreurs de proportions), orientation levée par
  max(raw, fliplr), delta persisté `pipeline/state/silh.json`, planche réf|rendu|XOR
  `renders/silh.png`.
P0-C CAGE : ✅ JALON ATTEINT.
- `core.mirror` (clip+merge, à appeler AVANT subsurf) + builder `cage` dans organic.py
  (verts/faces de la spec, mirror_x, normales recalc, subsurf paramétrable — `subsurf: 0`
  utile pour les petites plaques que le subsurf écraserait).
- `specs/krokmou_cage.json` = spec de DEV cage (SOURCE DE VÉRITÉ, à éditer à la main
  désormais) : body_cage 100 verts (19 stations × anneaux 5 pts moitié +X), 4 pattes
  individuelles (tubes 6 pts, pose de marche), oreilles + tail_ridge (plaques subsurf 0).
  Amorçage archivé `research/tests/gen_krokmou_cage.py` (ATTENTION : le relancer ÉCRASE
  la spec). Blend jalon : `renders/scene.blend` (clay), planche 4 vues `renders/step_468.png`.
- validate : 0 non étanche, 0 collision. Baseline vs jalon dans `pipeline/state/silh.json`.

## Leçons de la boucle interne (à réutiliser)

- L'analyse NUMÉRIQUE des poches XOR (composantes connexes MANQUE/EXCÈS + bbox, script
  local `xor_report.py` refaisable en ~40 l. numpy sur renders/silh.png) guide 10× mieux
  que l'œil sur la vignette — chaque passe guidée a gagné +0.013 à +0.017.
- Compensation du rétrécissement subsurf : corps ×1.06, tubes de pattes 6 pts ×1.2 (le
  subsurf mange bien plus les petites sections) ; plaques fines → subsurf 0.
- Changement non améliorant → REVERT immédiat (une baisse de -0.015 attrapée ainsi) ;
  changer UN groupe de choses à la fois pour pouvoir attribuer.

## Contrat boucle 25 (proposition, à confirmer par l'utilisateur)

P1 INTÉGRATION : souder pattes/oreilles à la peau du corps (extrusions dans la MÊME cage
ou weld à la construction — PAS de boolean), puis ailes + ailerons caudaux (grandes
plaques cage membraneuses). Ensuite : vue face (pas de réf ortho face — juger à l'œil
+ planche), tête détaillée (yeux/mâchoire dans la cage), et seulement après → look
(matériaux noirs satinés, yeux verts) sur la nouvelle surface.
Règles inchangées : itérer local avec silh + XOR, check.sh vert avant commit, montrer
uniquement les jalons, HQ une fois en fin.

## Restes hors contrat (reportés, ne pas redécouvrir)

Pari 30 min (fond de boucle, jamais bloquant) : TripoSR (MIT) sur CPU local — wheels
PyTorch Windows ARM64 existent ; comparer son ébauche à la cage. Œil : lisibilité iris —
à rejuger sur la nouvelle surface. Backlog : emblème blanc prothèse + selle/sangles ;
catchlight. `scene.blend` s'ouvre sur la caméra du dernier shot ; copper_fraction non
pertinent (palette noire). Drogon archivé : `specs/dragon_got.json` + maps +
`renders/drogon_step297.blend`. Ancien pipeline primitives : checkpoint `48963ba`.
