# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → CLAUDE.md, backlog → NEXT.md)

Reprise : CLAUDE.md → ce fichier, puis si l'utilisateur dit « continue », exécuter le
contrat ci-dessous sans reposer de question. EXÉCUTION 100 % LOCALE (Windows) :
`bash pipeline/blender_run.sh <cmd> <spec> [flags]` (Blender installé, bpy embarqué,
part ~4 s, HQ 5 shots ~2 min) — wheel bpy pip impossible (ARM64/Py3.14) ; conteneur
Linux = `bootstrap.sh` puis `python3 pipeline/run.py` comme avant.

## Où on en est
Boucle 22 EXÉCUTÉE en local (2026-07-14) — **EN ATTENTE DE FEEDBACK sur step_432_* (HQ)**.
Historique : boucle 20 = switch Drogon→**Krokmou** + virage SIMPLICITÉ (boucles courtes,
réponses pédagogiques) ; boucle 21 (œil enfoncé, museau élargi, cornes+nubs, corps
massif/cou fin, tailfins pénétrant la queue, finger_bow) jugée step_400 : « ne va pas du
tout » — diagnostic structurel : primitives POSÉES/disjointes au lieu de surfaces continues
soudées (guide externe trié, verbatim + tri en session.json step 400 ; rejets motivés :
métaballes corps entier, subsurf global).
Boucle 22 (thème SOUDER, PAS POSER), 1 gros round shape-smith + 1 round finition + micro-fixes :
- Spine LISSE générique : `laws.catmull_rom`, clé `smooth`/`profile_smooth` (body/tail/head)
  — zigzag queue et cou rigide réglés, transition crâne→museau adoucie.
- Aileron = UN mesh soudé : `ops.boolean_union` EXACT + clé `wing.weld` (bug corrigé :
  modifier Boolean perd les matériaux par défaut → `material_mode='TRANSFER'`) ; prothèse
  dans l'axe de la queue. LE gain le plus net du round.
- Cornes = PLAQUES courbées/torsadées : `ops.tube(flat=, tilts=)`, clé `horns.blade` ;
  épines dorsales aplaties (`spikes.flat`).
- Orbite adoucie : `ops.boolean_diff(bevel_width=)`, clé `eye.socket_bevel` ; arcade
  sourcilière en spec seule (`head.ridges[brow]`, mécanisme existant étendu flat/twist).
- Bouche = fente carvée continue : `mouth_carve` + cutter positionné par RAYCAST BVH sur la
  surface réelle (plus d'estimation analytique faussée par `exp`) ; `lip_profile` RETIRÉ de
  la spec (le bourrelet-tube lisait comme un fil détaché, redondant avec la fente).
- Œil : `eye.globe_recess` (nouvelle clé, défaut 0 rétro-compat) = globe enchâssé ;
  compromis final 0.02 après essais 0.04/0.07/0.10 (plus = iris illisible).
validate : 0 mal posés ; check.sh vert (+ fix encodage UTF-8 console Windows).

## Contrat prochaine boucle (À CADRER après feedback utilisateur sur step_432)
Restes CONNUS boucle 22 (ne pas redécouvrir) :
1. ŒIL : lisibilité insuffisante au shot eye — le vert n'apparaît qu'en croissant malgré
   look_dir ≈ axe caméra ; occlusion par rebord d'orbite/arcade/paupière. 4 micro-essais
   arrêtés (règle anti-spirale). Piste : coupler `globe_recess` à un raycast surface (comme
   la bouche), ou réduire socket_r/brow radii près de l'œil. C'était l'élément identitaire
   n°1 — probable P0 du prochain feedback.
2. Ailerons caudaux : soudés et dans l'axe, mais toujours des LAMES triangulaires plates —
   pas des nageoires organiques à bord arrondi (reste hérité v1).
3. Arcade sourcilière : trop subtile pour lire à l'échelle des shots (jugement agent).
4. Épines dorsales plates : correctes mais petites.
5. Micro-relief musculaire du dos : NON fait (P1 du guide, pas de mécanisme displace léger
   adapté — à trancher).
Backlog inchangé : emblème blanc prothèse + selle + sangles (pas de mécanisme décalque) ;
catchlight à pousser ; découpage organic.py par type (si l'utilisateur lit ce code).

## Restes connus hors contrat
Cible = `references/krokmou_ref.md` ; la photo PNG doit être committée par l'utilisateur en
`references/krokmou_pose.png` pour réactiver `run.py compare` (réseau conteneur bloqué, et
session locale : à lui de la déposer). ~130-343 mesh non-manifold préexistants sans effet ;
scene.blend s'ouvre sur la caméra du dernier shot ; copper_fraction non pertinent (palette
noire) — juger luminance p5/p50/p95. Drogon archivé : `specs/dragon_got.json` + maps +
`renders/drogon_step297.blend`.
