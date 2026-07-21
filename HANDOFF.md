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

## Boucle 25 — « du visible d'abord » (recadrée par l'utilisateur 2026-07-19 : trop de
## tokens pour un blob gris → tête/yeux/look AVANT la soudure des membres)

FAIT (2026-07-19) : builder `globe` (blob de surface générique, look_dir = axe du regard,
mirror_x) ; yeux verts b23 (`materials.eye_globe`, copié dans la spec cage) + paupières
plaques posés sur la cage ; éclairage studio + `scene.shots` (full/head) copiés du spec
b23. Silhouette TENUE : IoU 0.9026. Leçon placement œil : itérer avec
`forge --fast --shot head` (~30 s), 3 passes ont suffi (enfoui → sorti/regard avant).

FAIT (2026-07-21) — TÊTE LISIBLE, **IoU 0.9089** (+0.0063, au-dessus du jalon b24) :
- Builder générique `spike` dans organic.py (enveloppe spec d'`ops.spike` : `pos`, `dir`,
  `tilt`, `height`, `radius`, `flatten`, `tip_frac`, `mirror_x`) — même primitive « plaque
  charnue » que les oreilles de `head_galet`, sans dupliquer de code.
- Oreilles : les 2 boîtes `cage` remplacées par `ear_plate` (spike aplati balayé arrière)
  + `ear_nub_hi/lo` (appendices sensoriels de la réf). Réglages qui marchent :
  `flatten [0.42,1.0]` (mince en X = face large visible de PROFIL, c'est la lecture
  Krokmou), `tip_frac 0.22`, `dir [0.28,0.78,0.48]` (~31° vers le haut : plus vertical
  = « cornes », plus couché = la plaque se fond dans le dos), height 0.62.
- `mouth_line` : décalque `cage` subsurf 0 généré par `research/tests/gen_mouth.py`
  (IMPRIME le JSON, n'écrit PAS la spec). Sur du noir la ligne se voit par l'OMBRE, pas
  par l'albédo → section en **lèvre en surplomb** (bord haut +0.020, bord bas -0.006,
  face interne -0.030), pas une corniche symétrique (round 1 : invisible + effet ledge).
  Station de tête SUR l'axe → pas de bouchon avant (2 ngons coïncidents = non manifold ;
  le mirror clip+merge referme). Matériau `skin_matte` (reptile_scales rough 0.72,
  spec_level 0.08) : contraste par la RUGOSITÉ.
- `nostril` : 2 `globe` aplatis (r [0.05,0.08,0.03]) mats sur le dessus du museau.
- Shot `head_side` ajouté (`frame_match mouth_`, lens 70) : la bouche NE SE JUGE PAS au 3/4.
- Repère mesuré (`run.py inspect`) : la surface lissée = cage/1.06 EXACTEMENT (bbox
  body_cage x_max 0.6363 = 0.653/1.06) ; museau lisse à y=-1.984 (cage -1.988).
Rendus HQ jalon : `renders/step_484_head_side.png`, `step_485_head.png`,
`step_486_full.png`, blend `renders/scene.blend`.

RESTE boucle 25+ (dans l'ordre de visibilité) : souder pattes/oreilles à la peau
(extrusions dans la cage ou weld — PAS de boolean ; la base d'`ear_plate` lit encore
« plaque collée » en HQ) ; ailes + ailerons caudaux (grandes plaques cage membraneuses) ;
nubs de mâchoire/menton de la réf ; vue face à l'œil (pas de réf ortho face). Règles
inchangées : itérer local silh + XOR + shots --fast, check.sh vert avant commit, montrer
uniquement les jalons, HQ une fois en fin.

## Restes hors contrat (reportés, ne pas redécouvrir)

Pari 30 min (fond de boucle, jamais bloquant) : TripoSR (MIT) sur CPU local — wheels
PyTorch Windows ARM64 existent ; comparer son ébauche à la cage. Œil : lisibilité iris —
à rejuger sur la nouvelle surface. Backlog : emblème blanc prothèse + selle/sangles ;
catchlight. `scene.blend` s'ouvre sur la caméra du dernier shot ; copper_fraction non
pertinent (palette noire). Drogon archivé : `specs/dragon_got.json` + maps +
`renders/drogon_step297.blend`. Ancien pipeline primitives : checkpoint `48963ba`.
