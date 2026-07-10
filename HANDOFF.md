# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → claude.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → claude.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Boucle 16 close, **EN ATTENTE DE FEEDBACK** sur les shots HQ **step_182_hero/head/legs**
(jalons précédents : 172_* boucle 15, 161 post-volume). Doctrine :
`research/doctrine_bake_v1.md` (synthèse des 2 réponses externes).
Fait en boucle 16 :
- **Étage BAKE générique** (`bx/bake.py`, cmd `run.py bake <spec> [--fast]`) : shell
  high-poly TEMPORAIRE (voxel remesh ~1.3M tris) + couches `surface.layers`
  (scales/wrinkles/micro, masques numpy axe/normale, `wrinkle_zones` aux ancres) →
  UV auto low-poly (smart_project+pack, câblé dans build) → bake Cycles
  selected_to_active NORMAL 2048 / AO 1024 / COURBURE 1024 (Pointiness→EMIT) →
  `maps/<spec>_<groupe>_*.png` versionnées. **Bake total 45 s**, rendu inchangé ~39 s.
- Matériaux : `reptile_scales` accepte normal_map/ao_map/curvature_map (+strengths),
  mixés aux nœuds procéduraux ; patine modulée par courbure BAKÉE. Nouveau matériau
  `scales_body` sur le mesh fusionné.
- **BUG MAJEUR corrigé** : le mesh fusionné SDF gardait un slot matériau None → le corps
  rendait avec le matériau PAR DÉFAUT de Blender entre les plaques depuis la boucle 11
  (fix générique dans _apply_fuse_groups : materials.clear() avant assign).
- Métriques pleine qualité vs réf : cuivre .455 (réf .458 ✓), bords .2988 (réf .348) —
  la normal map bakée agit (crops A/B validés) mais le cadrage hero est dominé par
  l'armure instanciée/membrane, hors scope bake v1 (corps seul).

## Contrat boucle 17 (à recadrer selon feedback sur step_182_*)
1. Étendre le bake aux groupes `head` et `hindleg` (le gap bords est là : la peau bakée
   n'est visible que sur le corps nu) + tuning lisibilité des wrinkle_zones (doute agent).
2. Selon verdict couleur : recaler le look (le corps est plus PÂLE depuis le fix matériau
   None — c'était un gris sombre par défaut avant ; scales_body base/patina à foncer ?).
3. Restants NEXT item 0 : œil/iris gros plan, environnement caverne/canyon, cicatrices.

## Restes connus hors contrat
fuse_groups head/hindleg (armure spatiale prérequis) ; compare --fast sous-estime les
bords (denoise) — métrique toujours en pleine qualité ; `noise_scale` textures legacy :
plus PETIT = motif plus FIN (piège, documenté dans bake.py) ; scene.blend s'ouvre sur la
caméra du dernier shot ; front_extent root_follow_arm en dur.
