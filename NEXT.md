# NEXT — backlog long terme (lu au CADRAGE d'une boucle seulement ; état courant → HANDOFF.md)

Priorisé, à recadrer à chaque feedback. Le « fait » vit dans git log + HANDOFF, pas ici.

0. ROADMAP utilisateur (feedback step_141, détail intégral dans session.json) — chaque item
   doit devenir un MÉCANISME PIPELINE générique, pas une rustine spec (« les boucles qu'on
   fait maintenant, je ne veux pas les refaire plus tard ») :
   a. Écailles : variation de taille par zone (ventre fin / dos+membres robustes — étendre
      scale_grad/masks en gradient multi-zones générique), plis de peau aux articulations
      (nouvel op générique `fold_rings` aux joints des tubes limb/spine).
   b. Tête : iris reptilien (shader fente verticale), narines creusées nettes, cornes plus
      définies, gencives + dents individualisées, rides autour des yeux.
   c. Membrane : réseau tendons/vaisseaux SOUS la peau (shader bump/veines procédural
      générique dans materials.py), peau fine plissée (micro-plis).
   d. PBR patine : cuivre frotté + vert-de-gris dans les CREUX (masque cavité/AO générique
      dans le shader écailles), reflets dorés sur bords exposés, griffes/épines cornées,
      cicatrices subtiles.
   e. Environnement : fond détaillé flou (caverne trésor / canyon), lumières d'appoint
      dorées, volumétriques (brume, poussière d'or) — builders scène génériques.
1. Membrane organique niveau 2 (après boucle 13) : micro-plis dynamiques, translucidité
   contrôlée sans taches (cf. pièges claude.md), déchirures/cicatrices héros.
2. fuse_groups : étendre à head (couture crâne/cou) et hindleg (hanche) — BLOQUÉ tel quel
   (constat boucle 13) : la fusion consomme skull/tubes de patte dans le groupe `body`, or
   `detail.armor` cible les groupes par id (`head`, `hindleg`) et le masque corps monte à
   y=3.5 → régression exacte du fix boucle 12 (armure corps sur la tête). Prérequis : armure
   par masque SPATIAL sur mesh fusionné (ou fusion préservant l'appartenance aux groupes).
3. Œil : validation gros plan couleur (cadrage dédié), contraste iris/pupille, paupière.
4. (Doctrine axe 3) vocabulaire relief générique : `ridge_line` (crête + train de piques),
   `carve_feature` (naseaux creusés, orbites), `displacement_zone` (zones héros).
5. Look : recaler couleur/atmosphère sur la réf (`run.py compare` : cuivre .42, bords .36) —
   la priorité utilisateur reste la densité de détail (bords), pas la couleur.
6. Généricité : 2e créature de test pour prouver que rien n'est spécifique dragon
   (banc d'essai du pipeline texte→spec→3D complet ingest→grounding→generation→evaluation).
7. Doctrine SDF v1 (`research/doctrine_sdf_v1.md`) : axes restants — SDF backbone complet,
   attachment_curve généralisé.
