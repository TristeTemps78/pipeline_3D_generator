# Boucle 7 — feedback utilisateur sur step_073 (2026-07-08), RIEN N'EST LANCÉ

## Feedback à traiter (géométrie tête, prioritaire)
1. **Tête pas intégrée au cou** (impression de greffe — raccord/continuité à retravailler).
2. **Mâchoire inférieure encore beaucoup trop petite** (2e fois : agrandir FORTEMENT).
3. **Gueule bien plus imposante et impressionnante** dans l'ensemble.
4. **Gros naseaux**.
5. **2 cornes pointant vers l'ARRIÈRE sur la tête** (2 maîtresses claires, pas une forêt).
6. Toujours plus de détails (le +35k va dans le bon sens mais insuffisant).

## Architecture à tester d'abord (budget tokens neuf)
Suivre `research/detail_architecture.md` : tests T10-T14 (SDF anatomie, archétypes
d'écailles par région, micro par instance via Attribute Instancer, adaptive subdiv
OBJECT, throttling Cycles). Câbler seulement ce qui passe les tests. T14 et T11 d'abord.

## Reprise de session (conteneur neuf)
`bash pipeline/bootstrap.sh` puis lire claude.md. Modèle Blender ouvrable :
`renders/scene.blend` (commité, régénérable par `python3 pipeline/run.py forge specs/dragon_got.json --fast`).
