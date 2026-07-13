# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → CLAUDE.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → CLAUDE.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Hors boucle (2026-07-13, plainte coût tokens) : CLAUDE.md renommé (minuscule = pas
auto-chargé), `model: sonnet` AJOUTÉ au frontmatter des 4 agents (il manquait — chaque
délégation tournait sur le modèle cher), règles budget lecture/images dans CLAUDE.md,
audit.sh détecte renders non référencés + agents sans model, purge PNG 182/218/231/297/381.
Audit 2 (même jour, « trop compliqué, fluidifie ») : run.py factorisé (_begin/_end, table
COMMANDS, --help sans bpy, erreurs propres), orchestrator.md réaligné sur la cadence
SIMPLICITÉ (contradiction « max 3 itérations » supprimée) + économie dédupliquée vers
CLAUDE.md, CLAUDE.md restructuré (pièges en liste, métriques Drogon marquées archivées),
NEXT.md nettoyé (items Drogon archivés, « 2e créature » retiré : FAIT = Krokmou), README
réécrit (exemples Krokmou), note DOUTE résolue retirée de la spec, research/renders purgé.
Audit 3 (final) : `pipeline/check.sh` = QA statique 1 commande (~5 s, sans bpy) — c'est
L'AUDIT, ne pas ré-explorer à la main ; 3 fonctions mortes supprimées ; HISTORIQUE GIT
RÉÉCRIT avec accord utilisateur (402→20 Mo, vieux blends/PNG purgés, tip identique) et
miroité sur TOUTES les branches claude/* — tout clone antérieur doit être RE-CLONÉ ;
règle : blends committés aux JALONS seulement (cause de l'ancien gonflement).
Boucle 20 = SWITCH Drogon → **Krokmou** (Toothless, décision utilisateur) + virage
SIMPLICITÉ/RAPIDITÉ (feedback mi-boucle, directive permanente ajoutée à CLAUDE.md).
Boucle 21 exécutée en local, **verdict step_400 : « ne va pas du tout »** (2026-07-14) —
diagnostic structurel accepté : primitives POSÉES/disjointes au lieu de surfaces continues
soudées. Guide externe trié (verbatim + tri dans session.json step 400) → contrat boucle 22.
Pipeline 100 % local désormais : `bash pipeline/blender_run.sh <cmd> <spec>` (Blender installé,
bpy embarqué, part ~4 s) — plus besoin de conteneur ; wheel bpy pip impossible (ARM64/3.14).
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
  (pièce isolée ~20-30 s, `core.isolate` générique), directives CLAUDE.md.

## Contrat boucle 22 (verdict step_400 + guide externe trié — thème : SOUDER, pas POSER)
- **P0 QUEUE/AILERON** (« inacceptable ») : spine à interpolation LISSE (plus de coudes vifs
  entre pts — mécanisme générique, règle aussi le zigzag connu) ; aileron = UN objet soudé
  (boolean union os+membrane, PAS voxel) pénétrant la queue.
- **P0 TÊTE** : orbite = dépression ovoïde à bords ADOUCIS (pas trou net) ; arcade =
  plaque ENVELOPPANTE (large côté externe → fine vers le front, inclinée bas-extérieur) ;
  museau : aplat vertical + élargissement progressifs, profil U doux ; bouche = fente
  CARVÉE suivant le U (pas un fil) ; cornes = PLAQUES élancées courbées arrière à base
  large (pas des cônes), petites excroissances fusionnées au crâne.
- **P1 DOS** : épines = profils plats type écaille, taille/rotation variables le long de la
  spine (petites tête → grandes milieu) ; micro-relief musculaire léger (bruit sur le dos).
- REJETÉS : métaballes corps entier (refonte incompatible spec/écailles/maps) ; subsurf
  global fin de script (piège perf step_160) — lissage ciblé seulement.
- Rappels : Bézier+rayon variable = déjà `pts`/`radii` ; ancres absolues à recaler si la
  spine bouge ; membranes des ailes principales = NE PAS TOUCHER.

## Contrat boucle 21 — EXÉCUTÉ (round géométrie unique ; jugé : REJETÉ, cf. ci-dessus)
Fait : œil enfoncé (globe_r .16→.135, paupière inclinée via nouvelle clé générique
`eye.lid_upper_rot`), museau élargi ×2 (fini la proue), 2 cornes arrière + nubs
menton/mâchoire (`face_blobs`), earplates épaissies/balayées arrière (étaient des disques),
corps massif/cou fin (radii body .67→.75 max, .42→.20 côté tête) + dos bombé, base
tailfin_pros/nat pénétrant le tube de queue (sans fuse), doigts d'aile `finger_bow` .28→.38.
Annulés (non améliorants) : cornes spiky rise .85, earplate-hélice. validate = 0 mal posés.
RESTES à l'œil : cornes encore fines/pointues (power_taper finit à rayon ~0 — extension
builder si l'utilisateur les veut charnues) ; pincement possible à la jonction cou-tête
(radii .20 très fin) ; earplates à confirmer en HQ.
Contrat d'origine (feedback step_380, verbatim en session.json) :
Cadence SIMPLICITÉ : 1 round géométrie + 1 round look max avant de montrer ; HQ en fin seulement.
- **P0 TÊTE** (« le gros point noir », aspect mécanique/aplati) :
  a. Œil INTÉGRÉ : le crâne doit englober l'arrière du globe (aujourd'hui : sphère parfaite
     posée à l'extérieur + orbite « découpée » agressivement) ; arcade sourcilière = courbe
     fluide type paupière naturelle, pas plaque rigide posée dessus.
  b. Crâne = ellipsoïde APLATI (tête de salamandre/serpent) avec taper vers l'avant mais
     museau LARGE et ARRONDI — pas plat sur le dessus, pas de « proue de bateau ».
  c. Cornes/oreilles MANQUANTES : 2 grandes cornes principales à l'arrière + petites
     excroissances côtés/menton (aspect « axolotl »).
- **P1 COU/CORPS** : vraie distinction cou (fin) / corps (massif) — variation de rayon le
  long de la spine, dos légèrement bombé ; transition cou→tête pas un tube rigide.
- **P1 QUEUE/AILERON** (tailfin.png : pièces qui ne se touchent pas) : aileron prothétique
  DÉTACHÉ de l'axe de queue → faire pénétrer sa base dans le cylindre de queue. L'utilisateur
  suggère boolean union + remesh ; ATTENTION piège connu : pas de fuse voxel sur pièces fines
  (gonfle ×3) — préférer la pénétration géométrique simple.
- **P2 AILES** (point le MIEUX réussi — membranes plissées validées) : doigts = cylindres
  parfaits rigides → légère courbure vers l'arrière (chauve-souris).

Restes v1 NON couverts par ce feedback (backlog, ne pas redécouvrir) :
emblème blanc prothèse + selle + sangles (pas de mécanisme décalque) ; iris catchlight à
pousser ; zigzag anguleux entre points de spine (recouvre partiellement P1) ; découpage
d'organic.py en fichiers par type (à valider par l'utilisateur s'il lit ce code).

## Restes connus hors contrat
compare mesuré suspendu (pas de krokmou_pose.png) ; ~138-343 mesh non-manifold préexistants
sans effet ; scene.blend s'ouvre sur la caméra du dernier shot ; copper_fraction non
pertinent pour Krokmou (palette noire) — juger luminance p5/p50/p95 dans la créature.
