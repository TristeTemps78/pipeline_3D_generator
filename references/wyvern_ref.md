# Wyverne — cible visuelle (conception MAISON, 2026-07-22)

Pas de modèle externe : cette créature est une commande de l'utilisateur (« fais TON
dragon, réaliste, quelque chose d'impressionnant qui fait peur »). Choix arrêtés avec lui :
**wyverne** (2 pattes + ailes = bras), registre **prédateur sec et nerveux**, pose **à
l'affût, tête basse**.

## La référence est à nous

`references/wyvern_ortho_side.png` — généré par `research/tests/gen_wyvern_trace.py`, qui
**est** le document de design (tableau `BODY` : stations `x, y_haut, y_bas, demi-largeur`,
+ chaîne `LEG`). Conséquences :
- committable (aucun ©) → contrairement à Krokmou, le score de silhouette tourne aussi en
  conteneur et en CI ;
- `gen_wyvern_cage.py` importe ce même tableau. **L'IoU ne valide donc pas le dessin** (il
  vient d'ici) : il mesure la DÉRIVE 3D→2D — rétrécissement du subsurf, forme des
  sections, coudes de tube, soudure des membres. C'est exactement le défaut que la
  métrique a rattrapé en b26 (−0.011 à la soudure des pattes) ;
- `wyvern_ortho_side_nolegs.png` = tronc seul, aide de lecture, non scorée.

Le décalque est CORPS SEUL : ailes, cornes, dents, épines dorsales en sont exclues et
masquées au scoring par `scene.silh.exclude_like`.

## Ce qui doit faire peur (et pourquoi), levier par levier

| Levier | Krokmou (contre-exemple) | Wyverne |
|---|---|---|
| Crâne | galet rond et haut | **coin bas et lourd**, 184 × 116 px (1.6:1) |
| Museau | s'effile en museau de chat | **carré et massif** au bout (44 px) — un museau qui s'effile lit « herbivore » |
| Chanfrein | convexe | **creux** entre les narines et l'orbite : le profil concave fait le reptile |
| Œil | énorme (r 0.21) | **petit** (r ≈ 0.09) et enfoncé sous une arcade — un petit œil fait lire un GROS animal |
| Nuque | continue | **encoche occipitale** : c'est elle qui DÉTACHE la tête du cou |
| Cou | épais et court | 44 px seulement, **sec et tendu**, en arc de frappe |
| Tronc | ovale régulier | **quille sternale 142 px** puis **taille pincée 96 px** — le contraste fait la faim |
| Membres | trapus | **digitigrades** en Z : genou avant, talon haut en arrière, métatarse long |
| Ligne générale | ramassée | **822 × 317 px (2.7:1)** : ça rampe vers toi |

Pose : les 2 pattes sont plantées **symétriquement**, donc superposées exactement de
profil — le rendu ortho vaut le décalque, sans la pénalité d'IoU qu'imposait la pose de
marche de Krokmou.

## Repères chiffrés

Échelle `S = 0.009` u/px, `X0 = 420` (x_img 420 → Y=0), `Y0 = 545` (sol → Z=0).
La créature regarde vers **−Y**. Longueur ≈ 7.5 u, hauteur au garrot ≈ 2.9 u.
