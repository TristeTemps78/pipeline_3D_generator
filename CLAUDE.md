# Pipeline 3D — Claude + Blender (bpy headless)

## But & directives permanentes (utilisateur, 2026-07-08 ; PIVOT 2026-07-16)
- BUT (pivot « PIPELINE SCULPTEUR », 2026-07-16) : modèles 3D PREMIUM par moyens GRATUITS
  et ILLIMITÉS (services à crédits type Meshy/Tripo REJETÉS par l'utilisateur). Constat :
  l'assemblage de primitives paramétriques a plafonné (jalons 400/432/456 rejetés, b21-23).
  Méthode = modéliser comme un artiste : CAGE basse résolution au niveau vertex + subsurf
  (une seule peau par construction), jugée contre des VUES ORTHO de référence (score de
  silhouette), avec auto-critique visuelle haute fréquence. Code/données SPÉCIFIQUES à la
  créature AUTORISÉS — la généricité s'extrait A POSTERIORI des techniques qui marchent.
  Bases mesh CC0/CC-BY autorisées comme point de départ. La spec JSON reste le véhicule
  (elle peut porter une cage : vertices/faces/creases).
- ÉCONOMIE : l'orchestrateur délègue le gros du travail à des agents SONNET (`model: sonnet`
  imposé dans le frontmatter de `.claude/agents/*.md` — vérifier qu'il y reste) ; auto-audit
  régulier via `bash pipeline/audit.sh`. Budget lecture : boot session = CLAUDE.md (auto) +
  HANDOFF.md, RIEN d'autre ; gros fichiers (bx/organic.py, materials.py, specs) JAMAIS en
  Read complet — Grep ciblé/offset, spec éditée par patchs ; images : depuis le pivot,
  l'AUTO-critique visuelle est le moteur (regarder des rendus multi-vues rapides à chaque
  micro-étape, en local part ~4 s) MAIS en planches assemblées (1 image lue = 4-6 vues),
  jamais N PNG séparés ; pour l'UTILISATEUR : jalons seulement ; rendu HQ = long → le
  lancer UNE fois en fin de boucle, pas au milieu d'allers-retours (chaque pause >5 min
  casse le cache de prompt et refacture tout le contexte).
- COMPACITÉ : dossier léger — purger les renders sauf jalons référencés, logs compacts,
  CLAUDE.md court. Conseil clone local léger : `git clone --depth 1`.
- BLENDS : toujours garder les 2 derniers modèles ouvrables (`renders/scene.blend` +
  `renders/scene_prev.blend`, rotation auto dans run.py) pour le Blender local de l'utilisateur.
