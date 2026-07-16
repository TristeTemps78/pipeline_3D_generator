# ARCHITECTURE — la carte pour lire ce projet (pédagogique)

Écrit suite au feedback utilisateur (boucle 20) : « je suis perdu, on m'a conseillé de
découper la pipeline en stacks et modules, je veux inspecter les pièces et itérer vite ».
Bonne nouvelle : le code EST déjà découpé en modules (~6 100 lignes en tout). Ce qui
manquait, c'est cette carte, et un mode d'inspection rapide pièce par pièce (`part`).

## La vue « stacks » (5 étages, de l'idée à l'image)

```
  TA PHRASE / TA PHOTO
        │
        ▼
 ┌─────────────────┐   agent ref-analyst
 │ 1. GROUND        │──► écrit specs/<créature>.json      ← LA SOURCE DE VÉRITÉ
 │ (comprendre)     │       (aucun code, que du JSON)
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   bx/ops.py      → briques bêtes : tube, blob, ring, grille
 │ 2. BUILD         │   bx/organic.py  → assemble les briques en ANATOMIE :
 │ (géométrie)      │       spine (corps), head, wing, limb, dewlap…
 │                  │   bx/detail.py   → relief : écailles plaquées, displace
 │                  │   bx/fuse.py     → soude les morceaux (voxel/SDF)
 │                  │   bx/validate.py → contrôle SANS rendu (BVH, sol, collisions)
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   bx/materials.py → shaders : peau, membrane, corne, œil
 │ 3. LOOK          │   bx/bake.py      → maps normal/AO/courbure (high→low)
 │ (matière+lumière)│   bx/core.py      → scène : caméra, lumières, monde, rendu
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   pipeline/run.py → le CHEF D'ORCHESTRE (1 commande par action) :
 │ 4. RENDER        │       forge, clayhero, part, sheet4, bake…
 │                  │       `python3 pipeline/run.py --help` les liste toutes
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   bx/feedback.py → mesures : compare à la réf, bbox par pièce,
 │ 5. EVALUATE      │       planches-contact ; + agent render-critic (œil neuf)
 └─────────────────┘
```

Règle d'or historique : **le JSON de spec pilote tout, le code ne connaît aucune
créature**. AMENDÉE au pivot 2026-07-16 (« pipeline sculpteur ») : le travail au niveau
vertex spécifique à une créature est désormais AUTORISÉ — la spec porte des données de
cage (vertices/faces/creases) propres à Krokmou, et la généricité s'extrait a posteriori
des techniques qui marchent, au lieu d'être imposée d'avance.

## PIVOT boucle 24 — « pipeline sculpteur » (2026-07-16)

Pourquoi : 3 jalons rejetés d'affilée (step_400/432/456) — l'assemblage de primitives
paramétriques (tubes, booleans, skin modifier) a un plafond de qualité pour l'organique.
Nouvelle méthode, celle des artistes : **cage basse résolution + Subdivision Surface**.
- `bx/cage.py` (à créer, b24) : part type `cage` — maillage grossier (~100-250 vertices
  posés explicitement, symétrie X) lu depuis la spec, + Subsurf ×2 = surface organique
  continue, UNE seule peau sans boolean ni soudure.
- Cible mesurable : vues ortho de référence (`references/krokmou_ortho_*.png`) + score
  de **silhouette** (IoU rendu ortho vs réf, dans `bx/feedback.py`, cmd `run.py silh`).
- Boucle interne : éditer cage → planche 4 vues (~15 s) → auto-critique + score → répéter,
  des dizaines de fois AVANT de montrer quoi que ce soit à l'utilisateur.
- Bases mesh CC0/CC-BY autorisées comme point de départ ou comparaison.
Les types `skin_body`/`head_galet` ci-dessous (boucle 23) restent documentés comme état
de REPLI (checkpoint `48963ba`) — ne plus itérer dessus.

## Qui fait quoi (fichier par fichier, du plus simple au plus gros)

| Fichier | Lignes | Rôle en une phrase |
|---|---|---|
| `pipeline/run.py` | ~335 | CLI : lit la spec, appelle les étages, écrit les PNG. `--help` liste tout. **Commence ta lecture ici.** |
| `bx/validate.py` | 127 | « Est-ce que la géométrie est saine ? » sans dépenser un rendu. |
| `bx/fuse.py` | 167 | Soude des groupes d'objets en un seul mesh (voxel/SDF). |
| `gvl/laws.py` | 201 | Petites lois de croissance réutilisables (anneaux de corne, spirales…). |
| `bx/ops.py` | 276 | Les briques géométriques de base. Aucune intelligence, juste des formes. |
| `bx/core.py` | ~380 | La scène : caméra, lumières, monde, clay, rendu, save .blend. |
| `bx/bake.py` | 440 | Fabrique les maps de détail (normal/AO) d'un coup, pour rendre vite ensuite. |
| `bx/feedback.py` | 567 | Tout ce qui MESURE : bbox par pièce, comparaison à la réf, planches. |
| `bx/detail.py` | 732 | Écailles/reliefs plaqués sur les surfaces. |
| `bx/materials.py` | 1078 | Les shaders (peau reptile, membrane, œil…). Gros mais indépendant. |
| `bx/organic.py` | ~2100 | LE gros morceau : transforme chaque entrée `parts[]` de la spec en anatomie. Lis-le partie par type (`spine`, `head`, `wing`, `limb`, `skin_body`, `head_galet`) — chaque type est une fonction. |

