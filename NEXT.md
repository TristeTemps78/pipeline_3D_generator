# Boucle 6 — candidats (boucle 5 close : points 1-3 faits, rendu step_057 ; EN ATTENTE DE FEEDBACK)

Reste des candidats (les points 4-5 d'origine, reportés, + nouveaux constats step_057) :
- **Luminosité/chaleur** : rendu 2× trop sombre vs réf, cuivre 0.36 (cible 0.42) ; monter
  key/rim, réchauffer les creux, désaturer l'or de l'œil (trop bijou), éteindre le sol visible.
- **Densité de bords 0.13 → 0.36** : rides/plis displace sur zones nues, petites écailles
  joues/mâchoire, carènes plus saillantes en silhouette.
- **Plans durs du crâne** : joues creuses, mâchoire anguleuse (sections superellipse plus carrées).

Archive boucle 5 (fait) :

Métriques honnêtes depuis le fix de normalisation (analyse à hauteur commune 512 px) :
cibles réf = couleur moy (0.33, 0.27, 0.26) · part cuivre 0.42 · densité de bords 0.36.
État rendu step_044 = (0.17, 0.14, 0.13) · 0.44 ✓ · 0.15.

Par impact décroissant (à valider/prioriser par l'utilisateur) :

1. **Œil** : actuellement un disque orange posé sur la joue. Il faut une orbite — creux
   sous l'arcade, globe enchâssé, paupière écailleuse. Position à remonter vers l'arcade.
2. **Couronne de cornes + crête** : la réf a une couronne DENSE et irrégulière qui se fond
   dans la crête du cou ; nous avons quelques cônes épars. Plus de paires, tailles variées,
   ancrage dans les plaques crâniennes.
3. **Cou plus musclé** : la réf a un arc de cou épais avec masses qui pendent (fanons) ;
   le nôtre est un tube. Sections de spine élargies + repli de peau sous la mâchoire.
4. **Luminosité/chaleur** : rendu 2× plus sombre que la réf. Monter key/rim, réchauffer
   copper_mean (0.10,0.07,0.06) → (0.26,0.17,0.15) : cuivre des creux plus émissif/clair.
5. **Densité de bords 0.15 → 0.36** : carènes plus saillantes en silhouette, rides/plis
   de peau (displace macro) sur les zones sans plaques, petites écailles sur joues/mâchoire.

Rappel workflow : géométrie via `run.py clayhero` d'abord, look ensuite, chaque pas jugé
par `run.py compare specs/dragon_got.json references/drogon_head_profile.png` (métriques
maintenant invariantes à la résolution) + regard humain sur la planche.
