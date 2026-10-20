> Mise à jour du 1er octobre 2026 : deux parcours indépendants depuis la carte « Mémoriser des séries ». Mots lus : 2 s visibles + 2 s de blanc ; mots entendus : fichiers locaux mutualisés, pause de 2 s après la fin du mot. Séances de quatre items. Voir ADR-022. Les descriptions de rythme antérieures ci-dessous sont historiques.

# Module « Rappel de séries » (rappel libre — hors MDR)

**Principe** : plusieurs courtes séries de mots sont présentées l'une après l'autre, puis l'utilisateur **rappelle librement** ce dont il se souvient — tous mots confondus, ou seulement ceux de la première série. C'est un exercice de **récupération** : rien n'est proposé, l'indice n'existe plus, il faut retrouver.

Le nombre de mots retrouvés reste le résultat principal : l'item déclare un **seuil** (`reponse.seuil`). L'interface sépare désormais les mots retrouvés, les omissions, les mots d'une autre série quand seule la première était demandée, et les intrusions (mots jamais présentés). Atteindre le seuil avec une confusion ou une intrusion ne compte pas comme maîtrise complète de la carte, tout en créditant explicitement les cibles retrouvées.

## Paliers

| Palier | Contenu | Seuil |
|---|---|---|
| 1 | Une série de 4 mots, rappel immédiat | 0,75 |
| 2 | Deux séries de 3 mots, rappel de l'ensemble | 0,60 |
| 3 | Trois séries de 3 mots, rappel de l'ensemble | 0,50 |
| 4 | **Rappel différé** : l'affichage est suivi de 20 s d'attente, puis question — toutes les séries, puis la première série seule | 0,50 / 0,60 |

8 items par palier, soit **32 items**.

La carte sépare trois progressions : rappel immédiat, rappel différé de toutes les séries et rappel de la première série seulement. Le parcours immédiat commence automatiquement au palier 2 (deux séries de trois mots) pour éviter une première séance limitée à quatre mots ; le palier 1 reste disponible. Les deux tâches différées commencent à leur unique niveau et ne sont pas présentées comme la suite obligatoire du rappel immédiat.

## Deux mécanismes, deux effets distincts

- **Interférence entre séries** (paliers 2 et 3) : plus il y a de séries, plus le rappel doit trier — c'est le rappel de *toutes* les séries qui est demandé, pas seulement de la dernière.
- **Délai** (palier 4) : un temps d'attente de 20 secondes sépare l'affichage de la question. L'attente est visible et peut être passée (aucune contrainte imposée) ; ce qui compte, c'est que l'information doit être retrouvée **sans appui contextuel**.

## Structure

- `paliers.json` — manifest des 4 paliers
- `paliers/palier-01..04.json` — 8 items par palier

## Réponses attendues

`reponse.valeur` est la liste des mots cibles ; `reponse.seuil` le seuil de réussite. La comparaison est faite côté serveur : mots comparés sans accents ni casse, ordre indifférent, pluriel simple toléré. Le serveur renvoie aussi le détail des omissions, confusions de série et intrusions ; le navigateur ne recalcule pas ce résultat. Aucun mot ne peut apparaître dans deux séries (le comptage serait ambigu) — contrôle bloquant du validateur.

## Précautions

- **Aucune norme, aucune note** : le nombre de mots retrouvés est un repère personnel de séance, jamais un score de mémoire.
- Les mots du pool sont concrets et courts, choisis pour limiter les confusions phonologiques ; aucun matériel de test normé n'est reproduit.
- Le rappel différé proposé ici reste **court** (20 s) : il entraîne la récupération sans indice, il ne prétend pas mesurer la mémoire à long terme.

## Génération

`tools/generer_rappel_series.py` (déterministe, graine 20260922). Relecture orthophoniste formelle à faire.
