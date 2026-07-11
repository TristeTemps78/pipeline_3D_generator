# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → claude.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → claude.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Boucle 18 close, **EN ATTENTE DE FEEDBACK** sur **step_231_hero/head/legs** (HQ).
Lignée A/B conservée : step_182 (avant boucle 17) → step_218 (avant boucle 18) → step_231.
Fait en boucle 18 (2 agents Sonnet, feedback step_218 dans session.json) :
- AILES (point critique) : diagnostic « le détail existait mais ne lisait pas » —
  vein_dark≈base + bump couplé (→ vein_width/vein_bump découplés, veines sombres rouges),
  bone_mat=plaques délavées sur tubes fins (→ matériau wing_bone kératine dédié),
  horn spec_level .6 chromé sous rim fort (→ paramétré). + phalanges (knuckles_per_finger),
  ALULA avec micro-membrane et griffe (fix exclude_like fuse — piège récurrent), griffes
  de doigts ×2 recalibrées (r .065, rot 125/0/25 — à .12 elles rendaient des BOULES).
- TÊTE : masque générique `mask_near`/`mask_near_avoid` (zones par points) → couronne
  d'écailles GROSSES autour des orbites + ligne de mâchoire, armure fine écartée de ces
  zones ; œil : BUG émission uniforme iris_color sur toute la sphère (= disque doré) →
  émission suit la rampe, iris 2 tons, paupière couvrante ; dents : crocs dominants ×1.5
  + matériau `enamel` (gradient racine via UV.U) ; NARINES : cutter sous la surface
  (jamais percé) + mound qui l'engloutissait → recalés, visibles ; piques dorsales :
  spec_level .28 + base élargie + growth_rings.
- Scène 288k verts stable, tête 66.5k.

## Contrat boucle 19 (à recadrer selon feedback step_231)
Restes du feedback step_218 non traités : TORSION du corps entier (pose plus complexe —
spine ne supporte pas le twist axial, mécanisme à créer) + tension musculaire des pattes ;
CR4 de l'audit (plaques héros épaules/dos, couche muscles bake, bake étendu head/hindleg
avec exclude eye_/lid_) ; NEXT 0 : environnement caverne/canyon, cicatrices.
Doutes agents : piques encore « lames rétroéclairées » (contrainte lumières), alula fondue
dans le panneau (edge_color dédié ?), gradient enamel suppose racine→pointe.

## Restes connus hors contrat
copper_fraction peu fiable (juger via luminance p5/p50/p95, réf .082/.185/.715) ;
compare --fast sous-estime les bords ; ~175 mesh non-manifold préexistants sans effet ;
scene.blend s'ouvre sur la caméra du dernier shot ; fuse_groups head/hindleg bloqué.
