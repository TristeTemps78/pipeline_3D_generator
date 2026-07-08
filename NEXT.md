# Boucle 8 CLOSE (2026-07-08) — EN ATTENTE DE FEEDBACK sur step_087 (compare) / step_088 (scène)

## Fait (tête v2, par agent shape-smith Sonnet + retouche orchestrateur)
1. **Cornes** : maîtresses couchées vers l'ARRIÈRE au-dessus du haut du cou (pitch +70 —
   ATTENTION : angle X POSITIF = bascule arrière dans ce repère), bases reculées, r0 0.13.
2. **Naseaux intégrés** : ouverture CARVÉE au boolean dans le museau (comme les orbites),
   monticule enfoncé aux 2/3 — plus de blob posé.
3. **Gueule** : gape 36°, mâchoire inf. élargie/approfondie (~×1.15/×1.3), crocs saillants
   génériques (fang_idx_*/fang_scale_* dans la spec), tooth_scale 1.7, arcade rehaussée.
Aussi : directives projet (généricité, agents Sonnet, compacité), audit.sh, purge 72→14 Mo,
rotation scene.blend + scene_prev.blend (2 derniers modèles pour Blender local).

## Mesures HQ (step_087 vs drogon_head_roar)
bords 0.195 (0.182 en b7 ; cible 0.36) · cuivre 0.403 (cible 0.42).

## Boucle 9 (après feedback)
- Bords : monter densités/distance_min (mémoire quasi gratuite), displacement zones héros
  (T13 adaptive subdiv OBJECT à tester), micro par instance plus contrasté.
- Couche MACRO anatomie SDF (T10 OK) : muscles/os sous-peau + règle les non-manifolds.
- Déléguer la phase BUILD à shape-smith Sonnet avec contrat chiffré (protocole).

## Reprise (conteneur neuf)
`bash pipeline/bootstrap.sh` puis lire claude.md.
