# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → CLAUDE.md, backlog → NEXT.md)

Reprise : CLAUDE.md → ce fichier, puis si l'utilisateur dit « continue », exécuter le
contrat ci-dessous sans reposer de question. EXÉCUTION 100 % LOCALE (Windows) :
`bash pipeline/blender_run.sh <cmd> <spec> [flags]` (Blender installé, bpy embarqué,
part ~4 s, HQ 5 shots ~2 min) — wheel bpy pip impossible (ARM64/Py3.14) ; conteneur
Linux = `bootstrap.sh` puis `python3 pipeline/run.py` comme avant.

## Où on en est — PIVOT « PIPELINE SCULPTEUR » (2026-07-16, validé utilisateur)

Diagnostic accepté : 3 jalons rejetés d'affilée (step_400/432/456) parce que l'ASSEMBLAGE
DE PRIMITIVES PARAMÉTRIQUES a un plafond de qualité pour l'organique — tourner des boutons
scalaires ne produira jamais une surface sculptée. Les services image→3D à crédits
(Meshy/Tripo) sont REJETÉS (exigence : gratuit + illimité). Garde-fous sautés, validés
par l'utilisateur :
1. Généricité-d'abord → code/données spécifiques Krokmou AUTORISÉS, généricité a posteriori.
2. Assemblage de primitives → CAGE basse résolution vertex-level + SUBSURF (méthode artiste).
3. Économie de regards → auto-critique visuelle haute fréquence (planches multi-vues à
   chaque micro-étape), utilisateur = jalons seulement.
4. Photo unique → VUES ORTHO de référence + score de silhouette (IoU) par vue.
5. Zéro asset externe → bases mesh CC0/CC-BY autorisées en point de départ ou étude.

Boucle 23 (skin_body/head_galet, rounds 1-3) : committée en checkpoint `48963ba`
(jalon step_456, jamais présenté) — état de REPLI, ne plus itérer dessus.

## Contrat boucle 24 — « SCULPTEUR v1 » (À DÉMARRER)

P0-A RÉFÉRENCES : ✅ FAIT (2026-07-16) — `references/krokmou_ortho_side.png` (profil
entier debout, fond blanc = cible IoU), `krokmou_ref_front34.png` (HQ 3/4, pas ortho),
`krokmou_anatomy_skeleton.png` (squelette profil = guide cage). ⚠ LOCALES et GITIGNORÉES
(© DreamWorks, push sur repo public bloqué — URLs de re-téléchargement dans
`references/krokmou_ref.md`) → `silh` et la cage ne se travaillent qu'en session LOCALE
tant que l'utilisateur n'a pas committé les PNG lui-même. Pas de vraie vue face/dessus
dans les renders officiels — métrique v1 = PROFIL seul. (Piste écartée : STL Thingiverse
TEXNOme = chibi assis, hors proportions film.)
P0-B MÉTRIQUE : EN COURS (interrompu fin de session 2026-07-16). Fait : plan approuvé
(voir ci-dessous), exploration = TOUT existe déjà dans `bx/feedback.py` — `silhouette()`
:89-101 (rendu ortho alpha), `mask_from_image()` :104-113, `iou(normalize=True)` :128-136
(bbox 256×256), `_save_png` :37-46 ; `run.py` dispatch dict `COMMANDS` :322-332, ajouter
`do_silh` après :226 ; `blender_run.sh` passthrough OK. Étape 1.1 en cours : décalque
polygone CORPS SEUL (sans ailes NI ailerons caudaux, pattes+oreilles incluses) sur la réf
→ état+points+mesures dans `references/krokmou_silh_trace.txt` (LOCAL, gitignoré) ;
correction identifiée : la queue sort BAS des hanches (x≈285) et court à y≈287-299,
ailerons = cluster x≥355 à exclure ; reste = mesurer ligne de dos x 150-290, corriger PTS,
générer `references/krokmou_ortho_side_body.png` (gitignoré). Ensuite : `do_silh` (~20 l. :
_begin clay → silhouette('side') → mask_from_image(body) → iou → print + delta persisté
`pipeline/state/silh.json` + planche réf|rendu|XOR `renders/silh.png` ; vérifier le SENS —
réf regarde à GAUCHE, fliplr si besoin).
P0-C CAGE : nouveau type de part `cage` — intégration explorée : `@builder('cage')` dans
organic.py après `ground` (:2150-2154, dispatch dict BUILDERS :15-22, signature
`(part, mats) -> [ob]`), mesh `from_pydata` (pattern ring_loft ops.py:174-199),
`core.subsurf(ob,2)` :25-28 + `core.shade_smooth` :18-22 existants, helper `core.mirror`
À CRÉER (aucun modifier MIRROR dans le repo) ; validate.py/check.sh : RIEN à modifier
(aucune vérif de type). Plan complet approuvé :
`~/.claude/plans/tranquil-frolicking-flask.md` (machine locale). Construire la cage Krokmou corps+cou+tête+queue
EN UNE SEULE PEAU (~100-250 verts posés un à un, symétrie X par miroir), en itérant :
éditer cage → planche 4 vues (~15 s) → auto-critique + score silhouette → répéter.
JALON de boucle = la silhouette de PROFIL colle à la réf (IoU ≥ ~0.90) — pas de détails,
pas de look. C'est le test « le plafond a-t-il sauté ».
P1 (si P0 convainc) : ailes/pattes/oreilles dans la MÊME cage (extrusions), ou plaques
cage séparées soudées à la construction (pas de boolean).
Règles du round : itérer en local (`blender_run.sh`), check.sh vert avant commit, HQ + 
planche UNE fois en fin pour présentation. Étude parallèle autorisée : chercher une base
mesh CC0 de dragon/quadrupède comme comparaison ou point de départ de cage.

## Restes hors contrat (reportés, ne pas redécouvrir)

Pari 30 min (fond de boucle, jamais bloquant) : TripoSR (MIT) sur CPU local — PyTorch a
des wheels Windows ARM64 natifs depuis 2025 ; si l'install passe, générer une ébauche
depuis la photo et la comparer à la cage. Œil : lisibilité iris — à rejuger sur la
nouvelle surface. Backlog : emblème blanc prothèse + selle/sangles (mécanisme décalque) ;
catchlight. ~130-343 mesh non-manifold préexistants sans effet ; scene.blend s'ouvre sur
la caméra du dernier shot ; copper_fraction non pertinent (palette noire). Drogon archivé :
`specs/dragon_got.json` + maps + `renders/drogon_step297.blend`.
