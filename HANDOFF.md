# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → CLAUDE.md, backlog → NEXT.md)

Reprise : CLAUDE.md → ce fichier, puis si l'utilisateur dit « continue », exécuter le
contrat ci-dessous sans reposer de question. EXÉCUTION 100 % LOCALE (Windows) :
`bash pipeline/blender_run.sh <cmd> <spec> [flags]` (Blender installé, bpy embarqué,
part ~4 s, silh ~15 s) — wheel bpy pip impossible (ARM64/Py3.14) ; conteneur
Linux = `bootstrap.sh` puis `python3 pipeline/run.py` comme avant. Python local (hors
bpy) : numpy+PIL dispo, ImageMagick dispo.

## BOUCLE 27 (2026-07-22) — WYVERNE ORIGINALE (essai demandé par l'utilisateur)

Demande : « fais TON dragon, pas de modèle, réaliste, un truc impressionnant qui fait
peur ». Choix arrêtés avec lui : **wyverne** (2 pattes, ailes = bras → crédible),
registre **prédateur sec et nerveux**, pose **à l'affût tête basse**.
**Krokmou n'est pas touché** (spec, réfs et score séparés).

Fichiers : `references/wyvern_ref.md` (cible visuelle + les leviers de peur, levier par
levier), `research/tests/gen_wyvern_trace.py` (**LE document de design** : stations BODY
+ chaîne LEG → `references/wyvern_ortho_side.png`), `gen_wyvern_cage.py` (→ **ÉCRASE**
`specs/wyvern.json`), `gen_wyvern_parts.py` (fusionne les 45 appendices, idempotent).
Ordre obligatoire : trace → cage → parts. **IoU silhouette 0.9424.**

Acquis GÉNÉRIQUES (réutilisables ailleurs, c'est le vrai gain de la boucle) :
- La référence est NOTRE dessin → committable → le score de silhouette tourne enfin en
  conteneur/CI, impossible avec Krokmou (réfs © locales).
- `run.py` : état du score **par spec** (`silh_<spec>.json`) — deux créatures en
  parallèle s'écrasaient le `delta`, qui est le signal de la boucle.
- `research/tests/xor_report.py` **committé** (il était refait à la main chaque session).
- `tube_along(miter=True)` dans `gen_appendages.py` : une section perpendiculaire à la
  bissectrice est trop étroite de cos(angle/2) → le dehors d'un coude se creuse (+0.0081).
- Compensation du subsurf en **LOI** `A + B/taille` au lieu de constantes : le
  Catmull-Clark ronge d'autant plus que la section est petite (+0.0100 ; c'est ce qui
  rattrape tête et cou, systématiquement trop maigres à 1.06).
- `web()` (dans gen_wyvern_parts) : membrane en **grille** paramétrique (feston radial +
  affaissement) — candidat nº1 à l'extraction vers `bx/`.

PIÈGES PAYÉS (ne pas redécouvrir) :
- `reptile_scales.scale` = **cellules par unité MONDE**, pas un nombre d'écailles. À 28
  puis 62 les plaques faisaient 3.5 puis 1.6 cm : invisibles → « plastique chocolat »
  pendant 3 rounds. À 14 elles se lisent, et `bump` 0.55 ne donne RIEN — il faut ~1.35.
- Membrane en polygones plats = origami, quel que soit le contour : il faut de la
  courbure DANS le panneau, et une normale d'affaissement COMMUNE (sinon accordéon).
- Le gradient de bord du builder `membrane` éclaircit vers le contour : sur de petits
  panneaux TOUT est bord → membrane rose pâle, élément le plus clair de l'image.
