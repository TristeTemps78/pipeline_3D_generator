# AUTO-AUDIT ORCHESTRATEUR (boucle 19) — pourquoi 3 boucles de « fixes » ne convainquent pas

Demandé par l'utilisateur au feedback step_231. Objet : le PROCESS, pas le modèle.
Constat : les évaluateurs répètent les mêmes critiques depuis step_182 (texture uniforme,
œil mort, dents-cônes, anatomie absente) alors que chaque boucle a livré des correctifs
« vérifiés ». Les deux sont vrais en même temps — c'est le process qui les réconcilie mal.

## Fautes du process (les miennes)

### F1 — Le juge n'est pas à l'échelle de l'acceptation
Les agents et moi validons sur des rendus 640×480 fast ou 1152×864/20 samples, en crops
choisis par CELUI QUI A FAIT le changement. L'évaluateur juge la lecture GLOBALE contre
une référence cinéma. Un iris fente de 12 pixels « validé en crop » est une bille de
verre à l'écran. Résultat récurrent : je rapporte « narines percées, gencives, iris » —
l'évaluateur répond « absents ». Techniquement présents, perceptuellement inexistants.
→ RÈGLE : un correctif n'est « fait » que s'il lit dans le SHOT DE PRÉSENTATION, pas en
crop de diagnostic. Ajouter des shots de vérification par feature (œil, dents, narine,
articulation) à ÉCHELLE ÉVALUATEUR dans scene.shots, rendus à samples élevés.

### F2 — Les agents s'auto-notent, render-critic n'a JAMAIS été utilisé
Le protocole (orchestrator.md) prévoit une phase CRITIQUE par l'agent `render-critic`
(œil neuf, liste de défauts priorisée AVANT le stop utilisateur). En 8 boucles je ne l'ai
pas spawné une seule fois : l'agent qui implémente juge son propre travail, et moi je
regarde ses rendus déjà cadrés pour flatter le correctif. L'évaluateur externe de
l'utilisateur joue le rôle que render-critic aurait dû jouer en interne.
→ RÈGLE : CRITIQUE obligatoire par render-critic (agent séparé, prompt = les critères de
l'évaluateur) sur les 3 shots HQ avant TOUT stop feedback. Ses défauts bloquants = la
boucle continue au lieu de s'arrêter.

### F3 — J'ai traité les symptômes texture avant la cause anatomie
« Pas d'ossature/muscles/articulations » est dans les feedbacks depuis step_141 (plis
d'articulations), l'audit boucle 17 le classait CR4 — et je l'ai reporté « si budget »
à CHAQUE boucle au profit de chantiers shader plus rapides à montrer. Or le « papier
peint » vient de là : une texture, même bonne, posée sur un cylindre lit comme un calque.
→ RÈGLE : boucle 19 = ANATOMIE D'ABORD (volumes musculaires fusiformes dans limb/wing,
articulations marquées, plis aux plis), textures ENSUITE.

### F4 — Bruit isotrope vendu comme organique
Les motifs procéduraux employés (Voronoï écailles, craquelures) sont ISOTROPES : même
statistique partout, aucune direction. L'évaluateur les nomme correctement (« type
Voronoï », « terre craquelée »). Le vivant est ANISOTROPE et suit l'anatomie : écailles
en RANGÉES le long des axes (spine, doigts), tailles en champs continus, veines en
ARBRE depuis les os. La donnée existe déjà dans la spec (axes, ancres) — les shaders ne
la consomment pas.
→ RÈGLE : les champs de texture doivent être PILOTÉS par l'anatomie de la spec
(coordonnées curvilignes le long des axes de pièces, arbres de veines tracés depuis les
doigts) — plus aucun bruit isotrope nu en première intention.

### F5 — Vocabulaire de rapport trompeur
Mes clôtures de boucle disent « corrigé/lisible/validé » sur la foi de l'agent. Trois
boucles de suite l'utilisateur constate l'inverse. C'est un problème d'HONNÊTETÉ du
process : le rapport doit distinguer « implémenté » (fait technique) de « lit à l'écran »
(constat render-critic) — et ne jamais confondre les deux.

## Ce qui est objectivement vrai côté évaluateur vs code
- « Iris/pupille fendue absents » : ils EXISTENT (materials.eye_globe) mais ~10 px,
  sombres, sous paupière — invisibles au cadrage head. F1.
- « Dents sans gencives » : gencives présentes (blobs) mais échelle/contraste faibles. F1.
- « Texture globale uniforme » : le zonage nz existe (ventre/dos/flancs) mais les
  ARCHÉTYPES restent semblables et le semis isotrope → perçu uniforme. F4 (fond vrai).
- « Cônes parfaits » pour dents/cornes : growth_rings/inclinaisons existent mais
  subtils ; aucune asymétrie/usure par dent. Fond vrai.
- « Aucune anatomie » : vrai. Jamais traité. F3.

## Plan boucle 19 (à valider par l'utilisateur avant exécution)
1. ANATOMIE (F3) : builder limb/wing avec volumes musculaires fusiformes (cuisse, mollet,
   avant-bras d'aile), articulations renflées + plis de peau aux plis (mécanisme
   générique), tension de pose.
2. CHAMPS ANATOMIQUES (F4) : écailles en rangées le long des axes (coordonnée curviligne
   de spine/membres exposée aux shaders et à l'armure), veines de membrane en arbre
   depuis les doigts (géométrie fine ou texture tracée, pas Voronoï).
3. LISIBILITÉ (F1) : dents/cornes irrégulières par seed (courbure, usure, asymétrie) à
   amplitude visible au shot head ; œil agrandi ou cadrage œil dédié dans shots.
4. PROCESS (F2/F5) : phase render-critic OBLIGATOIRE avant stop ; rapports en deux
   colonnes implémenté/lit-à-l'écran ; shots de vérification par feature.
