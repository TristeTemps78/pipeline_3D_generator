# Protocole d'orchestration (inspiré BlenderFusion, sans outil externe)

Boucle : **GROUND → BUILD → RENDER → CRITIQUE → FEEDBACK utilisateur → EDIT** (répéter).

1. **GROUND** (agent `ref-analyst`) : référence (texte/image/vidéo décrite) → `specs/<nom>.json`.
   Décomposition object-centric en parties contrôlables (spine, head, wing, limb…), chaque
   forme organique ancrée sur une clé GVL (`gvl/vocabulary.json`) au lieu d'une description verbeuse.
2. **BUILD** (agent `shape-smith`) : édite la spec (géométrie/pose) ou étend `bx/organic.py`
   si un nouveau type de partie est requis. Jamais de bpy brut hors de `bx/`.
3. **LOOK** (agent `look-dev`) : matériaux, lumières, caméra — sections `materials`/`scene` de la spec.
4. **RENDER** : `python3 pipeline/run.py forge <spec> --fast` pour itérer, sans `--fast` pour présenter.
5. **CRITIQUE** (agent `render-critic`) : compare le rendu à la référence, liste des défauts
   classés par impact ; max 3 itérations internes en --fast, puis rendu HQ.
6. **FEEDBACK** : STOP obligatoire — présenter le rendu HQ à l'utilisateur et attendre
   ses retours précis avant toute suite. Consigner le feedback dans `pipeline/state/session.json`.

## Règles d'économie de tokens
- L'état vit dans les fichiers (spec, session.json, claude.md), pas dans la conversation.
- Les agents lisent uniquement : claude.md + la spec + (si besoin) le module bx concerné.
- Éditions de spec par petits patchs JSON, pas de réécriture complète.
- Rendus internes en --fast (640×480/16 spl) ; HQ (1152×864/48 spl) réservé à la présentation.
- Mettre à jour claude.md à chaque grosse étape (fin de boucle, changement d'architecture).
