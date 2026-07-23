# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → CLAUDE.md, backlog → NEXT.md)

Reprise : CLAUDE.md → ce fichier, puis si l'utilisateur dit « continue », exécuter le
contrat ci-dessous sans reposer de question. EXÉCUTION 100 % LOCALE (Windows) :
`bash pipeline/blender_run.sh <cmd> <spec> [flags]` (Blender installé, bpy embarqué,
part ~4 s, silh ~15 s) — wheel bpy pip impossible (ARM64/Py3.14) ; conteneur
Linux = `bootstrap.sh` puis `python3 pipeline/run.py` comme avant. Python local (hors
bpy) : numpy+PIL dispo, ImageMagick dispo.

## BOUCLE 29 (2026-07-23) — NOUVEAU DRAGON « LE COLOSSE » (quadrupede, muscle) + CONTRAT JEU

Demande utilisateur : retours du projet AVAL (le jeu qui consomme les rendus) = 5 points sur
la LIVRAISON (film alpha transparent sans decor ; anims bouclees SUR PLACE, pas fly-by ;
rendu PAR ETAT MOTEUR carre 576² + sidecar `render.json` ; rig + param couleur ; polish
cadrage/fps/facing/lumiere neutre). ET « cree un nouveau dragon entierement… different,
beaucoup plus imposant, grosse musculature ». Cadre arrete avec lui : **dragon occidental
4 pattes**, **sans armature** (on generalisera la doctrine b28), **GEOMETRIE d'abord** cette
boucle — le harnais de rendu = boucle SUIVANTE (b30, cf. plus bas).

Krokmou et la wyverne INTACTS (spec/refs/score separes ; etat par spec `silh_<spec>.json`).

LIVRABLES b29 (jalon) : `renders/step_562_{hero,head,wide}.png`, `renders/scene.blend`.
**IoU silhouette 0.9581** (au-dessus de la wyverne, atteint au 1er jet de cage).

### La chaine b27 rejouee pour le slug `dragon` (aucune modif de `bx/`)
Ordre obligatoire **trace -> cage -> parts** (cage ECRASE la spec, parts idempotent) :
- `references/dragon_ref.md` : fiche d'espece « colosse lourd/cuirasse », leviers de MASSE
  levier par levier (tonneau sans taille pincee, cou de taureau, garrot en bosse, membres
  colonnes, crane de broyeur, queue-massue) + contraste explicite avec la wyverne.
- `research/tests/gen_dragon_trace.py` = LE document de design : `BODY` (stations lourdes) +
  2 chaines `LEG_FORE`/`LEG_HIND` -> rasterise `references/dragon_ortho_side.png` (la ref
  scoree, committable). Convention : la bete regarde -Y (= `facing:"left"` du jeu). S=0.010,
  X0=560, Y0=660. Bete ~10 u de long, ~3.7 u au garrot.
- `research/tests/gen_dragon_cage.py` -> **ECRIT specs/dragon.json** (corps + 4 pattes +
  sol + scene). Reutilise `tube_along`, la loi de compensation subsurf `A+B/taille`, le
  profil « squircle » (ici PLEIN, pas maigre).
