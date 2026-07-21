# NEXT — backlog long terme (lu au CADRAGE d'une boucle seulement ; état courant → HANDOFF.md)

Priorisé, à recadrer à chaque feedback. Le « fait » vit dans git log + HANDOFF, pas ici.
Nettoyé 2026-07-13 : items Drogon archivés en bas, « 2e créature » RETIRÉ (fait — Krokmou,
boucle 20, prouve la généricité dragon→autre morphologie).
PIVOT 2026-07-16 « pipeline sculpteur » (voir CLAUDE.md/HANDOFF.md) : la liste
« mécanismes génériques » ci-dessous est GELÉE — à REJUGER item par item une fois la base
cage validée (plusieurs deviennent inutiles : lissage spine, plis de tubes… la cage les
couvre nativement).

## Post-pivot (nouvelle colonne vertébrale du backlog)
1. Extraction de généricité A POSTERIORI : quand la cage Krokmou marche, en tirer le
   schéma (cage dans la spec, outils d'édition de cage, miroir/creases) — PAS avant.
2. TripoSR CPU local (MIT, gratuit illimité) comme générateur d'ébauche photo→mesh à
   raffiner en cage — pari 30 min, jamais bloquant.
3. Bibliothèque de bases mesh CC0/CC-BY (quadrupèdes, dragons) + workflow « déformer une
   base propre vers la cible » (garde-fou 5 sauté).
4. Retopo/decimate outillé si les cages grossissent (rester éditable).

## Mécanismes génériques à construire (GELÉ post-pivot — rejuger après cage validée)
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
7. Découpage `bx/organic.py` (2616 l.) en un fichier par type de partie — SEULEMENT si
   l'utilisateur veut lire ce code.
8. Doctrine SDF v1 (`research/doctrine_sdf_v1.md`) : SDF backbone complet.
9. ~~Maintenance dépôt : `.git` à 400 Mo~~ — RÉGLÉ (audit 2026-07-21 : 42 Mo, clone
   complet de 72 commits). Rien à réécrire ; garder la règle « blends aux jalons ».

## Archivé avec Drogon (reprendre SEULEMENT si retour au dragon)
- PBR patine cuivre/vert-de-gris dans les creux, reflets dorés (roadmap step_141 d/e).
- Restes boucle 19 : bake consommant axis_uv (edge_density .19→.348), pad/toes pâles,
  anatomie bras d'aile vs fuse SDF (détail : git log + session.json).
- fuse_groups étendu à head/hindleg — BLOQUÉ : la fusion casse le ciblage armor par
  groupe (prérequis : masque spatial sur mesh fusionné). Cibles compare Drogon :
  cuivre .42, bords .36 (priorité utilisateur = densité de bords).
