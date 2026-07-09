# Doctrine v1 « organisme continu » (boucle 11+) — synthèse convergente

Sources : 2 réponses externes au prompt boucle 11 (identiques entre elles) + recommandation
orchestrateur. Convergence totale sur les 5 axes. STATUT : test en boucle 11 — adoption
définitive conditionnée au feedback utilisateur.

## Les 5 axes (ordre d'implémentation)
1. **SDF = colonne vertébrale des masses organiques** (pas seulement les jointures).
   `fuse_groups` déclarés dans la spec (ex. `torso+wing_roots+leg_roots`, `neck+head`,
   `tail_root`) → Mesh to SDF Grid → SDF Grid Boolean UNION → SDF Grid FILLET (rayon
   paramétrable par groupe) → Grid to Mesh UNE fois → armure/détails re-skinnés sur la coque
   fusionnée. Armure et petits accessoires restent des instances mesh (hors SDF).
   T10 valide : tous les nodes dispo en bpy 5.0.1 headless (y c. GeometryNodeSDFGridFillet).
2. **attachment_curve = concept de spec de 1er rang** : une pièce s'attache le long d'une
   COURBE paramétrique sur la surface parente (u0..u1 sur le loft), pas en un point.
   Cas d'usage : aile↔flanc (« nageoire »), corne↔arcade, piques↔crête dorsale.
3. **Vocabulaire de relief minimal** (opérations de SURFACE, pas de nouveaux blobs) :
   `ridge_line` (crête + train de piques, profil hauteur/largeur/falloff, jitter),
   `carve_feature` (creusage : naseaux, orbites), `displacement_zone` (zones héros
   multi-octaves), plus tard `curvature_mask` (concentrer le relief sur les convexités).
4. **Œil composite** : builder générique sclère+cornée bombée+iris/pupille+paupières,
   matériaux séparés (cornée glossy transparente, spéculaire « vie »), paramétré spec.
5. **Perception ×5-10 par itération, hors-LLM** : planche multi-vues (ortho face/profil/
   dessus + héros + silhouette), passe ID par pièce (couleurs plates), métriques calculées
   en Python (IoU par pièce, histogrammes de courbure) résumées en JSON court, caméras
   anatomiques prédéfinies (tête/racine d'aile/pattes/yeux), script d'introspection scène
   (pièces, bbox, compteurs) donné aux agents en texte.

## Ordre retenu (les 2 réponses + orchestrateur d'accord)
Boucle 11 : axe 5 (léger, d'abord — il sert à juger le reste) + axe 1+2 sur torse/ailes
(« l'aile ne DOIT plus pouvoir se coller en un point »). Boucle 12 : axe 3 + re-block crâne
carré massif SDF (menton, naseaux carvés, arcades→cornes). Boucle 13 : axe 4 (yeux) +
pattes visibles en vol (bug z absolus orteils corrigé). Intégration perception au fil de l'eau.

## Backlog feedback step_118 couvert par quel axe
aile collée au corps → axes 1+2 · tête carrée massive/relief/lignes+piques → axes 1+3 ·
naseaux → axe 3 (carve) · yeux réels → axe 4 · pattes visibles → boucle 13 + bug limb.
