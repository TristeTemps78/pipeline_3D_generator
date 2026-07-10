# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → claude.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → claude.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Boucle 14 close, **EN ATTENTE DE FEEDBACK** : l'utilisateur rend en LOCAL (bpy) — un
`python3 pipeline/run.py forge specs/dragon_got.json` (sans --fast) sort désormais les
3 PNG HQ (hero / head / legs). Jalons fast de la boucle : **step_159_hero**,
**step_158_head**, **step_158_legs** (anciens jalons rejetés gardés : 133 deltaplane,
141 bras-en-lignes/nageoire ; fixes : 148 gros plan main, 151 vue).
Fait en boucle 14 (le feedback step_141 intégral est dans session.json) :
- Aile continuité (organic.py, générique) : `knuckle_spread` (doigts échelonnés + masse
  carpienne hand_ fusionnée SDF), `batten_start`, `root_follow_arm` (membrane sous le bras,
  fini la nageoire au flanc à z décalé).
- Multi-shots (run.py+feedback.py, générique) : `scene.shots` → 1 PNG/prise, cadrage AUTO
  bbox par pièce (`frame_part`/`dir`/`margin`/`lens`), `--shot <id>` pour isoler.
- Look (materials.py+core.py, générique, défauts rétro-compat) : patine cavité/arête sur
  reptile_scales (`patina_*`, `edge_copper`), veines+micro-plis membrane (`vein_*`,
  `wrinkle_*`, transmission bornée ≤.05 en dur), builder `horn` kératine (clé mat `bone`),
  fond monde `variation` + volume bruité (poussière). Métriques : cuivre .63→.471 (cible
  .45-.50 ✓), bords .21→.233 (cible finale .35 = géométrie fine à venir).

## Contrat boucle 15 (à recadrer selon feedback sur les rendus HQ locaux)
Roadmap utilisateur restante = NEXT.md item 0 : (a) écailles par zones + plis articulations
`fold_rings`, (b) tête fine (iris fente, narines, gencives/dents, rides), (c) micro-plis
membrane niveau 2, (d) cicatrices, (e) environnement caverne/canyon détaillé. Prioriser la
DENSITÉ DE BORDS (gap .233→.35) = géométrie détail, via agents Sonnet + mécanismes génériques.

## Restes connus hors contrat
fuse_groups head/hindleg bloqué (NEXT item 2, prérequis armure spatiale) ; œil composite
jamais validé en gros plan couleur (le shot head le cadre désormais — vérifier au feedback) ;
scene.blend s'ouvre avec la caméra du DERNIER shot rendu (legs) ; `front_extent=0.5` de
root_follow_arm en dur dans le builder (à exposer si autre gabarit d'aile).
