# Prochaine boucle — décisions utilisateur (2026-07-07)

Exécuter au prochain créneau (utilisateur en attente, ne pas relancer sans lui) :

1. **Géométrie prioritaire** : (a) écailles GÉO chevauchantes sur cou+tête via
   `detail.armor_scales`/`keeled_scale` (comble l'écart densité de bords 0.15→~0.24) ;
   (b) reliefs crâniens osseux : arcades sourcilières, brow ridges, naseaux (tête trop lisse).
2. **Couleur** : TEMPÉRER le cuivre vers la réf — part cuivre 0.79 → ~0.42. Charbon noir
   dominant, cuivre plus discret. Baisser `tint`/couverture d'arête dans `reptile_scales`.
3. **Éclairage hero** : RIM contre-jour (`core.rim_setup`, comme step_027), fond noir.
4. Valider chaque pas via `run.py compare specs/dragon_got.json references/drogon_head_profile.png`
   (réf | rendu + deltas couleur/densité). Cibles : couleur moy ≈ (0.24,0.16,0.14), bords ≈ 0.24.
