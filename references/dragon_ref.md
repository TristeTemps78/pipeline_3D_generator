# Le Colosse — cible visuelle et fiche d'espèce (conception MAISON, dragon occidental)

Créature originale, commande de l'utilisateur (2026-07-23) : « crée un nouveau dragon
entièrement… différent, beaucoup plus imposant, avec une grosse musculature ». Choix arrêté
avec lui : **dragon occidental à 4 pattes** (quadrupède + 2 ailes séparées), registre
**colosse lourd, cuirassé, écrasant** — l'exact opposé de la wyverne (bipède sec et nerveux).
La wyverne « rampe affamée » ; le Colosse, lui, est **une masse qui avance** : rien ne
l'arrête, il n'a pas besoin d'être rapide.

## La référence est à nous

`references/dragon_ortho_side.png` — généré par `research/tests/gen_dragon_trace.py`, qui
**est** le document de design (stations `BODY` + chaînes `LEG_FORE`/`LEG_HIND`). Committable
(aucun ©), donc `run.py silh` tourne aussi en conteneur/CI. Contrepartie assumée (comme la
wyverne) : décalque et cage sortant du même tableau, l'IoU ne valide pas le DESSIN — il
mesure la dérive 3D→2D (rétrécissement subsurf, coudes de tube, jonctions de pattes).

Décalque = CORPS + 4 PATTES seulement : ailes, cornes, dents, crête dorsale en sont exclus et
masqués au scoring par `scene.silh.exclude_like`.

## Fiche d'espèce

**Le Colosse.** Dragon de siège, quadrupède, cuirassé. ~10 m du museau au bout de la queue,
~4 m au garrot, plusieurs tonnes. Stance BASSE et LARGE. Ce n'est pas un chasseur d'altitude,
c'est un **bélier vivant**.

### Ce qui fait la MASSE (les leviers de « musculature/imposant », levier par levier)

C'est le cahier des charges de la boucle géométrie. Chaque levier a une traduction chiffrée
dans `gen_dragon_trace.py` (stations `BODY`, profil `SECTION`, renflements musculaires).

- **Poitrail en tonneau, PAS de taille pincée.** La wyverne creuse la taille pour lire
  « affamée » ; le Colosse la garde PLEINE — cage thoracique et ventre forment un seul bloc.
  C'est la différence nº1 de silhouette.
- **Quille sternale profonde + pectoraux** : le poitrail descend bas entre les pattes avant,
  et les masses pectorales le débordent latéralement (renflement de section, visible de face
  et au 3/4 — le côté « musclé » que le profil pur ne montre pas).
- **Encolure de taureau** : cou COURT et TRÈS épais, presque aussi large que le crâne, porté
  bas et droit (pas l'arc de cygne d'un dragon d'illustration). Un trapèze massif le relie au
  garrot.
- **Épaules et hanches en renflements localisés** (deltoïde, quadriceps/biceps fémoral) :
  ce sont des bulges de section posés sur les stations d'attache des membres, pas un
  élargissement uniforme du tube.
- **Membres colonnes** : pattes ÉPAISSES et relativement droites (graviportantes, comme un
  éléphant/sauropode), pas les jambes fines et pliées d'un coureur. Pieds larges à gros
  orteils écartés — l'appui d'un poids lourd.
- **Crâne LARGE et lourd** : mâchoire massive, arcade épaisse, masses temporales/masséters
  marquées (le muscle qui broie). Museau carré, jamais effilé (un museau qui s'affine =
  herbivore). Petit œil sur un grand crâne = gros animal.
- **Queue épaisse à la base**, tenue basse et lourde, s'amincissant peu — un contrepoids de
  massue, pas un fouet.

### SPÉCIALITÉ (arrêtée avec l'utilisateur, 2026-07-23) — le POISON / la CORROSION

Le Colosse est un **charognard cuirassé venimeux**. Sa spécialité, lisible d'un coup d'œil :
- **Bave acide** qui pend de la gueule (`drool_*`, matériau émissif `acid` vert) — la
  signature ; positions/longueurs irrégulières (asymétrie voulue, pas décoratif).
- **Cuirasse rongée** : la hide et les plaques osseuses sont **corrodées** — le système
  `patina` (verdigris) du builder `reptile_scales` poussé à fond dépose du vert acide dans les
  creux, comme si la bête était attaquée par son propre poison ; `bump` relevé = surface
  **piquée** (corrosion), pas lisse.
- **Œil vert-poison luminescent** (glow relevé), **crocs jaune-vert tachés** (macèrent dans
  l'acide, pas de l'ivoire).
- Registre : lent, blindé, il empoisonne et digère — il n'a pas besoin d'être rapide.

### Trait d'identité — la CUIRASSE (osseuse, corrodée)

Le dos et la nuque portent des **plaques osseuses fusionnées** (ostéodermes, `scute()`,
`subsurf: 0` facetté) + une **crête nasale** osseuse sur l'axe du museau (casse le dôme lisse
en deux plans — anti-cartoon). Deux grandes cornes frontales balayées (bélier) dont **la
droite est cassée** ; deux **crocs cassés** : une bête qui se bat, pas une figurine neuve.

