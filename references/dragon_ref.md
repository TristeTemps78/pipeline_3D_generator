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

### Trait d'identité (un seul, assumé) — la CUIRASSE

Le dos et la nuque portent des **plaques osseuses fusionnées** (ostéodermes épais, façon
crocodile/ankylosaure) : une véritable armure vivante, pas une crête décorative. C'est ce qui
dit « cuirassé/imposant » en silhouette et justifie une géométrie **facettée** (`subsurf: 0`
sur les plaques) au milieu d'un corps entièrement lissé. Deux grandes cornes frontales
balayées vers l'arrière complètent le bloc-tête en bélier.

### Couleur — paramétrable (retour du jeu)

Base = hide de pierre sombre (basalte/obsidienne), relief d'écailles épaisses. La couleur de
base sera **exposée en paramètre** (boucle b30, `materials`) pour décliner une famille de
Colosses à moindre coût (le jeu génère 12 dragons par variantes de couleur). On garde donc
une base neutre-sombre qui accepte un re-teintage franc, plutôt qu'une couleur d'espèce figée.

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
