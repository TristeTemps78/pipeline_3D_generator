# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → claude.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → claude.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Boucle 17 close (« vrais changements » exigés après l'audit `research/audit_boucle17.md`),
**EN ATTENTE DE FEEDBACK** sur le A/B : **step_182_*** (avant) vs **step_218_*** (après,
HQ 3 shots). Jalons intermédiaires : step_195_* (CR1 look), step_208_head (CR3 tête).
Fait (3 agents Sonnet, dans l'ordre d'impact de l'audit) :
- CR1 LOOK charbon/rouge : base quasi-noire, arêtes rouge-cuivre, `instance_variation`
  par écaille, roughness contrastée .82/.24, fond noir + rim dur — les écailles LISENT
  enfin. + métrique CR5 : luminance p5/p50/p95 dans color_stats (réf .082/.185/.715).
- CR3 TÊTE v4 : courbure crocodilienne museau/mâchoire (loi `axis_flex`), lèvres
  bruitées génériques (`lip_profile`, remplace les ridges durs), dents inclinées seedées
  + gencive par dent, EyeBuilder (matériau `eye_globe` spéculaire, iris fente gradient,
  paupières aplaties, œil DÉSOCCLUS — il était caché par le crâne depuis toujours).
- CR2 POSE dynamique : virage bancé (overrides d'aile par côté `wing.pose.L/R`,
  génériques post-miroir), queue en S, cou tendu, tête yaw 9°, gape 56°, caméra roll 10°
  — TOUTES les ancres recalées (masks armure, throat, wrinkle_zones, head.loc).
- Maps rebakées pour la nouvelle pose (bake 52 s), HQ 3 shots ~2 min.
- Wyverne vs dragon : notre modèle EST une wyverne (2 ailes + 2 pattes) — décision : rien
  à changer, l'audit externe avait mal compté.

## Contrat boucle 18 (à recadrer selon feedback sur le A/B 182→218)
Restes de l'audit par impact : CR4 (plaques héros 3-4x épaules/dos, couche `muscles`
dans bake surface.layers, bake étendu à head/hindleg avec exclude eye_/lid_) ; doutes
agents : froissement aile haute en gros plan, throat non recalé en X pour le yaw,
lip_profile/œil à caler en HQ ; NEXT 0 restants : environnement caverne/canyon, cicatrices.

## Restes connus hors contrat
copper_fraction peu fiable (dominé par la couleur du rim — juger via p5/p50/p95) ;
compare --fast sous-estime les bords ; ~170 meshes non-manifold préexistants (dents/
griffes, sans effet visible) ; scene.blend s'ouvre sur la caméra du dernier shot ;
fuse_groups head/hindleg bloqué (armure spatiale prérequis).
