# Doctrine bake v1 — synthèse des 2 réponses externes (boucle 16)

Réponses intégrales collées par l'utilisateur dans la conversation (2026-07-10) ; points
convergents + décisions d'implémentation pour NOTRE pipeline (bpy 5.0 headless, spec-driven).

## Convergences des deux réponses
1. Étage HIGH-POLY TEMPORAIRE purement procédural : duplication du low-poly → voxel remesh
   dense (peau continue, 1-4M tris, hors budget rendu car jeté après) → détails en
   creux/bosses PAR DISPLACEMENT (écailles imbriquées, plis, veines), PAS en instances.
2. UV automatiques sur le LOW-poly seulement : smart_project + pack_islands (marge en px
   convertie en ratio) ; le high-poly n'a pas besoin d'UV (selected_to_active).
3. BAKE Cycles high→low : normal (tangent) = LA map de densité de bords perçue ; AO ;
   courbure (Pointiness→ColorRamp→EMIT) ; height/displacement en float pour les grands
   volumes. Marge + cage_extrusion à régler ; pas d'autosmooth sur le low après bake.
4. Réapplication : maps branchées dans le matériau du low-poly (normal → Principled,
   courbure/AO → masques patine/roughness — remplace la patine cavité « uniforme »).
5. Micro-détail perçu = stack : displacement réel (grandes formes) + normal bakée
   (moyennes) + bump multi-échelles procédural (micro) + masques courbure/AO.
6. Généricité : profils de surface (`surface_profile` par zone) + budgets/résolutions
   dans la spec ; les fonctions bpy ne connaissent que des types de pièces et des profils.

## Décisions pour notre implémentation (bx/bake.py)
- `spec['bake']` : liste de bake_groups {id, parts:[...], exclude_like:[...],
  maps:{normal:2048, ao:1024, curvature:1024}, margin_px, cage_extrusion, voxel,
  ao_samples, surface:{layers…}} — v1 : groupe `body` (mesh fusionné + tête ?
  commencer corps seul), les instances d'écailles GARDÉES par-dessus (grandes plaques),
  la peau continue micro vient de la normal map.
- High-poly : join des meshes du groupe (copies), remesh voxel (`voxel_size` dérivé du
  budget), displacement modifiers empilés pilotés par `surface.layers`
  (type: scales/wrinkles/veins/noise ; masques par axe/normale réutilisant _axis_factor,
  et `wrinkle_zones` génériques {loc, radius, freq, strength} pour les PLIS D'ARTICULATIONS
  aux ancres de la spec).
- PIÈGES Blender 5.0 : PAS de bake_type 'DISPLACEMENT' dans Cycles (height = bake EMIT
  d'un shader hauteur si besoin) ; bake NORMAL selected_to_active avec
  scene.render.bake.margin, cage_extrusion ; images normal/height en Non-Color ;
  height float_buffer=True ; uv ops exigent mode EDIT + objet actif ; AO cher → samples
  bornés (16-32) et résolution modérée ; use_clear=True.
- Assemblage : le builder matériau écailles/membrane accepte des slots de maps
  (normal_map, curvature_map, ao_map) qui SE MIXENT aux nœuds procéduraux existants
  (patine modulée par courbure bakée au lieu de Pointiness seul, plus fin).
- run.py : commande `bake <spec>` (produit renders/maps/*.png + spec_state) ; `forge`
  détecte les maps existantes et les branche (ou re-bake si --rebake).
- Ordres de grandeur v1 : high-poly ~1.5-2M tris, maps 2048 (normal) / 1024 (AO, curv),
  bake total visé < 10 min CPU conteneur, rendu final inchangé (~40 s).
