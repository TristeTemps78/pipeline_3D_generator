# NEXT — backlog long terme (lu au CADRAGE d'une boucle seulement ; état courant → HANDOFF.md)

Priorisé, à recadrer à chaque feedback. Le « fait » vit dans git log + HANDOFF, pas ici.
Nettoyé 2026-07-13 : items Drogon archivés en bas, « 2e créature » RETIRÉ (fait — Krokmou,
boucle 20, prouve la généricité dragon→autre morphologie).

## Mécanismes génériques à construire (valables toute créature)
1. Décalque/texture localisée (emblème blanc prothèse Krokmou, cicatrices, marquages) —
   seul manque bloquant identifié en boucle 20 (note « OMIS v1 » de la spec).
2. Accessoires portés : selle/sangles cuir (nouveau type de partie ou courbe d'attache
   généralisée — cf. doctrine SDF v1, axe attachment_curve).
3. Lissage de spine au close-up : interpolation plus ronde entre points (queue Krokmou
   = zigzag anguleux) ; bord organique pour ailerons (lames plates → nageoires).
4. Plis de peau aux articulations (`fold_rings` aux joints des tubes limb/spine) +
   écailles multi-zones (étendre scale_grad/masks en gradient multi-zones).
5. Environnement : builders de fond génériques (dégradé/flou), lumières d'appoint —
   JAMAIS de volume scatter par défaut (piège CLAUDE.md : ×30-100 sur CPU).
6. Membrane niveau 2 : réseau veines/tendons sous la peau (shader), micro-plis,
   translucidité sans taches (cf. pièges CLAUDE.md).
7. Découpage `bx/organic.py` (1854 l.) en un fichier par type de partie — SEULEMENT si
   l'utilisateur veut lire ce code.
8. Doctrine SDF v1 (`research/doctrine_sdf_v1.md`) : SDF backbone complet.
9. Maintenance dépôt : `.git` pèse ~400 Mo (historique de renders) — proposer à
   l'utilisateur une réécriture d'historique (destructif, décision à lui) ou vivre avec
   `git clone --depth 1`.

## Archivé avec Drogon (reprendre SEULEMENT si retour au dragon)
- PBR patine cuivre/vert-de-gris dans les creux, reflets dorés (roadmap step_141 d/e).
- Restes boucle 19 : bake consommant axis_uv (edge_density .19→.348), pad/toes pâles,
  anatomie bras d'aile vs fuse SDF (détail : git log + session.json).
- fuse_groups étendu à head/hindleg — BLOQUÉ : la fusion casse le ciblage armor par
  groupe (prérequis : masque spatial sur mesh fusionné). Cibles compare Drogon :
  cuivre .42, bords .36 (priorité utilisateur = densité de bords).
