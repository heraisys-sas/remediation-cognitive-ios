# Module Mémoire (Entraînement — hors MDR)

**Principe** : entraîner la mémoire de travail et la mémorisation par les familles classiques des techniques d'entraînement cognitif — empan, apprentissage par paires, sonde n-back. Implémentations originales : la logique des paradigmes est assimilée.

## Parcours indépendants

- **Empan de chiffres** (endroit puis envers) : longueur 3 → 6 chiffres par paliers ; l'envers ajoute la manipulation en mémoire de travail. Affichage séquentiel, avec 2 secondes visibles et 2 secondes de blanc par élément.
- **Paires associatives mot–nombre** : 2 → 4 paires de mots concrets courants, affichage en liste (16 s), puis rappel du nombre associé à un mot sondé — entraîne une compétence utile au quotidien (codes, rendez-vous, cours).
- **Sonde n-back** : rappel de l'élément situé N positions avant la fin d'une séquence de lettres (N = 2 → 4) — variante « rappel » du paradigme n-back, exigeante mais moins frustrante que la version oui/non continue.

Les cinq parcours ont une maîtrise séparée : chiffres endroit, chiffres envers, mots, associations et position dans une séquence. Le mode automatique commence à cinq chiffres endroit, quatre mots et trois paires ; l'ordre inverse et la sonde de position commencent à leur premier niveau car ils introduisent une manipulation différente. Les niveaux plus simples restent disponibles dans le sélecteur d'essai.

## Structure

- `paliers.json` — manifest des 8 paliers (id, description, prerequis, nb_items)
- `paliers/palier-01..08.json` — 18 items par palier, soit **144 items**

## Réponses attendues

- empans : chaîne de chiffres (les espaces de saisie sont ignorés côté serveur) ;
- n-back : lettre (casse ignorée) ;
- paires : nombre.

## Génération

Contenu produit par `tools/generer_memo_concentration.py` (déterministe, graine 20260904). Toute retouche manuelle d'un item doit mettre à jour `meta.relecture_ortho` (relecture orthographique et clinique avant diffusion large).

## Moteur

Identique aux autres thèmes : paliers (90 % × 3 séances), FSRS, détection de fatigue, séparément pour chaque parcours. L'affichage temporisé (phase de mémorisation distincte de la question, stimulus masqué avant la saisie) est pris en charge par l'interface ; le temps de mémorisation ne compte pas dans `temps_ms`.

## Empan de mots (sprint 4, paliers 9 à 12)

Même logique que l'empan de chiffres, avec du matériel verbal : trois à cinq mots
courts présentés un par un, à retranscrire **dans l'ordre** (puis à l'envers aux
paliers 11 et 12). L'ordre est significatif : la comparaison se fait mot à mot,
sans accents ni casse.

- palier 9 : 3 mots, endroit · palier 10 : 4 mots, endroit · palier 11 : 5 mots,
  endroit · palier 12 : 3 et 4 mots, envers.
- Le rappel verbal est sensible à la similarité phonologique et au sens : le pool
  est concret, court, et sans doublon dans une même séquence.

## Rythme d'affichage

Chaque chiffre, mot ou lettre reste visible **2 secondes**, puis disparaît pendant
**2 secondes** avant l'élément suivant. L'interface affiche donc explicitement
« un élément toutes les 4 secondes ». Le validateur exige ces deux durées sur
toute séquence à mémoriser.
