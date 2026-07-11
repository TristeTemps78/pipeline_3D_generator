# Protocole d'orchestration (inspiré BlenderFusion, sans outil externe)

Boucle : **GROUND → BUILD → RENDER → CRITIQUE → FEEDBACK utilisateur → EDIT** (répéter).

1. **GROUND** (agent `ref-analyst`) : référence (texte/image/vidéo décrite) → `specs/<nom>.json`.
   Décomposition object-centric en parties contrôlables (spine, head, wing, limb…), chaque
   forme organique ancrée sur une clé GVL (`gvl/vocabulary.json`) au lieu d'une description verbeuse.
2. **BUILD** (agent `shape-smith`) : édite la spec (géométrie/pose) ou étend `bx/organic.py`
   si un nouveau type de partie est requis. Jamais de bpy brut hors de `bx/`.
3. **LOOK** (agent `look-dev`) : matériaux, lumières, caméra — sections `materials`/`scene` de la spec.
4. **RENDER** : `python3 pipeline/run.py forge <spec> --fast` pour itérer, sans `--fast` pour présenter.
5. **CRITIQUE** : d'abord MESURÉE — `python3 pipeline/run.py compare <spec> <ref.png>`
   (planche réf|rendu + deltas `color_stats`/`edge_density`). Puis OBLIGATOIRE (auto-audit
   boucle 19, faute F2) : agent `render-critic` SÉPARÉ (œil neuf, jamais celui qui a
   implémenté) sur les shots HQ de présentation, prompt = critères de l'évaluateur
   utilisateur ; ses défauts bloquants font continuer la boucle au lieu de s'arrêter.
   Un correctif n'est « fait » que s'il LIT dans le shot de présentation (faute F1) —
   les rapports distinguent « implémenté » de « lit à l'écran » (faute F5). Max 3
   itérations internes en --fast, puis rendu HQ.
6. **FEEDBACK** : STOP obligatoire — présenter le rendu HQ à l'utilisateur et attendre
   ses retours précis avant toute suite. Consigner le feedback dans `pipeline/state/session.json`
   et les décisions actionnables dans `NEXT.md` (contrat de la boucle suivante, avec cibles chiffrées).

## Boucle mesurée (doctrine depuis research/inversions.md)
- Chaque changement visuel est jugé contre une CIBLE CHIFFRÉE (couleur moyenne, densité de bords,
  IoU silhouette) issue de `references/`, jamais « à l'œil » seul.
- Géométrie d'abord (clay), look ensuite ; on ne mélange pas les deux dans une même itération.
- Un pas qui n'améliore pas sa métrique est annulé (git checkout de la spec), pas « compensé ».

## Multi-sessions / branches
- Toutes les sessions convergent sur UNE lignée : avant de travailler, `git fetch --prune`,
  repérer la branche `claude/*` la plus avancée, fast-forward dessus (les branches ne doivent
  jamais diverger — une seule session écrit à la fois).
- Après push, miroiter la pointe sur les autres branches `claude/*` actives
  (`git push origin HEAD:<branche>`) pour que la prochaine session parte du bon état.
- Conteneur neuf : `bash pipeline/bootstrap.sh` (installe bpy pip si absent).

## Règles d'économie de tokens
- L'état vit dans les fichiers (spec, session.json, claude.md), pas dans la conversation.
- Les agents lisent uniquement : claude.md + la spec + (si besoin) le module bx concerné.
- Les phases BUILD/LOOK/GROUND sont DÉLÉGUÉES à des agents en modèle SONNET
  (`model: sonnet` au spawn) avec un contrat précis (cibles chiffrées, fichiers à toucher,
  nb max d'itérations) ; l'orchestrateur ne fait que cadrer, juger les rendus et committer.
- Auto-audit à chaque fin de boucle : `bash pipeline/audit.sh` + purge des renders non-jalons
  (garder : jalons référencés dans claude.md/NEXT.md, scene.blend + scene_prev.blend).
- Éditions de spec par petits patchs JSON, pas de réécriture complète.
- Rendus internes en --fast (640×480/16 spl) ; HQ (1152×864/48 spl) réservé à la présentation.
- Mettre à jour claude.md à chaque grosse étape (fin de boucle, changement d'architecture).