- SIMPLICITÉ/RAPIDITÉ (feedback 2026-07-13, mi-boucle 20 — l'utilisateur était PERDU) :
  boucles COURTES (1 round géométrie + 1 round look max avant de montrer), HQ et
  render-critic réservés à la présentation, réponses pédagogiques (il apprend).
  Carte de lecture du projet : `docs/ARCHITECTURE.md` (vue stacks) — à maintenir.
  Inspection pièce par pièce : `run.py part <spec> <id> --fast` (~20-30 s).

## État courant
JAMAIS ici : tout l'état (boucle en cours, dernier feedback, contrat, restes) vit dans
`HANDOFF.md` — seul fichier à lire après celui-ci. Backlog long terme : `NEXT.md`
(à lire seulement au cadrage d'une boucle). Protocole : `pipeline/orchestrator.md`.
Cible visuelle : `references/krokmou_ref.md` (Krokmou/Toothless, depuis boucle 20 ;
Drogon archivé : spec+maps+`renders/drogon_step297.blend`, réfs `references/drogon_*.png`).

## Pièges appris (chèrement — ne pas redécouvrir)
- Armure = Separate Components sinon OOM.
- Object Info ORIGINAL ignore le transform objet.
- Couronne : angle X POSITIF = bascule arrière.
- Transmission sur coque fine + lumières fortes = taches blanches transmises (mettre 0 ou masquer).
- `_axis_factor` (masks/grads armure) travaille en coordonnées locales == monde SEULEMENT
  si l'objet est à l'origine.
- Détail tête : plaques trop grosses/soulevées = « gravier » qui noie la sculpture
  (scale ~.02-.05 à l'échelle d'un crâne de 2u).
- VOLUME SCATTER mondial (brume/poussière) = rendu ×30-100 sur CPU (2h chez l'utilisateur) —
  atmosphère par dégradé+variation du fond, volume réservé GPU et jamais par défaut.
- Blobs quasi sphériques pour chair pendante = interdit (rend en œufs) : aplatir (ratio ≤0.5/2.7/0.8).
- voxel fuse ≥.04 gonfle ×3 les tubes fins (r~.05), <.033 = mesh vide → pas de fuse sur pièces fines.

## Métriques
SIGNAL PRINCIPAL (pivot sculpteur) : score de SILHOUETTE par vue ortho (IoU rendu vs
`references/krokmou_ortho_<face|side|top>.png`) — dense, mesurable, optimisable sans
attendre le feedback utilisateur. `run.py compare` (planche réf|rendu + deltas) en appoint.
Krokmou (noir sur fond blanc) : copper_fraction NON pertinent — juger luminance p5/p50/p95
dans la créature + densité de bords. (Cibles Drogon archivées : couleur (0.33,0.27,0.26),
cuivre .42, bords .36 ; priorité utilisateur = densité de détail, pas la couleur.)

## Règles
- Spec = source de vérité (`specs/krokmou.json`), y compris les données de cage (vertex-level
  spécifique-créature OK depuis le pivot). Jamais de bpy brut hors `pipeline/bx/`.
- Géométrie d'abord (clay), look ensuite. Chaque pas jugé par métrique + œil ; pas non améliorant → annulé.
- Corps/tête/membres = UNE cage subsurf continue ; écailles/détail = GÉOMÉTRIE plaquée
  (`detail.armor`) par-dessus, pas du bruit, et pas de boolean dans les formes organiques.
- Éditions par petits patchs ; --fast pour itérer, HQ pour présenter ; CLAUDE.md court.

## Cmds & modules
`bash pipeline/check.sh` = QA statique en 1 commande (~5 s, sans bpy : compile + cohérence
specs + audit) — à lancer AVANT tout commit, et c'est l'AUDIT : ne pas ré-explorer à la main.
`bash pipeline/bootstrap.sh` (conteneur neuf) puis `python3 pipeline/run.py --help`
(forge/part/clayhero/sheet/sheet4/compare/validate/inspect/bake — part = inspection d'UNE
pièce ~20-30 s ; validate/inspect = zéro rendu). Carte des modules bx : `docs/ARCHITECTURE.md`.
À TENIR À JOUR en codant : `fuse.exclude_like` pour tout nouveau motif d'objet ;
`materials` ignorés en clay ; GVL (`pipeline/gvl/`) pour toute nouvelle loi de croissance.

## Git
`main` = LA référence unique (source de vérité). L'hébergeur impose une branche `claude/*`
par session : y travailler, puis après CHAQUE push miroiter la pointe sur main
(`git push origin HEAD:main`, fast-forward seulement — refus = une autre session a avancé :
`git fetch` + rebase d'abord). Boot session : partir de `origin/main`, pas d'une vieille
`claude/*`. Les branches `claude/*` sont JETABLES une fois miroitées — ne pas en accumuler.
Commit par étape de boucle, push + état AVANT fin de session (conteneur éphémère).
BLENDS : ne committer `renders/scene*.blend` qu'aux JALONS (présentation/fin de boucle),
jamais à chaque étape — c'est ce qui a gonflé le .git à 400 Mo (~12 Mo d'historique par
commit de blends). `git add` explicite, pas de `git add -A` aveugle sur renders/.
