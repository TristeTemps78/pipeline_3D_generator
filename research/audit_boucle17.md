# AUDIT boucle 17 — pourquoi le dragon « se ressemble » depuis 5 boucles

Demande utilisateur (step_182) : audit réel, causes racines, vrais changements visibles.

## Constat honnête
Les boucles 12-16 ont construit des MÉCANISMES corrects (aile organique, zones d'écailles,
multi-shots, perf 2h→39s, bake high→low) mais l'IMAGE perçue a peu bougé. Les métriques
suivies (cuivre, bords Sobel) sont myopes : elles valident des deltas locaux, pas la
lecture globale « on dirait la référence ». Diagnostic par cause racine :

### CR1 — Le LOOK n'a jamais quitté le camaïeu brun-sur-brun (impact : énorme)
Réf : noir charbon + rouge profond, contrastes durs, rim light qui découpe chaque écaille,
fond sombre. Nous : sujet beige/cuivre clair sur fond brun clair, lumière douce uniforme.
Résultat : les écailles GÉOMÉTRIQUES (elles existent — 22k instances) ne LISENT pas ;
l'évaluateur externe conclut « aucune écaille visible, images sans texture ». La fraction
cuivrée .455≈réf est un faux ami : la MOYENNE colle, la DISTRIBUTION (quasi-noir + rouges
saturés + hautes lumières spéculaires) non.
→ FIX boucle 17 : look v3 « charbon/rouge » — albédo par instance varié (Object Info
Random), base presque noire, arêtes rouge-cuivre, roughness contrastée, rim dur, fond
quasi noir. C'est le levier n°1 du « vrai changement ».

### CR2 — La POSE est figée depuis la boucle 10 (impact : énorme)
Même vol plané en T, même caméra plongée, mêmes ailes symétriques. N'importe quel modèle
resemblerait « au même dragon ». La spec sait déjà tout piloter (spine pts, tips, cou).
→ FIX : pose dynamique — virage bancé (ailes asymétriques), queue en S, cou en arc,
gueule rugissante ouverte. PIÈGE connu : recaler les ancres absolues après tout
déplacement de spine (claude.md).

### CR3 — La TÊTE reste un assemblage de primitives lisible comme tel (impact : fort)
Mâchoires = 2 lofts droits → effet « pince/bec » ; ligne de bouche = coupe rectiligne ;
dents = cônes réguliers ; œil = boolean + matériau global = regard mort.
→ FIX (feedback détaillé) : courbure non-linéaire des mâchoires (profil crocodilien :
museau qui plonge puis remonte), bruit + épaisseur de lèvre sur la ligne d'ouverture,
dents variance forte taille/inclinaison ancrées dans un bourrelet de gencive, EyeBuilder
(cavité SDF, paupières fondues, matériau œil spéculaire isolé, iris gradient, HORS bake).

### CR4 — Le détail existe mais à la MAUVAISE échelle de lecture (impact : moyen)
Armure quasi uniforme ~même taille → bruit homogène à distance ; réf = grandes plaques
identifiables aux épaules/dos + fines au cou. Muscles absents → corps « mou ».
→ FIX : gradient d'échelle beaucoup plus agressif (plaques héros 3-4x aux épaules/dos),
couche `muscles` (voronoi large orienté) dans bake surface.layers, plis mieux lisibles.

### CR5 — Métriques : compléter le juge (impact : process)
Ajouter au compare : distribution de luminance (percentiles p5/p50/p95 vs réf — capte le
contraste), et vérif visuelle A/B systématique à CHAQUE boucle contre step précédent
(« est-ce que ça a VRAIMENT changé ? ») avant tout STOP feedback.

### Trancher : wyverne vs dragon
Notre modèle EST déjà une wyverne (2 ailes + 2 pattes arrière, comme Drogon) — l'audit
externe s'est trompé en comptant 6 membres. Décision : WYVERNE, on ne change rien.

## Plan boucle 17 (vrais changements, ordre d'impact)
1. LOOK v3 charbon/rouge + rim dur + variation par instance (look-dev). CR1.
2. POSE vol dynamique + recalage ancres (shape-smith). CR2.
3. TÊTE v4 : mâchoires courbes, lèvres bruitées, dents/gencives v2, EyeBuilder (shape-smith). CR3.
4. Si budget : plaques héros + couche muscles dans le bake (CR4), luminance p5/p95 (CR5).
Chaque étape jugée d'abord en A/B visuel contre step_182, métriques ensuite.