- Lèvre posée à fraction constante de la hauteur du crâne = **un sourire** (le crâne se
  creuse vers l'arrière) : définir la bouche par une altitude explicite qui descend.
- Crocs posés à la ligne de lèvre, pointés vers le bas = entièrement noyés (le crâne est
  une peau fermée, pas de bouche ouverte) : gueule close → les sortir latéralement.
- Arcade sourcilière en `spike` aplati = plaque hexagonale collée ; un tube à demi
  enfoui le long de l'orbite fait une vraie crête osseuse.
- Sans SOL, la bête flotte : plus d'échelle, plus d'ombre portée → ça lit « figurine ».
- Grossir un tube uniformément quand l'IoU manque à une extrémité est FAUX (−0.0087) :
  ce sont les **capuchons** qui rentrent sous subsurf → prolonger la chaîne et les enfouir
  (+0.0283).

RESTE : ailes encore un peu anguleuses (grille plus dense ou bord de fuite courbe) ;
pattes NON soudées au corps (la machinerie `gen_body_weld.py` est là, non appliquée) ;
tête lisse au close-up (écailles de crâne, plis) ; pas de selle/décor.

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
Rendus jalon b25 purgés (superseded b26) — ils restent dans l'historique git.

## Boucle 26 (2026-07-21) — AILES, AILERONS, SOUDURE DES PATTES + audit + hook

Rendus jalon : `renders/step_509_full.png` (hero), `renders/step_510_head_side.png`
(tête de profil), `renders/step_502.png` (planche clay 6 vues, montre la soudure).
Blend : `renders/scene.blend`. **IoU silhouette 0.8977** (0.9090 avant la soudure).

FAIT :
- `research/tests/gen_appendages.py` — 2 briques génériques : `plate()` (polygone 3D
  fermé → plaque étanche, normale de Newell) et `tube_along()` (polyligne → tube fermé).
- AILES : membrane `plate` subsurf 0 + bras + 2 doigts (`tube_along`), miroir X, ±18° de
  balayage et dièdre pour que les DEUX ailes lisent au 3/4. AILERONS caudaux : gauche
  noir, droit = **prothèse rouge brique** (materiau `membrane`, transmission 0).
- NUBS mâchoire/menton (`spike` + `skin_matte`).
- SOUDURE des 4 pattes dans la cage : `research/tests/gen_body_weld.py` — miroir cuit,
  **Catmull-Clark EXACT** ×1 (conserve la surface limite ; CC×1 + subsurf 1 == subsurf 2
  sur la cage grossière), perçage de 2 quads voisins sous le ventre, pontage du trou
  hexagonal sur l'anneau de GENOU (hanche jetée). Corps + pattes = UNE peau, sans
  booléen. `body_cage` = 722 verts, `mirror_x: false`, subsurf 1 (les 4 parts `leg_*`
  ont disparu de la spec).
- MÉTRIQUE : `scene.silh.exclude_like` (+ `feedback.silhouette`) masque ailes/ailerons
  pendant le rendu ortho (la réf est un décalque CORPS SEUL) ; `scene.silh.target` figé.
- HOOK git : `.push-test` = `bash pipeline/check.sh` → le pre-push refuse tout push non
  vert (le kit de hooks ne détectait aucun test). `check.sh` ajouté aussi à la CI.
- AUDIT complet : voir corrections dans NEXT.md (item 9 périmé : `.git` fait 42 Mo, pas
  400), `docs/ARCHITECTURE.md` (b25+b26), `orchestrator.md` (dédoublonné avec CLAUDE.md).

PIÈGES PAYÉS CETTE BOUCLE (ne pas redécouvrir) :
- Plaque fine → **subsurf 0** : le Catmull-Clark rogne le contour et avale les festons
  d'une membrane (les doigts dépassaient de l'aile).
- Un creux de membrane ne peut pas être plus profond que la corde poignet→pointe
  suivante, sinon le doigt (segment droit) sort de la membrane.
- Raffiner une cage par subdivision LINÉAIRE la gonfle vers son polygone de contrôle
  (IoU −0.02 avant même de souder) : utiliser Catmull-Clark exact.
- Trou d'attache trop GROS (2 quads de la cage grossière) → la cuisse rend en JUPE qui
  comble le vide sous le ventre (IoU −0.08). Percer après raffinement.
- Reculer la patte avant lointaine par cisaillement crée une cuisse diagonale qui bouche
  le vide poitrail/patte (IoU −0.09) : la réf a bien cette patte avancée (tête basse).
- Épaissir les pattes soudées (×1.18) n'aide pas (−0.005) : ce n'est pas l'épaisseur.

RESTE (ordre de visibilité) : la soudure coûte 0.011 d'IoU (le ventre descend plus bas
que la réf entre les pattes) — récupérable en remontant la ligne de ventre entre les
attaches ; base d'`ear_plate` encore « plaque collée » en HQ (même méthode de soudure
applicable) ; `validate` signale 30 tris auto-intersectés dans `body_cage` (cuisses qui
frôlent le ventre, sans effet visible) ; emblème blanc de la prothèse (décalque/texture,
mécanisme absent) ; selle/sangles ; vue face à l'œil (pas de réf ortho face).

## Restes hors contrat (reportés, ne pas redécouvrir)

Pari 30 min (fond de boucle, jamais bloquant) : TripoSR (MIT) sur CPU local — wheels
PyTorch Windows ARM64 existent ; comparer son ébauche à la cage. Œil : lisibilité iris —
à rejuger sur la nouvelle surface. Backlog : emblème blanc prothèse + selle/sangles ;
catchlight. `scene.blend` s'ouvre sur la caméra du dernier shot ; copper_fraction non
pertinent (palette noire). Drogon archivé : `specs/dragon_got.json` + maps +
`renders/drogon_step297.blend`. Ancien pipeline primitives : checkpoint `48963ba`.
