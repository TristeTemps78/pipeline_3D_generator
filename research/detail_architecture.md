# Architecture détail multi-échelle — convergence des 2 rapports (2026-07-08)

Réponse aux plafonds constatés (bords 0.19 vs 0.36, uniformité, anatomie absente, budget CPU).
Les deux rapports convergent sur une architecture EN 4 COUCHES, chacune pilotée par la spec JSON.
**À TESTER (session suivante, aucun test fait encore)** — plan de tests en bas.

## Couche 1 — MACRO : anatomie volumétrique sous la peau
Convergence forte : les lofts lisses n'offrent rien à la lumière. Solution :
- Primitives anatomiques paramétriques (muscles = capsules effilées, os = arêtes dures,
  gras = blobs mous) définies dans la spec (centerline, rayon, falloff).
- Voie A (rapport 2, préférée si bpy 5.x l'expose) : **SDF/OpenVDB** — `Mesh to SDF Grid`
  → `SDF Grid Boolean` (Union) → `SDF Grid Laplacian` (fascia/graisse) → `Grid to Mesh`
  (threshold 0, adaptivity>0) = corps étanche continu (règle aussi les 145 non-manifolds).
- Voie B (rapport 1, fallback) : primitives comme champs de déplacement par proximité
  (geometry proximity → displacement) sur le loft existant.
- Bonus : « coups de pinceau » codés (crease/inflate/scrape = courbe surface + falloff
  + amplitude) pour arcades, lignes de mâchoire, plans de crâne.

## Couche 2 — MESO : bibliothèques d'écailles par région + variation
Convergence forte : 1 seule plaque ×35k = artificiel. Solution :
- 3-8 ARCHÉTYPES de plaques par région (carénée triangulaire, plate losange, cornillon,
  scute large flanc, fine faciale) dans une collection → `Collection Info` (Separate
  Children) → `Instance on Points` avec **Pick Instance par index**.
- Index choisi par poids spatial (masques région/axes définis en JSON) + bruit ajouté
  AVANT l'arrondi entier → frontières de régions ditherées organiques (pas de lignes).
- Jitter par instance : taille/ratio/rotation bornés, biaisés le long des axes
  anatomiques (grand au dos, petit près des articulations), twist/skew léger.

## Couche 3 — MICRO : détail unique par instance à coût géométrique nul
Convergence exacte des 2 rapports (mécanisme clé) :
- `Store Named Attribute` domaine **Instance** (seed/coord unique par écaille) côté GN ;
- côté shader, node `Attribute` type **Instancer** → chaque instance échantillonne le
  bruit (Voronoi/Musgrave multi-octaves) à une origine différente → craquelures/pores/
  couleur uniques ×35k SANS réaliser les instances (pas d'explosion RAM).
- Displacement VRAI réservé aux zones héros en caméra ; bump/normal ailleurs.

## Couche 4 — BUDGET rendu CPU (piloté par la spec)
- **Adaptive subdivision en espace OBJET** (`adaptive_space='OBJECT'`,
  `adaptive_object_edge_length`) : subdivise l'archétype UNE fois puis instancie —
  évite l'explosion mémoire du mode PIXEL avec l'instancing (rapport 2, bpy 5.0 stable).
- Cycles : max bounces 6-8, diffuse 2-3, caustiques OFF, adaptive sampling threshold
  0.01-0.05, `use_persistent_data=True` (BVH caché entre itérations de la boucle).
- Fallback ultime : bake headless (temp_override) des instances → maps displacement
  EXR sur le mesh de base.

## Schéma de spec cible (extension progressive, rétro-compatible)
```json
"regions": {"skull": {"macro_anatomy": [...], "scale_archetypes": {"primary": "...",
  "ratio": [...], "noise_seed": 1}, "micro": {...}, "lod": {...}}}
```

## Plan de tests (research/tests/, AVANT de câbler dans organic.py)
- T10 : SDF pipeline dispo en bpy 5.0.1 headless ? (nodes SDF Grid) → sinon voie B proximity.
- T11 : 4 archétypes + Pick Instance par index + bruit de frontière, sur un tube — juger
  planche + edge_density vs armure actuelle.
- T12 : attribut Instance + Attribute('Instancer') dans le shader — vérifier unicité
  micro par instance au rendu, mesurer coût mémoire/temps.
- T13 : adaptive subdiv OBJECT sur un archétype instancié ×10k — temps de rendu vs fixe.
- T14 : throttling Cycles (bounces/adaptive/persistent_data) — chrono compare avant/après.
Ordre de câblage si tests OK : T14 (gratuit) → T11 (meso, gros gain visuel) → T12 (micro)
→ T10 (macro, le plus lourd) → T13.
