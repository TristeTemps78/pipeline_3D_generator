# Protocole d'orchestration (inspiré BlenderFusion, sans outil externe)

Boucle : **GROUND → BUILD → RENDER → CRITIQUE → FEEDBACK utilisateur → EDIT** (répéter).

1. **GROUND** (agent `ref-analyst`) : référence (texte/image/vidéo décrite) → `specs/<nom>.json`.
   Décomposition object-centric en parties contrôlables (spine, head, wing, limb…), chaque
   forme organique ancrée sur une clé GVL (`gvl/vocabulary.json`) au lieu d'une description verbeuse.
2. **BUILD** (agent `shape-smith`) : édite la spec (géométrie/pose) ou étend `bx/organic.py`
   si un nouveau type de partie est requis. Jamais de bpy brut hors de `bx/`.
3. **LOOK** (agent `look-dev`) : matériaux, lumières, caméra — sections `materials`/`scene` de la spec.
4. **RENDER** : `python3 pipeline/run.py forge <spec> --fast` pour itérer, sans `--fast` pour présenter.
5. **CRITIQUE** (cadence SIMPLICITÉ boucle 20, remplace le « max 3 itérations » d'avant) :
   1 round géométrie + 1 round look MAX avant de montrer. D'abord MESURÉE —
   `python3 pipeline/run.py compare <spec> <ref.png>` (planche réf|rendu + deltas). Puis
   agent `render-critic` SÉPARÉ (œil neuf, jamais celui qui a implémenté), UNE passe,
   UNIQUEMENT sur les shots HQ de présentation ; ses défauts bloquants font continuer la
   boucle. Un correctif n'est « fait » que s'il LIT dans le shot de présentation —
   distinguer « implémenté » de « lit à l'écran ».
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

## Économie de tokens
Les règles vivent dans CLAUDE.md (section ÉCONOMIE, auto-chargée par toutes les sessions
et tous les agents) — ne pas les dupliquer ici. Spécifique à l'orchestration :
- Délégation = contrat PRÉCIS : les CLÉS de spec à toucher (pas « relis la spec »),
  cibles chiffrées, nb max d'itérations ; l'orchestrateur ne fait que cadrer, juger,
  committer.
- Chaque PNG regardé coûte (≈0,4 k tokens en 640×480, ≈1,3 k en HQ) : juger sur UNE
  planche (`sheet`/`compare`) par round, pas les shots un à un.
- Fin de boucle : `bash pipeline/audit.sh` (signale renders non référencés et agents
  sans `model:`) + purge + mise à jour CLAUDE.md/HANDOFF.md.
