# Inversions — « regarde comment tu fais, fais le contraire »

Cible : `references/drogon_*.png` (Drogon / "The Tyrant Dragon rig", qualité film).
Écart mesuré d'entrée de jeu : écailles cuivrées cible ≈ **RGB linéaire (0.24, 0.16, 0.14)**
(42-46 % du sujet) — mon dragon actuel utilise du quasi-noir (0.008). Trop sombre, trop saturé.

Méthode : pour chaque **hypothèse implicite** de mon pipeline actuel, j'écris son **inversion**
et un **test** qui la départage numériquement ou en macro-rendu. Les inversions gagnantes
deviennent l'architecture (comme pour convergence.md).

| # | Hypothèse actuelle | Inversion | Test |
|---|---|---|---|
| I1 | **Écailles = bruit de displacement** (voronoi/clouds). Lisse la surface, « peau bosselée ». | **Les écailles SONT de la géométrie** : plaques carénées discrètes qui se chevauchent, alignées cranio→caudal. La surface est faite d'écailles, pas bruitée. | `t8` : patch macro écailles-géo vs `drogon_wing_membrane`/cou — densité de bords (Sobel) et lecture « plaques » à courte distance. |
| I2 | **Je juge à l'œil** un rendu plein cadre, la réf est ailleurs. | **La réf est le compagnon constant** : chaque rendu est produit CÔTE À CÔTE avec la frame de réf correspondante + deltas numériques (histogramme couleur, densité de détail). Jamais de rendu orphelin. | `t9` : `compare_sheet` réf|rendu + score couleur/détail ; vérifier qu'il chute quand la couleur diverge. |
| I3 | **Je rends le dragon entier, petit.** La tête fait 40 px. | **Macro-photographie par région.** Zoomer, pas dézoomer : tête, racine d'aile, patte, patch d'écaille — chacun poussé à la qualité film, PUIS assemblé. La réf s'attarde sur la tête → moi aussi. | Rendus macro par région (cams dédiées) ; la tête doit remplir le cadre comme `drogon_head_roar`. |
| I4 | **Shaders en dernier, clay toujours.** Le look est un après-coup. | **Look co-développé sur patch isolé.** À qualité film, le MATÉRIAU (SSS peau, translucidité de membrane sur les bords, rupture spéculaire) porte autant de réalisme que la géo. Testé sur sphère/patch avant l'assemblage. | Patch SSS cuivré vs couleur cible mesurée (0.24,0.16,0.14) ; membrane rétro-éclairée doit montrer translucidité de bord. |
| I5 | **Génération procédurale symétrique par lois de croissance** (inside-out). | **Ajustement piloté par la réf** (outside-in) : boucle qui optimise les params de spec pour MAXIMISER l'IoU/le score, au lieu que je devine les nombres. Asymétrie contrôlée de pose. | Optimiseur simple (recherche locale) sur 2-3 params × IoU silhouette ; l'IoU doit monter de façon monotone. |
| I6 | **Corps monolithique validé en bloc** (voxel-fuse global). | **Budget de détail par région** : la fusion reste globale MAIS le détail (densité d'écailles, force de displace, plis) est masqué par région anatomique (dos > flanc > ventre), piloté par la courbure ET des groupes de vertex nommés. | Densité d'écailles mesurée dos vs ventre ; ratio doit suivre la réf (dense sur crêtes). |
| I7 | **Une caméra, une lumière soleil douce.** | **Éclairage dramatique de contre-jour** (rim light) qui sculpte la silhouette et révèle les bords d'écailles et la translucidité de membrane — c'est ce qui fait « lire » le détail dans la réf (fond noir, jantes lumineuses). | Rendu même géo, éclairage doux vs rim ; densité de bords perçue (Sobel) doit augmenter au rim. |

## Priorisation (réalisme par itération)

1. **I1 (écailles géo)** + **I4 (matériau SSS cuivré)** = le plus gros saut visuel vers la réf.
   Le bruit ne deviendra jamais des écailles ; la couleur noire ne deviendra jamais du cuivre.
2. **I2 (réf côte-à-côte)** = change ma façon d'itérer : ancre chaque pas sur la cible, pas sur mon œil.
3. **I3 / I7** = rendre le détail visible là où il compte (macro + rim).
4. **I5 / I6** = raffinements d'automatisation une fois le langage visuel en place.

## Journal des tests

- `t8_geo_scales.py` → `research/logs/t8_geo_scales.json`, `research/renders/t8_*.png`
- `t9_ref_compare.py` → `research/logs/t9_ref_compare.json`, `research/renders/t9_*.png`

Résultats consignés ci-dessous au fur et à mesure.

### I1 — écailles géo vs bruit (t8), rendus macro

| | densité de bords (Sobel) | lecture |
|---|---|---|
| displacement voronoi (approche actuelle) | **0.0001** | bosses floues, jamais des écailles |
| écailles carénées chevauchantes (I1) | **0.0162** | **plaques discrètes alignées, ×162** |

Le bruit ne franchit pas le mur « écaille » ; la géométrie oui. `keeled_scale` + `armor_scales`
(alignement Z→normale, Y→caudal, Poisson) donnent un tuilage lisible. Knob `lift` : haut = crêtes
dorsales dressées, bas = armure ventrale serrée. **Adopté** dans `bx/detail.py`.

### I2/I4/I7 — réf côte-à-côte + SSS cuivré + rim (t9)

Cible mesurée (Drogon body_flight) : couleur moyenne sujet ≈ **(0.24,0.16,0.14)**, densité de bords **0.24**.

| rendu | couleur moyenne | écart couleur L2 → réf | part cuivre | densité bords |
|---|---|---|---|---|
| clay (actuel) | (0.58,0.58,0.57) | **0.524** | 0.00 | 0.007 |
| peau cuivre+SSS+rim+écailles (I1+I4+I7) | (0.20,0.13,0.09) | **0.238** | 0.95 | **0.20** |

L'inversion **halve l'écart couleur** et amène la densité de détail au niveau de la réf (0.20 vs 0.24).
`compare_sheet` (I2) rend réf|rendu en un PNG + ces deltas → **chaque itération est ancrée sur la cible,
pas sur mon œil**. Réserve : part cuivre 0.95 > réf 0.43 (sur-cuivré, à tempérer) ; cellules voronoi un
peu « boue craquelée » (agrandir l'échelle, adoucir les arêtes). **Adopté** : `bx/feedback.compare_sheet`,
`materials.reptile_scales(sss=…)`, `core.rim_setup`.

### Bilan

Les 4 inversions testées (I1, I2, I4, I7) gagnent nettement et sont câblées. Prochaines : I3 (macro
par région — déjà outillé par `compare_sheet`/`rim_setup`), I5 (optimiseur IoU), I6 (masques de densité
par groupe de vertex). Le langage visuel « vraies écailles + chair cuivrée + contre-jour + comparaison
réf » est en place ; reste à l'appliquer à l'anatomie du dragon et à zoomer région par région.
