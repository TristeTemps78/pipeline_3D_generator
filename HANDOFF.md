# HANDOFF — état courant + reprise (SEUL fichier d'état ; permanent → claude.md, backlog → NEXT.md)

Reprise (conteneur neuf) : `bash pipeline/bootstrap.sh` → claude.md → ce fichier, puis si
l'utilisateur dit « continue », exécuter le contrat ci-dessous sans reposer de question.

## Où on en est
Boucle 13 BUILD TERMINÉ, **EN ATTENTE DE FEEDBACK utilisateur** sur le HQ **step_141**
(comparer à step_133 = jalon précédent rejeté « deltaplane »). Jalons de la boucle :
planche sheet4 **step_134**, gros plan aile **step_136**, gros plan pieds **step_138**.
Fait (commits 35fde85+) :
- Aile organique anti-deltaplane, builder `wing` étendu GÉNÉRIQUEMENT : `finger_bow` (doigts
  en arcs divergents, colonnes membrane collées), `panel_billow` (chair par panneau),
  `finger_taper`, feston normalisé par corde de panneau. Spec : festoon .12→.55, finger_r0
  .22, bow .9, billow .35, root_curve resserrée (y .6→0.0, reste d'aile-nageoire réduit).
- Pieds massifs : foot length .5→.9, toe_r0 .15→.28, claw_len .32, pad ×~2.
- Item 3 (fuse_groups head/hindleg) REPORTÉ — blocage documenté dans NEXT.md item 2
  (armor cible les groupes par id ; fusion = régression du fix boucle 12).
Métriques step_140 (compare vs drogon_body_flight) : bords .21 vs cible .35, cuivre .63
vs .46 — le chantier look/densité reste ouvert (NEXT item 5, hors contrat boucle 13).

## Contrat boucle 14 (à cadrer APRÈS le feedback sur step_141)
Pas de contrat tant que l'utilisateur n'a pas jugé ailes (éventail/feston/chair) et pieds.
Consigner son feedback dans `pipeline/state/session.json` + réécrire ce fichier. Candidats
selon verdict : amplitudes finger_bow/panel_billow à recaler en HQ (doute agent boucle 13),
micro-plis membrane (NEXT 1), œil gros plan (NEXT 3), densité de détail/look (NEXT 5).

## Restes connus hors contrat
Œil composite jamais validé en gros plan couleur ; look couleur/atmosphère à recaler ;
caméra HQ = plongée d'origine (angles bas testés et rejetés) ; feston `chord_scale` =
approximation par largeur de panneau (à revoir si wing très asymétrique).