- `research/tests/gen_dragon_parts.py` : 92 appendices fusionnes -> plaques osseuses dorsales
  (`scute`, subsurf 0 : L'IDENTITE cuirassee), cornes balayees, arcade/oeil/machoire, crocs,
  ligne de levre, AILES deployees (envergure ~11.6 u), orteils+griffes des 4 pieds.

### Acquis / mecanismes de cette boucle
- **MUSCULATURE** (le vrai sujet) : `MUSCLE` dans gen_dragon_cage — pousse des SECTEURS de la
  section a certaines stations (deltoide/pectoral/fessier-cuisse). Le muscle vit DANS la peau
  (une seule surface subsurf), pas en blobs boulonnes (qui rendent en oeufs, cf. CLAUDE.md).
  INVISIBLE de profil (largeur = X) -> ne bouge PAS le score de silhouette. Candidat nº1 a
  l'extraction vers `bx/` si on refait un animal muscle.
- **PATTES NON SOUDEES** (comme la wyverne) : 4 tubes `tube_along` mirror_x (leg_fore/hind),
  enfouis dans le tronc. Pas de weld cette boucle (le weld Krokmou `gen_body_weld.py` suppose
  des demi-anneaux 5 pts ; la cage dragon est en 7 pts -> a adapter). `validate` signale les
  pattes en « clipping » (attendu, elles penetrent le tronc/sol).
- `scute()` (gen_dragon_parts) : osteoderme keele facette (hexagone allonge + arete mediane),
  subsurf 0 — l'armure « cuirasse », a ne PAS confondre avec les cristaux/epines.

### Look
Hide de PIERRE sombre NEUTRE (re-teintable en b30 pour la famille de dragons du jeu), grosses
ecailles (`scale` 12, bump 1.2). `bone` os patine sombre, `membrane` cuir sombre (transmission
0.10, le contre-jour l'allume sans cramer — piege « taches blanches » > 0.3). Low-key neutre :
soleil rasant (modele la masse) + 2 rims froids + fill ; key DISCRETE (une key forte cramait
l'aile en tan). Cadrage hero = 3/4 avant BAS (contre-plongee -> domine).

### v2 (2026-07-23) — feedback utilisateur : « ailes j'aime pas / trop cartoon / c'est quoi
### sa specialite ». 3 forks tranches avec lui : SPECIALITE = poison, AILES = en lambeaux,
### anti-cartoon = TOUT. Jalon v2 : `renders/step_569_{hero,head,wide}.png`. IoU 0.9098.
- **SPECIALITE = POISON / CORROSION** : hide corrodee (patina verdigris pousse a 0.55, bump
  1.45 = piquee), oeil vert luminescent, crocs jaune-vert taches, membrane rongee veines
  vertes, et la SIGNATURE = **bave acide** `drool_*` (materiau emissif `acid`, builder `eye`,
  glow) qui pend de la gueule. Base encore re-teintable (le vert vient de patina_color).
- **AILES EN LAMBEAUX** : `web()` gagne `tatter` (bord de fuite ronge irregulier) + `holes`
  (faces supprimees = trous francs) ; les doigts osseux ressortent + petite griffe au bout.
  Grille montee a nu=12 pour des trous ronds. Bord d'attaque peu dechire (structure).
- **ANTI-CARTOON** : (1) PATTES articulees — coude/genou/jarret PINCES, cuisse/triceps en
  masse, zigzag avant-arriere (digitigrade), fini le poteau-ballon. Cout : IoU 0.958 -> 0.910
  (les joints fins retrecissent plus sous subsurf ; ref+cage bougent ENSEMBLE donc c'est de la
  derive 3D, pas une erreur de dessin — assume). (2) CRANE plus dur : **crete nasale osseuse**
  sur l'axe (casse le dome en 2 plans) + arcade plus lourde qui fronce. (3) USURE/asymetrie :
  corne droite + 2 crocs CASSES.

### v3 (2026-07-23) — PASSE TETE (feedback « museau encore lisse ») + demande « passe tete puis b30 »
Jalon v3 : `renders/step_573_{hero,head,wide}.png`. IoU 0.9114 (tenu, +0.0016).
- **SECTION DE CRANE CARREE** : le corps est lofte avec un « squircle » rond -> une tete du
  meme profil rend en MUSEAU-BALLON. Ajout de `HEAD_SECTION` (dessus plat, flancs verticaux,
  COINS DURS) blendee vers SECTION le long du cou (`_blend_section`, gen_dragon_cage). Museau
  BLOCKY. Le score tient : la section ne change pas l'extreme dorsal/ventral (l'outline de profil).
- **PLANS OSSEUX** (gen_dragon_parts, head_parts) : arete zygomatique (`cheek_ridge`) qui
  plaque un plan dur sur la joue desormais plate ; oeil ENFONCE dans l'orbite (out 0.90->0.84)
  sous l'arcade ; jaw_mass reduit (ne re-gonfle plus la joue). Le crane lit « dur/anatomique »,
  plus « boite lisse ».

RESTE (pour b30+) : corps peu de relief musculaire sur les FLANCS ; trous d'ailes un peu
geometriques ; SOUDURE des 4 pattes non faite (adapter gen_body_weld a 7 pts) ; recuperer
l'IoU des pattes (grow par section fine) ; param couleur non expose (b30).

### >>> BOUCLE b30 (le CONTRAT DU JEU — deja cadre, a executer) <<<
Le jeu aval veut, PAR ETAT MOTEUR (SPAWN/IDLE/ALERT/FLY_AWAY/FLY_ACROSS/RECEDE/ROAR/PERCH ;
au min. les 4 de base + ROAR) :
1. **Film TRANSPARENT** (alpha natif), SANS decor -> `core.render` Cycles doit poser
   `sc.render.film_transparent` (EEVEE le fait deja, `core.py:367` ; Cycles NON — 1 ligne).
   Retirer le `ground`/sol des clips. Encoder **VP9 `yuva420p`** (l'alpha survit), pas le
   `libx264 yuv420p` actuel (`anim_wyvern.py`).
2. **Boucles SUR PLACE** (centre, distance/echelle CONSTANTES, ailes qui cyclent, 1re image =
   derniere) — PAS de fly-by camera. Un vrai vol stationnaire (hover, pattes repliees) sert
   IDLE-en-vol + FLY_ACROSS + RECEDE d'un coup (c'est le clip qui manque le plus au jeu).
3. Rendu **carre 576²** + emettre `render.json` a cote : `{fps, frames/etat, facing:"left",
   loop, scale, anchor}` -> consommable tel quel par le `forge.py` du jeu (plus de mapping a
   deviner, plus de duree = frames/24 devinee). fps DECLARE.
4. **Param couleur de materiau** expose (`materials`, base-color) -> decliner une famille de
   dragons a moindre cout (le jeu genere 12 variantes couleur).
5. Polish : cadrage carre a marge CONSTANTE des Blender (supprime l'union-bbox cote jeu),
   orientation documentee (`facing:"left"`), eclairage cle NEUTRE et homogene (evite les
   ailes quasi-blanches qui collent au fond).
Generaliser `research/tests/anim_wyvern.py` en un harnais d'etats nommes (le rig-free
reconstruit deja la scene par image et boucle en `t=i/N`). Plan detaille :
`C:\Users\trist\.claude\plans\valiant-bouncing-blossom.md`.

## BOUCLE 28 (2026-07-23) — TYPE GLACE + ANIMATIONS

Demande utilisateur : « des animations de vol », « des caractéristiques naturelles ou
surnaturelles », « type glace ». Pokédex demandé PUIS écarté par l'utilisateur : « je
veux juste les rendus que je mettrai dans un autre projet » — donc AUCUNE structure de
dex ici, seulement des livrables image/vidéo.

LIVRABLES : `renders/anim/wyvern_{flap,flight,turntable,takeoff}.{mp4,gif}`.
Les séquences PNG (67 Mo) sont GITIGNORÉES — régénérables en une commande.

### Animation SANS armature (le choix structurant)
Le modèle fait ~90 objets séparés (chaque cristal, croc, griffe, panneau de membrane) :
les peser sur un squelette serait long et fragile. Mais tout sort de PARAMÈTRES — une
aile, c'est six points de contrôle. `research/tests/anim_wyvern.py` fait donc du mouvement
une fonction du temps et **reconstruit la scène image par image** (`core.reset()` +
`organic.build()`), ~4 s/image en EEVEE. Le mouvement tient en deux blocs :
- `warp(p, t, motion)` : champ de déplacement appliqué à TOUT point — cristaux, crocs et
  œil suivent gratuitement puisqu'ils sont dans le champ ;
- une rotation d'aile à part, autour de l'axe d'épaule, avec un **retard croissant vers
  la pointe** : c'est lui qui fait le fouetté d'une aile souple.

Réglages qui font la différence (mesurés à l'œil sur les cycles) :
- le corps monte pendant la **descente** des ailes (déphasage d'un quart de cycle) ;
- descente motrice plus ample que la remontée (sinus biaisé) ;
- cou et queue en retard de ~1.2 et ~1.5 rad sur le corps — en phase, la bête est d'un bloc ;
- boucle parfaite : `t = i/N` et non `i/(N-1)`, sinon la dernière image répète la première.

PIÈGES PAYÉS :
- **Les pieds décollaient** : le champ de déplacement soulevait aussi les pattes → la bête
  flottait 8 cm au-dessus de son ombre. Correctif : atténuer le déplacement vertical vers
  le bas du modèle tant que `grounded(t) > 0`.
- Battement **sur place = pattes plantées** (menace/échauffement) ; ne replier qu'en vol
  réel. Le round 1 repliait aussi en `flap` → pattes détachées.
- Ce build de Blender est compilé **sans sortie FFMPEG** (l'enum `file_format` ne propose
  que des images) → encodage par le binaire `ffmpeg` externe (présent en local).
- Au décollage, la caméra doit **panoramiquer** : +3.4 u de montée sortent du cadre fixe.

### Nouveaux mécanismes génériques
- `core.render(settings={'engine': 'EEVEE'})` : ~4 s/image contre ~25 s en Cycles. On perd
  les caustiques et la transmission fine, on garde la lecture du mouvement.
- `pipeline/blender_py.sh <script.py>` : lance un script arbitraire dans Blender (pendant
  de `blender_run.sh`, câblé sur run.py) — pour les outils qui pilotent leur propre boucle.
- `materials.ice()` : glace NATURELLE, pas du verre. Trois traits, dont aucun n'est la
  transparence : laiteuse (SSS domine la transmission — au-delà de ~0.5 sur des pointes
  fines on rejoue le piège des taches blanches), rugosité TACHETÉE (plages polies/givrées
  mélangées par bruit), bleue en PROFONDEUR seulement.
- `crystal()` (gen_wyvern_parts) : prisme facetté `subsurf: 0` — le Catmull-Clark
  arrondirait justement les arêtes qui font la lecture.

### Identité d'espèce
Voir `references/wyvern_ref.md` (réécrit) : traits naturels tous justifiables
(contre-jour double camouflage, réseau vasculaire alaire anti-gel, griffes-crampons,
narines hautes) et **un seul** trait surnaturel assumé — la crête dorsale n'est pas de la
kératine mais de vrais cristaux de glace exsudés, qui repoussent et se brisent.

RESTE : tête encore lisse au close-up ; pattes non soudées ; le turntable recadre un peu
juste sur l'envergure ; le `flap` gagnerait un pliage du coude en haut de course.

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

### v2/v3 — réponse au feedback utilisateur « il est trop cartoon » (2026-07-22)

Diagnostic en 3 causes, traitées dans cet ordre (la 1re domine largement) :
1. **PROPORTIONS** — v1 : tête 22 % de la longueur, queue 26 %, pattes courtes = la
   grammaire du dessin animé (grosse tête = mignon). v2/v3 : tête 17 %, cou 19 %,
   tronc 32 %, queue 35 % tenue à l'**horizontale** (contrepoids de théropode), pattes
   plus longues et plus fines. Crocs ramenés de 18 % à ~9 % de la longueur du crâne.
2. **SECTIONS EN BALLON** — le corps était un loft d'ELLIPSES. Remplacé par un profil
   « squircle » 7 points (dos/ventre aplatis, flancs plats, arêtes dorso- et
   ventro-latérales) : un animal a des PLANS, pas un tube.
3. **PERFECTION** — corne droite CASSÉE net (2 cornes séparées au lieu d'un `mirror_x`),
   un croc cassé. Une bête symétrique et intacte lit « figurine neuve ».

PIÈGES SUPPLÉMENTAIRES PAYÉS EN v2/v3 :
- **Rétrécir une forme sans densifier ses stations la détruit** : la tête v2 (14 %,
  9 stations) rendait un « chausson » — le subsurf 2 lisse d'autant plus qu'une forme
  est petite ET grossièrement stationnée. v3 : 14 stations rien que pour le crâne.
- Un œil nu se lit « bille de verre collée » : il faut une **paupière** qui mord dessus.
- Le profil squircle **résiste mieux au Catmull-Clark** que l'apex d'une ellipse → il
  faut nettement MOINS compenser (`GROW_A` 1.040 → 1.012 ; symptôme : 2.3 % d'excès en
  bande le long du dos).
- **Aile à demi pliée = impasse** (2 échecs) : les panneaux tombent en plans quasi
  verticaux lus « rideau de carton ». Une membrane pliée est un exercice de drapé, très
  dur en peu de polygones. Une membrane TENDUE est physiquement plate entre ses doigts :
  ailes déployées (envergure 9.2 u) + 3 mécanismes dans `web()` — affaissement par
  **gravité** (une membrane pend, elle ne se creuse pas perpendiculairement à elle-même),
  **plis radiaux** en éventail depuis le poignet (visibles en silhouette, ce que le
  `wrinkle_*` du shader ne fait pas), et `drop` qui recule la nappe sous le plan des os
  pour que les doigts **ressortent en nervures** au lieu d'affleurer. C'est ce trio qui
  a fait basculer la lecture.
- **Profondeur de champ** ajoutée (`core.camera(fstop=, focus=)` + `fstop` par shot dans
  `run.py`, défaut None = rétro-compatible) : une image nette du museau au bout de la
  queue est un marqueur « CG » fort, aucun appareil ne fait ça sur un sujet de plusieurs
  mètres.
- Cadrage : avec 9.2 u d'envergure pour 7.5 u de corps, **toute vue latérale occlut** (la
  queue disparaît derrière l'aile). La prise qui marche est quasi-frontale, très basse,
  au grand-angle (40 mm) — les ailes sortent du cadre, donc la bête « ne tient pas dedans ».
- `sheet4` devient inutilisable dès qu'un sol est dans la spec (il cadre sur la bbox
  globale) : juger avec `forge --shot`.

RESTE : tête encore lisse au close-up (le crâne manque d'un décrochement museau/crâne et
d'une masse de mâchoire distincte — c'est le prochain défaut le plus visible) ; pattes NON
soudées au corps (`gen_body_weld.py` est là, non appliqué) ; albédo uniforme (pas de
contre-ombrage ventre/dos, pas de marquages) ; pas de selle/décor.

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
