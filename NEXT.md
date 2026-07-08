# Boucle 7 CLOSE (2026-07-08) — EN ATTENTE DE FEEDBACK UTILISATEUR sur step_080/step_081

## Fait cette boucle
1. **Tests architecture T10-T14** (`research/logs/`) : SDF voie A OK (T10), archétypes
   +15 % bords (T11), micro par instance OK mais meurt au Realize (T12), throttle neutre (T14).
2. **Câblage** : archétypes par région (`detail.armor[].archetypes` + `index_grad` dithéré),
   instances vivantes (`realize:false` défaut) + `scale_seed` lu par `reptile_scales(micro)`,
   throttle Cycles. FIX OOM : distribution bornée au mesh de base (Separate Components) —
   les entrées empilées semaient des écailles sur les écailles (272k instances dès 2 entrées).
3. **Tête refaite** (feedback step_073) : crâne élargi/reculé fondu dans le cou (armure cou
   continuée sur l'arrière du crâne jusqu'à y 3.5 = plus de bande lisse « greffe »),
   mâchoire inf. fortement agrandie + gape 30°, dents ×1.55, naseaux monticule+ouverture,
   2 cornes MAÎTRESSES balayées arrière (pairs 6, master_k 1, pitch -48, scale 1.6).

## Mesures HQ (step_080, compare drogon_head_roar)
bords 0.182 (cible 0.36) · cuivre 0.404 (cible 0.42) · 19.5k plaques, build 0.33 Go.

## Boucle 8 (après feedback)
- Bords encore loin : monter densités/distance_min (mémoire désormais quasi gratuite),
  displacement VRAI zones héros (T13 adaptive subdiv OBJECT à tester), micro plus visible.
- Couche MACRO anatomie : câbler la voie SDF (T10 OK) — muscles/os sous-peau + règle
  les 119 non-manifolds restants.
- Si la tête convient : verrouiller, sinon itérer sur retours précis.

## Reprise de session (conteneur neuf)
`bash pipeline/bootstrap.sh` puis lire claude.md. Modèle Blender ouvrable :
`renders/scene.blend` (régénérable : `python3 pipeline/run.py forge specs/dragon_got.json --fast`).
