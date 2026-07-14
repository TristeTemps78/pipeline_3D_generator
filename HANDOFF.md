# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → CLAUDE.md, backlog → NEXT.md)

Reprise : CLAUDE.md → ce fichier, puis si l'utilisateur dit « continue », exécuter le
contrat ci-dessous sans reposer de question. EXÉCUTION 100 % LOCALE (Windows) :
`bash pipeline/blender_run.sh <cmd> <spec> [flags]` (Blender installé, bpy embarqué,
part ~4 s, HQ 5 shots ~2 min) — wheel bpy pip impossible (ARM64/Py3.14) ; conteneur
Linux = `bootstrap.sh` puis `python3 pipeline/run.py` comme avant.

## Où on en est
Verdict step_432 (2026-07-14) : « ça va toujours pas », AUCUNE amélioration perçue sur les
3 dernières boucles → les rustines sur l'assemblage de primitives ne convergent pas.
Feedback détaillé (verbatim en session) : tête = bloc biseauté à cavités (attendu : galet
plat type axolotl, sphère UV écrasée Z) ; museau coupé net (attendu : U très large sans
boolean) ; oreilles-sucettes tige+boule (attendu : plaques charnues coniques dans la
continuité du crâne) ; yeux au fond de grottes (attendu : EN SURFACE + paupière-plaque
par-dessus, supprimer le boolean) ; cou plus massif que la tête sans transition (attendu :
cou FIN < crâne, poitrail gonflé, affinement continu jusqu'à la queue) ; épines-aiguilles
(attendu : ailerons de requin plats arrondis, 2 rangées, scale décroissant) ; queue à
cassure nette (attendu : courbe lisse haute résolution) ; aileron = cônes flottants
(attendu : membrane = plane sculpté + solidify). Idée stratégique utilisateur RETENUE :
**Skin Modifier** sur squelette d'edges (rayon par vertex) = base organique soudée.
Historique : boucle 20 = switch **Krokmou** + virage SIMPLICITÉ ; boucle 21 rejetée
(step_400) ; boucle 22 « souder pas poser » (catmull_rom, weld boolean EXACT/TRANSFER,
horns.blade, socket_bevel, mouth_carve raycast BVH, globe_recess) rejetée (step_432).

## Contrat boucle 23 — « UNE SEULE PEAU » (refonte base mesh, EN COURS)
P0 CORPS : nouveau mécanisme générique skin-skeleton (squelette d'edges spec-driven :
colonne + membres branchés, modifier SKIN rayon par vertex, subsurf objet) = corps + cou +
queue + pattes en UN objet continu. Profil : cou nettement plus fin que le crâne, poitrail
massif, affinement régulier jusqu'au bout de queue, AUCUNE cassure d'angle.
P0 TÊTE : base = UV sphere écrasée Z / étirée XY (galet-axolotl), museau étiré en U large
SANS boolean (mouth_carve SUPPRIMÉ) ; yeux EN SURFACE orientés avant + paupières = plaques
courbes par-dessus (socket boolean SUPPRIMÉ) ; oreilles = cônes écrasés Z (plaques
triangulaires charnues, 2 grandes + 2 moyennes + pointes mâchoire) insérés à l'arrière du
crâne ; tête soudée au cou (weld EXACT existant).
P1 : épines dorsales = ailerons requin plats arrondis ×2 rangées, scale décroissant vers la
queue ; ailerons caudaux + prothèse = plane aux vertices sculptés en éventail + SOLIDIFY
(plus de cônes assemblés).
Règles du round : spec-driven générique, itérer en `part --fast` local, validate +
check.sh verts, HQ UNE fois en fin de boucle seulement.

## Restes hors contrat (reportés, ne pas redécouvrir)
Œil : lisibilité iris (croissant vert) — à rejuger APRÈS la refonte surface (le problème
venait de l'orbite creusée, supprimée en b23). Micro-relief musculaire dos (P1 guide b22).
Backlog : emblème blanc prothèse + selle/sangles (mécanisme décalque manquant) ;
catchlight ; découpage organic.py (si l'utilisateur lit ce code).

## Restes connus hors contrat
Cible = `references/krokmou_ref.md` ; la photo PNG doit être committée par l'utilisateur en
`references/krokmou_pose.png` pour réactiver `run.py compare` (réseau conteneur bloqué, et
session locale : à lui de la déposer). ~130-343 mesh non-manifold préexistants sans effet ;
scene.blend s'ouvre sur la caméra du dernier shot ; copper_fraction non pertinent (palette
noire) — juger luminance p5/p50/p95. Drogon archivé : `specs/dragon_got.json` + maps +
`renders/drogon_step297.blend`.
