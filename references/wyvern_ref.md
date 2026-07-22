# Wyverne des glaces — cible visuelle et fiche d'espèce (conception MAISON)

Créature originale, commande de l'utilisateur (2026-07-22) : « fais TON dragon, réaliste,
quelque chose d'impressionnant qui fait peur », puis (2026-07-23) « type GLACE, avec des
caractéristiques naturelles ou surnaturelles ». Choix arrêtés avec lui : **wyverne**
(2 pattes + ailes = bras), registre **prédateur sec et nerveux**, pose **à l'affût**.

## La référence est à nous

`references/wyvern_ortho_side.png` — généré par `research/tests/gen_wyvern_trace.py`, qui
**est** le document de design (stations `BODY` + chaîne `LEG`). Committable (aucun ©),
donc `run.py silh` tourne aussi en conteneur et en CI, ce que les réfs © de Krokmou
interdisaient. Contrepartie assumée : décalque et cage sortant du même tableau, l'IoU ne
valide pas le DESSIN — il mesure la dérive 3D→2D (rétrécissement subsurf, coudes de tube,
soudures). C'est exactement le défaut qu'il a rattrapé en b26.

Décalque = CORPS SEUL : ailes, cristaux, cornes et dents en sont exclus et masqués au
scoring par `scene.silh.exclude_like`.

## Fiche d'espèce

**Type : GLACE.** Prédateur d'altitude des plateaux gelés. ~7,5 m du museau au bout de la
queue, 9,2 m d'envergure, bipède digitigrade.

### Traits naturels (tout est justifiable)

- **Contre-jour et non contre-ombrage** : le dos est presque noir, seules les **arêtes**
  des écailles remontent en bleu givré. Sur un plateau de neige aveuglant, une bête
  sombre vue d'en bas se découpe sur le ciel ; vue d'en haut, ses arêtes claires la
  fondent dans la glace craquelée. Les deux camouflages en un.
- **Tête petite, cou long, queue de contrepoids** (14→17 % / 19 % / 35 % de la longueur) :
  proportions de théropode, pas de dragon d'illustration.
- **Membranes alaires à réseau vasculaire dense** (visible dans le shader) : échangeur à
  contre-courant qui empêche le gel des extrémités — le vrai problème d'un animal ailé
  par −40 °C.
- **Pattes digitigrades à griffes-crampons**, orteils écartés : portance sur la neige et
  ancrage sur la glace vive.
- **Museau étroit à narines hautes** : l'air inspiré est réchauffé par un long trajet
  nasal avant d'atteindre les poumons.
- **Œil petit, enfoncé sous une arcade osseuse**, iris bleu pâle laiteux : protection
  contre le vent de glace et l'éblouissement ; un petit œil fait aussi lire un GROS animal.
- **Usure** : corne droite cassée net, un croc brisé. Une bête intacte et symétrique lit
  « figurine neuve ».

### Trait surnaturel (un seul, assumé)

- **La crête cristalline.** Les épines dorsales ne sont pas de la kératine : ce sont de
  vrais **cristaux de glace**, poussés hors de la peau par une sécrétion sursaturée que
  l'animal exsude le long de sa ligne dorsale. Ils repoussent après chaque combat, se
  brisent, se ramifient — d'où les éclats latéraux désalignés une station sur deux. C'est
  le trait d'espèce le plus lisible en silhouette, et il justifie que la géométrie soit
  **facettée** (`subsurf: 0`) au milieu d'un corps entièrement lissé.

## Ce qui doit faire peur (les leviers, pas le hasard)

| Levier | Krokmou (contre-exemple) | Wyverne |
|---|---|---|
| Crâne | galet rond et haut | **coin bas et lourd**, museau carré (un museau qui s'effile = herbivore) |
| Chanfrein | convexe | **creux** : le profil concave fait le reptile |
| Œil | énorme (r 0.21) | **petit** (r 0.072) sous une arcade, avec paupière |
| Nuque | continue | **encoche occipitale** : c'est elle qui DÉTACHE la tête |
| Tronc | ovale régulier | quille sternale puis **taille pincée** — le contraste fait la faim |
| Sections | ellipses | **squircle** : dos et flancs plats, arêtes marquées. Un animal a des PLANS |
| Membres | trapus | **digitigrades** en Z, hauts sur pattes |

## Repères chiffrés

Échelle `S = 0.009` u/px, `X0 = 420` (x_img 420 → Y=0), `Y0 = 545` (sol → Z=0).
La créature regarde vers **−Y**. Longueur ≈ 7.5 u, hauteur au garrot ≈ 2.9 u,
envergure ≈ 9.2 u. Axe d'épaule (plan de battement) : Y −0.15, Z 2.28.

## Chaîne de génération (ordre obligatoire)

```
gen_wyvern_trace.py   -> references/wyvern_ortho_side.png   (le document de design)
gen_wyvern_cage.py    -> ÉCRASE specs/wyvern.json           (corps, pattes, sol, scène)
gen_wyvern_parts.py   -> fusionne les appendices            (idempotent)
anim_wyvern.py        -> renders/anim/<motion>/ + mp4 + gif
```