### Boucle 23 « UNE SEULE PEAU » — squelette SKIN + tête sans booléen (Krokmou)

Deux nouveaux types de partie, en remplacement de `spine`+`head` pour Krokmou (les
anciens types restent dispo pour d'autres créatures) :
- `skin_body` : squelette réel (mesh vertices+edges, PAS une NURBS) — colonne
  vertébrale + membres branchés (`limbs[]`, attache AUTO au vertex de spine le plus
  proche) — porté par un modifier `SKIN` (rayon PAR VERTEX, `bm.verts.layers.skin`)
  puis lissé par Subdivision Surface. UN SEUL objet continu corps+cou+queue+pattes.
  `smooth` réutilise `laws.catmull_rom` mais avec une DÉCIMATION ADAPTATIVE
  (`_densify_chain`) : le modifier SKIN a besoin d'arêtes plus longues que le rayon
  local, sinon les anneaux se chevauchent et ça se lit comme des « ailerons » en
  éventail (bug mesuré) — la densification retombe donc naturellement là où le
  rayon est grand (torse) et reste fine là où il est petit (cou, queue).
- `head_galet` : crâne = UV sphere écrasée/étirée puis museau = étirement
  proportionnel des vertices avant (pas de découpe). Yeux posés EN SURFACE
  (`_ellipsoid_surface`, calcul analytique) + 1 paupière-plaque par œil. Oreilles =
  `ops.spike(flatten=..., tip_frac=...)` (cônes écrasés à pointe émoussée),
  liste générique `ears[]`.
- `weld_groups` (clé top-level de la spec, générique) : soude en un seul mesh
  (`ops.boolean_union`, EXACT+TRANSFER) les groupes de parts listés, hors motifs
  `exclude_like` — utilisé pour souder `head_galet` à `skin_body` sans booléen dans
  le builder lui-même (`_apply_weld_groups`, même schéma que `fuse_groups` mais
  boolean exact au lieu de SDF voxel). Piège : un objet consommé par le weld perd
  son nom d'origine (`classify_object` par préfixe) → un `scene.shots[].frame_part`
  qui le ciblait doit passer à `frame_match` (sous-chaînes de nom, ex. `eye_`/`lid_`).
- `limb.skip_tube` (bool) : ne construit que pied/orteils/griffes, le volume de la
  patte étant porté par une branche `skin_body.limbs` (évite un double tube).

### Boucle 23 round 2 — ancrage des appendices tête, crête dorsale, ailerons plats

- `head_galet.ears[].dir`/`tilt`/`embed_frac` (remplace le `pos`/`rot` brut, resté
  dispo en repli) : ancre la BASE de chaque plaque d'oreille sur la surface réelle
  du crâne (`_ellipsoid_surface`, même calcul que les yeux) au lieu d'un point posé
  à la main qui dérivait facilement en l'air (bug mesuré : nub flottant sous le
  museau). La base est enfoncée de `embed_frac*height` le long de la normale locale
  -> la plaque prolonge la coque au lieu de flotter dessus.
