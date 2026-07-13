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
 ┌─────────────────┐   pipeline/run.py → le CHEF D'ORCHESTRE (301 lignes, 1 commande
 │ 4. RENDER        │       par action) : forge, clayhero, part, sheet4, bake…
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   bx/feedback.py → mesures : compare à la réf, bbox par pièce,
 │ 5. EVALUATE      │       planches-contact ; + agent render-critic (œil neuf)
 └─────────────────┘
```

Règle d'or qui tient tout : **le JSON de spec pilote tout, le code ne connaît aucune
créature**. `dragon_got.json` et `krokmou.json` passent dans exactement le même code.

## Qui fait quoi (fichier par fichier, du plus simple au plus gros)

| Fichier | Lignes | Rôle en une phrase |
|---|---|---|
| `pipeline/run.py` | ~340 | CLI : lit la spec, appelle les étages, écrit les PNG. **Commence ta lecture ici.** |
| `bx/validate.py` | 127 | « Est-ce que la géométrie est saine ? » sans dépenser un rendu. |
| `bx/fuse.py` | 167 | Soude des groupes d'objets en un seul mesh (voxel/SDF). |
| `gvl/laws.py` | 201 | Petites lois de croissance réutilisables (anneaux de corne, spirales…). |
| `bx/ops.py` | 276 | Les briques géométriques de base. Aucune intelligence, juste des formes. |
| `bx/core.py` | ~380 | La scène : caméra, lumières, monde, clay, rendu, save .blend. |
| `bx/bake.py` | 440 | Fabrique les maps de détail (normal/AO) d'un coup, pour rendre vite ensuite. |
| `bx/feedback.py` | 567 | Tout ce qui MESURE : bbox par pièce, comparaison à la réf, planches. |
| `bx/detail.py` | 732 | Écailles/reliefs plaqués sur les surfaces. |
| `bx/materials.py` | 1078 | Les shaders (peau reptile, membrane, œil…). Gros mais indépendant. |
| `bx/organic.py` | 1854 | LE gros morceau : transforme chaque entrée `parts[]` de la spec en anatomie. Lis-le partie par type (`spine`, `head`, `wing`, `limb`) — chaque type est une fonction. |

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
3. **L'état est éclaté en 3 fichiers** (claude.md = règles, HANDOFF.md = état courant,
   NEXT.md = backlog). C'est voulu (sessions éphémères) mais il faut le savoir.

## Ta boucle de travail recommandée (rapide)

1. Ouvre `specs/krokmou.json`, change UNE valeur (ex. un rayon, une couleur).
2. `python3 pipeline/run.py part specs/krokmou.json <la_pièce> --fast` → 20-30 s.
3. Content ? `forge --fast` pour voir l'ensemble. Pas content ? git checkout de la spec.
4. Les `renders/scene.blend` (+ `scene_prev.blend`) s'ouvrent dans TON Blender local
   pour tourner autour du modèle en 3D temps réel — souvent plus parlant qu'un PNG.
