# Prompt de réflexion boucle 16 — plafond de détail & bake headless

## Contexte
Nous construisons un pipeline **GÉNÉRIQUE texte→3D** en Python + Blender headless (bpy),
sans aucun autre outil ni session interactive. Une phrase/référence produit une **spec
JSON** (pièces paramétriques : spine, head, wing, limb…) ; des builders la transforment
en scène : lofts superellipse, tubes/blobs, **fusion SDF** entre pièces (masses
continues), **écailles = géométrie instanciée** (archétypes + Geometry Nodes Pick
Instance) pilotée par masques (bandes axiales + normale de surface `nx/ny/nz`) et
gradients/bruits de taille, matériaux procéduraux (patine par cavité/Pointiness, veines
Voronoi, micro-plis), rendu multi-prises à cadrage automatique par pièce. Banc d'essai :
un dragon type Drogon (GoT), mais **aucun code spécifique à l'objet n'est autorisé** —
tout mécanisme nouveau doit être un paramètre de spec réutilisable par une future
créature/véhicule/bâtiment.

Chaque itération est jugée par **métriques** contre la référence (couleur moyenne,
fraction cuivrée, densité de bords Sobel) + inspection visuelle multi-vues.
Contraintes dures : rendu final sur machine locale modeste (CPU, parfois GPU) en
**minutes maximum** (on vient d'éliminer une brume volumétrique qui coûtait 2 h →
38 s) ; budget scène **≤ ~400 k sommets** ; Cycles 20 samples + OpenImageDenoise.

## Ce qui marche
- Silhouette, proportions, pose de vol ; ailes membraneuses organiques : doigts en
  éventail arqués, main carpienne fusionnée SDF au bras, membrane charnue par panneaux,
  bord de fuite festonné, deux générations de nervures suivant le relief.
- Écailles par zones anatomiques (ventre = plaques larges lisses, dos = carènes
  serrées, flancs = mix) + patchs de taille par macro-bruit : densité de bords
  0.233 → **0.30** (référence : 0.35).
- Tête blockée : cornes à anneaux de croissance, crocs variés, gencives/lèvres.
- Perf : rendu HQ 1152×864 ≈ 40 s CPU.

## Ce qui ne marche pas / plafonne
1. **Le détail reste « procédural visible »** : les écailles sont des instances posées
   SUR une surface lisse — pas de peau continue imbriquée, pas de plis de peau aux
   articulations, transitions entre pièces encore « CG ». En gros plan (shot tête),
   ça ne soutient pas la comparaison avec un vrai sculpt.
2. **La densité de bords plafonne ~0.30** : chaque cran de détail supplémentaire en
   géométrie réelle fait exploser sommets et temps de rendu — le micro-détail (rides,
   grain de peau, micro-écailles, réseau vasculaire fin) est inatteignable ainsi.
3. **Pas d'étage de bake** : tout le détail matériau est évalué à CHAQUE rendu (nœuds
   procéduraux) ; rien n'est écrit en textures image (normal/displacement/albedo/AO).
   L'objectif utilisateur explicite : « sculpter les détails organiques et les baker
   sur des cartes de normales et de déplacement, utiliser des textures d'images au lieu
   de nœuds procéduraux complexes en temps de rendu » — mais en **headless scripté et
   générique** (pas d'UV faits main, pas de sculpt manuel).
4. **Boucles par objet** : malgré les mécanismes génériques accumulés, chaque nouveau
   palier de qualité redemande des allers-retours spécifiques (recalage d'ancres, de
   masques, de valeurs). Objectif : encoder le savoir-faire UNE fois dans le pipeline.

## À résoudre
A. Comment obtenir un rendu « sculpté organique » (peau continue, écailles imbriquées
   dans la surface, plis, micro-relief) avec bpy headless scripté, dans les budgets
   (~400 k sommets, minutes de rendu) ? Multires + displacement baké ? Coque haute
   densité temporaire (voxel remesh) sculptée procéduralement puis projetée ?
B. **Pipeline de bake générique headless** : UV automatiques fiables (Smart UV
   Project ? autre ?), bake normal/displacement/AO/albedo du haut-poly procédural vers
   le low-poly, ré-application automatique des maps — quelles API bpy exactes, quels
   pièges (marges, cage, espace tangent, seams, îlots), comment rester spec-driven ?
C. **Micro-détail perçu sans micro-géométrie** : quelles combinaisons (normal maps
   bakées, bump multi-échelles, masques de courbure/AO) maximisent la densité de bords
   perçue à coût de rendu quasi nul ?
D. **Architecture** : comment structurer ces étapes (proxy-sculpt → bake → assemblage
   final) pour qu'un futur objet les réutilise sans nouvelle boucle d'ingénierie ?

**Question : comment résoudre concrètement ces problèmes dans ce pipeline ?** Propose
une architecture d'étapes bpy scriptées (ordre, données échangées), les API/nœuds
précis, les ordres de grandeur (résolutions de maps, comptes de sommets par étage,
temps attendus), et les pièges connus de chaque étape.
