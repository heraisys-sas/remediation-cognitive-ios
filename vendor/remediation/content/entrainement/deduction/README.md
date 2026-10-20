# Déduction — cinq paliers, 100 grilles

Chaque figure colorée est utilisée une fois et chaque case reçoit un pion. **Toute autre contrainte doit être écrite dans les indices de la grille en cours**. Aucune répartition des formes ou couleurs n'est une règle permanente.

## Progression

| Palier | Grille | Travail proposé |
|---|---|---|
| 1 | 3×3 | Repères et voisinages ; chaînes guidées, puis informations à relier soi-même |
| 2 | 3×3 | Exclusions et voisinages simples ; repères positifs en entrée, deux repères du même pion regroupés en étape 2, sans repères individuels en étape 3 |
| 3 | 3×3 | Répartition d'une catégorie, relations et entre-deux ; extrémités nommées puis partielles, enfin sans voisinages immédiats |
| 4 | 3×3 | Diversité explicite, exclusions, entre-deux partiel et relations croisées ; derniers exercices sans repères individuels de ligne/colonne |
| 5 | 4×4 | Synthèse de ces familles ; entre-deux diagonal à partir de l'étape 2, davantage de positions à départager |

20 grilles par palier : 7 d'introduction, 7 intermédiaires et 6 de synthèse (`contenu.etape_progression`). C'est une progression de **contraintes pédagogiques**, pas une échelle de difficulté cognitive étalonnée : une grille peut être subjectivement plus facile que la précédente.

Les nouveautés suivent cet ordre. Lorsqu'il existe aussi des révisions dues, la moitié des places de la séance est réservée aux nouveautés ; les révisions avancées passent avant les anciennes grilles faciles. La maîtrise exige trois séances réussies selon le critère existant, **chacune comprenant une réponse de l'étape finale**. Les seules étapes préparatoires ne valident pas le palier. Le choix manuel du palier reste disponible.

## Familles d'indices

- Repères, exclusions individuelles, voisinages, comparaisons, diagonales et opposition par symétrie centrale.
- **Exclusion collective** : aucune figure d'une couleur ou d'une forme dans une ligne/colonne.
- **Répartition** : exactement un pion d'une catégorie dans une région, ou dans chaque ligne/colonne.
- **Diversité** : exactement un pion de chaque forme ou couleur dans la région indiquée. C'est un indice local au puzzle.
- **Entre-deux** : un pion se trouve strictement entre deux autres sur une ligne, colonne ou diagonale à 45°. Les extrémités peuvent n'être désignées que par leur forme ou couleur. Elles sont deux pions distincts, choisis parmi ceux de la palette. La distance et le voisinage immédiat ne sont pas imposés.

Au palier 2, une phrase comporte au maximum deux repères concernant exclusivement le même pion, reliés par « et ». Les relations avec un autre pion restent autonomes : aucun changement de sujet avec « qui ». Le palier compte désormais 6 à 8 phrases par grille (7,25 en moyenne, contre 9,8). Aux autres paliers, une phrase peut porter plusieurs informations utiles ; aucune longueur minimale artificielle. Les phrases collectives restent autonomes. Les longues chaînes de l'initiation se raccourcissent progressivement.

Sur une grille 3×3, « entre deux pions sur une diagonale » donnerait immédiatement le centre. Le générateur réserve donc cet indice au 4×4, pour conserver le recoupement exigé aux paliers avancés. Les autres indices diagonaux restent disponibles en 3×3.

## Garanties vérifiées

- Chaque réponse satisfait les indices ; contrôle séparé de leur sens et de leur formulation française.
- Chaque grille se résout par éliminations et propagation de contraintes, sans recherche par hypothèses.
- Un second algorithme, qui n'appelle pas le propagateur de génération, cherche jusqu'à deux solutions et confirme **l'unicité et l'identité avec la réponse enregistrée**.
- Aux paliers 2–5, aucune phrase seule ne fixe une position : énumération des placements pour les relations individuelles/entre-deux, symétrie des pions d'une catégorie pour les contraintes collectives autonomes.
- Retirer une information du noyau de résolution empêche la résolution complète par le propagateur. Exception pédagogique explicite : certaines grilles d’entrée de P2 ajoutent un repère visible (`repere_accompagnement`) pour faciliter le démarrage ; le noyau est vérifié séparément, sans ce repère. Cette nécessité pour la preuve utilisée **ne signifie pas** que chaque information serait indispensable à l'unicité mathématique ; ce sont deux propriétés distinctes.
- Des tests comparent les contraintes collectives à un oracle indépendant sur 2 160 affectations, dont des configurations non latines, des contradictions et des références partielles.

Ces contrôles structurels ne démontrent ni une équivalence clinique avec un matériel papier ni une efficacité thérapeutique. La relecture orthophonique reste `a_revoir`.

## Utilisation et génération

Six grilles au maximum par séance ; à dix minutes, l'arrêt est proposé. Le bouton **Aide au raisonnement** propose trois étapes : phrases numérotées à observer, possibilités à comparer, puis conclusion expliquée sur demande explicite. Les aides utilisent uniquement les énoncés déjà visibles : aucune coordonnée supplémentaire tirée au hasard de la solution. Pour les croisements complexes, la démonstration conserve la succession des réductions de possibilités, vérifiée étape par étape. Les grilles d’entrée de P2 affichent en plus une méthode de démarrage. Le tableau est une **aide facultative du logiciel**, fermée à chaque nouvelle grille et accessible par « Aide — noter les possibilités ». Les consignes et aides au raisonnement ne demandent pas de l’utiliser. Son ouverture permet d’externaliser les possibilités ; il ne fait pas partie du parcours par défaut. La grille de placement des pions reste, elle, toujours présente.

```sh
python3 tools/generer_deduction.py
python3 tools/validate_items.py
python3 tools/verifier_unicite_deduction.py
python3 tools/mesurer_difficulte.py
node tools/verifier_phrases.js
```

Génération déterministe, graines isolées par palier, solutions distinctes et identifiants dérivés du contenu. Cette refonte **remplace le corpus de 80 grilles par 100 grilles avec de nouveaux identifiants** : les anciennes cartes de répétition espacée ne sont pas réaffectées à de nouveaux exercices. Le palier courant enregistré est préservé ; l'ancien palier 4 propose maintenant le 3×3 avancé, le 4×4 se choisit au palier 5.