- `_dorsal_spikes` (nouvelle fonction partagée, `spine` ET `skin_body.spikes`
  l'appellent — même mécanisme, pas de copie) : `rows` (nb de rangées, défaut 2),
  `shape:'fin'` (triangle court/large/arrondi type aileron de requin, vs `'blade'`
  = profil historique long/fin), `up_bias` (0..1, défaut 0 rétro-compat) — mélange
  la normale "suit la courbure" avec un vrai vertical fixe : sur `skin_body`, une
  colonne qui monte/descend beaucoup (poitrail bombé) rend la perpendiculaire pure
  presque horizontale -> les piques se couchent à plat (bug mesuré, bbox du groupe
  ne dépassait quasi pas la coque) ; `up_bias>0` corrige.
- `wing.skip_bones`/`edge_ridge_height` (fix « ailerons caudaux = assemblage de
  cônes ») : `skip_bones=true` ne construit plus les tubes os séparés (arm/hand/
  finger/wclaw) — seulement la membrane (déjà une plane en éventail, `grid_surface`
  + `col_pts`). `edge_ridge_height` bombe directement les colonnes "doigt" de la
  membrane (renflement du MÊME mesh) pour simuler la nervure, au lieu d'un tube qui
  se lisait comme un cône rond posé sur le bord de la plaque.
- Piège transversal (weld_groups) : tout objet créé dans un groupe soudé
  (`weld_groups[].parts`) qui ne doit PAS être fusionné (oreilles, piques
  dorsales…) a besoin d'un motif dans `exclude_like` (ex. `_spike_`) — sinon un
  booléen EXACT à 40+ opérandes minces peut produire un mesh corrompu (mesuré :
  torso+tête entièrement disloqués après ajout des piques avant ce fix).

### Boucle 23 round 3 — ancrage réel des ailerons caudaux (`wing.root_curve`), taper des piques

- Piège mesuré (`wing` avec `skip_bones:true`, cf. round 2) : sans `root_curve`,
  la racine de la membrane (`col_pts`) reste un point UNIQUE fixé au `wrist` —
  pour un petit aileron dont `shoulder` est proche du corps mais `wrist` est déjà
  loin dans le vide (c'était l'extrémité de l'os `arm`, supprimé par
  `skip_bones`), toute la membrane part d'un point qui flotte à ~0.4 unité du
  corps -> lu comme un « assemblage de pièces posées », pas une greffe. Fix :
  `root_curve` (mécanisme existant, ex-« aile nageoire ») avec un premier point
  choisi explicitement SUR la ligne centrale du corps porteur (pas juste
  `shoulder`, qui peut être quasi au bout d'une pointe fine qui se réduit
  fortement au modifier SKIN+Subsurf) -> la racine de la membrane traverse
  réellement le volume solide au lieu de l'effleurer.
- `_dorsal_spikes.tail_taper` (0..1, défaut 0 rétro-compat) : l'enveloppe `env`
  (sin(pi·t)) ne redescend presque pas dans la plage utile de la crête quand son
  pic tombe près de `end_frac` -> piques quasi uniformes (« peigne rectangulaire »
  au lieu de petits ailerons dégressifs). `tail_taper` ajoute une décroissance
  linéaire explicite le long de l'index de la crête, par-dessus `env`.

## Inspecter les pièces (le mode rapide que tu voulais)

```bash
# UNE pièce isolée à l'écran, cadrée auto, ~20-30 s :
python3 pipeline/run.py part specs/krokmou.json head --fast
python3 pipeline/run.py part specs/krokmou.json tailfin_pros --fast
python3 pipeline/run.py part specs/krokmou.json wing --fast --clay   # géométrie nue

# ids disponibles = champ "id" de chaque entrée parts[] de la spec
# (le message d'erreur les liste si tu te trompes)

# Toute la bête, vite :
python3 pipeline/run.py clayhero specs/krokmou.json --fast    # géométrie seule, ~30 s
python3 pipeline/run.py forge specs/krokmou.json --fast       # avec matériaux, ~1-3 min
python3 pipeline/run.py sheet4 specs/krokmou.json --fast      # 6 vues + couleur par pièce, 1 PNG

# Sans AUCUN rendu (instantané) :
python3 pipeline/run.py inspect specs/krokmou.json    # JSON : pièces, tailles, sommets
python3 pipeline/run.py validate specs/krokmou.json   # santé géométrique
```

Le HQ (`forge` sans `--fast`, ~6 min) ne sert QUE pour te présenter un résultat.

## Pourquoi ça t'a semblé compliqué (diagnostic honnête)

1. **Le process, pas le code** : les boucles orchestrateur→agents→critique→rendus HQ
   prennent des heures et produisent des commits denses. Le code, lui, tient en 11
   fichiers. → Nouveau réglage : boucles COURTES (1 round géométrie + 1 round look max),
   HQ et critique seulement quand on te présente quelque chose.
2. **2 fichiers concentrent la moitié du code** (`organic.py`, `materials.py`). C'est le
   prochain découpage utile si on va plus loin : `organic.py` → un fichier par type de
   partie (spine.py, head.py, wing.py, limb.py). À faire SI tu veux lire ce code-là.
3. **L'état est éclaté en 3 fichiers** (CLAUDE.md = règles, HANDOFF.md = état courant,
   NEXT.md = backlog). C'est voulu (sessions éphémères) mais il faut le savoir.

## Ta boucle de travail recommandée (rapide)

1. Ouvre `specs/krokmou.json`, change UNE valeur (ex. un rayon, une couleur).
2. `python3 pipeline/run.py part specs/krokmou.json <la_pièce> --fast` → 20-30 s.
3. Content ? `forge --fast` pour voir l'ensemble. Pas content ? git checkout de la spec.
4. Les `renders/scene.blend` (+ `scene_prev.blend`) s'ouvrent dans TON Blender local
   pour tourner autour du modèle en 3D temps réel — souvent plus parlant qu'un PNG.
