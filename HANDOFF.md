# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → claude.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → claude.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Boucle 20 = SWITCH Drogon → **Krokmou** (Toothless, décision utilisateur) + virage
SIMPLICITÉ/RAPIDITÉ (feedback mi-boucle, directive permanente ajoutée à claude.md).
**EN ATTENTE DE FEEDBACK** sur **step_380_hero/head/eye/wing/tailfin** (HQ, v1 Krokmou).
Drogon archivé : `specs/dragon_got.json` + maps + `renders/drogon_step297.blend` + jalons.

Cible = photo utilisateur transcrite dans `references/krokmou_ref.md` (pose couchée ailes
étalées, queue enroulée devant, prothèse rouge, yeux verts, fond blanc). La photo PNG
n'a PAS pu être téléchargée (réseau conteneur = registres seulement) → l'utilisateur doit
la committer en `references/krokmou_pose.png` pour réactiver `run.py compare`.

Fait en boucle 20 :
- GROUND : `specs/krokmou.json` (ref-analyst) — types existants seulement, ailerons
  caudaux = wing sans bras ; omis v1 : selle, sangles, emblème blanc prothèse.
- BUILD ×4 rounds (shape-smith) : pose au sol 32→0 mal posés ; bug générique corrigé
  (noms objets wing préfixés par id de part — collision entre parts wing multiples) ;
  queue continue ; bouche FERMÉE (gape 0, gum teinte peau) ; poitrail épaissi ; fils de
  bord de fuite supprimés ; fuse_groups RETIRÉ sur ailerons (mesuré : voxel≥.04 gonfle ×3
  les tubes fins, <.033 = mesh vide) → prothèse rouge lisible.
- LOOK (look-dev) : mécanisme générique `world visible_strength` (fond blanc caméra
  découplé du GI — peau noire pas noyée) ; cuivre Drogon décâblé de reptile_scales
  (paramètres exposés) ; eye_globe débogué (iris écrasé en bande → dist_round+dist_slit) ;
  fixes orchestrateur : iris vert acide, fond blanchi (visible_strength 1.9).
- CRITIQUE render-critic round 1 : NON PRÉSENTABLE (bouche ouverte langue rouge, serpent,
  prothèse absente, blob flottant) → tous les P0 traités en round 4 + micro-fixes.
  Round 2 de critique SAUTÉ (virage rapidité) — jugement orchestrateur seul sur step_380.
- SIMPLICITÉ : `docs/ARCHITECTURE.md` (carte stacks pédagogique), `run.py part <spec> <id>`
  (pièce isolée ~20-30 s, `core.isolate` générique), directives claude.md.

## Contrat prochaine boucle (À CADRER après feedback utilisateur)
Restes ASSUMÉS v1 Krokmou (connus, ne pas redécouvrir) :
1. Queue : zigzag anguleux au close-up tailfin (coudes vifs entre points de spine) ;
   ailerons = lames triangulaires plates, pas des nageoires organiques à bord arrondi.
2. Emblème blanc prothèse + selle + sangles cuir : omis v1 (pas de mécanisme décalque).
3. Ailes : bord de fuite encore un peu « découpé » au hero ; drapé perfectible.
4. Pointe/dard noir près de la tête au shot eye/head (earplate ou nub qui lit en lame).
5. Iris : vert acide obtenu mais catchlight/vivacité à pousser (photo très expressive).
6. Proposé à l'utilisateur (à valider) : découper organic.py (1854 l.) en un fichier par
   type de partie — SEULEMENT s'il veut lire ce code.

## Restes connus hors contrat
compare mesuré suspendu (pas de krokmou_pose.png) ; ~138-343 mesh non-manifold préexistants
sans effet ; scene.blend s'ouvre sur la caméra du dernier shot ; copper_fraction non
pertinent pour Krokmou (palette noire) — juger luminance p5/p50/p95 dans la créature.