### Ailes EN LAMBEAUX (refonte 2026-07-23, feedback « les ailes j'aime pas »)

Plus de membrane chauve-souris lisse : **ailes déchirées de charognard**. Mécanismes dans
`web()` (gen_dragon_parts) : `tatter` ronge irrégulièrement le bord de fuite, `holes` perce
des trous francs (faces supprimées, `subsurf: 0` → bords bruts) ; les **doigts osseux
ressortent** au-delà de la membrane rongée et se prolongent en petites griffes. Bord d'attaque
peu déchiré (c'est la structure), inter-doigts et grand pan arrière en lambeaux.

### Couleur — paramétrable (retour du jeu)

Base neutre-sombre re-teintable exprès (boucle b30, `materials`) : le vert vient surtout de la
**patina** de corrosion, donc décliner une famille (autre venin : violet, jaune…) = changer la
`patina_color` + `base`, pas repeindre. Le jeu génère 12 variantes de couleur.

## Contraste avec la wyverne (pour ne pas refaire deux fois le même animal)

| Levier | Wyverne (sec/nerveux) | Colosse (lourd/cuirassé) |
|---|---|---|
| Plan corporel | bipède + ailes-bras | **quadrupède** + ailes séparées |
| Taille | pincée (affamé) | **pleine** (bloc en tonneau) |
| Cou | long, en arc, sec | **court, épais, de taureau** |
| Membres | digitigrades fins, hauts | **colonnes épaisses**, stance basse |
| Crâne | coin bas et long | **large et lourd**, mâchoire de broyeur |
| Dos | cristaux de glace exsudés | **plaques osseuses cuirassées** |
| Registre | prédateur qui rampe | **masse qui écrase** |

## Repères chiffrés

Échelle `S`, `X0` (x_img → Y=0) et `Y0` (sol → Z=0) définis en tête de `gen_dragon_trace.py`.
La créature regarde vers **−Y** (= `facing:"left"` du jeu aval). Convention image : x vers la
DROITE = museau→queue, y vers le BAS, pieds au sol. La 4ᵉ colonne des stations `BODY`
(demi-largeur) est le degré de liberté que le décalque de profil ne peut pas montrer — c'est
là que passe la largeur « de taureau ».

## Chaîne de génération (ordre obligatoire)

```
gen_dragon_trace.py   -> references/dragon_ortho_side.png   (le document de design)
gen_dragon_cage.py    -> ÉCRASE specs/dragon.json           (corps, 4 pattes, sol, scène)
gen_dragon_parts.py   -> fusionne les appendices            (idempotent : ailes, cornes,
                                                              dents, plaques dorsales, griffes)
```

Harnais de rendu du jeu (états moteur, alpha carré 576², render.json, param couleur) : voir
`HANDOFF.md` — boucle b30, préparée mais hors de la boucle géométrie b29.
