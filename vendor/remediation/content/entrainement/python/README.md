# Module Python (Entraînement — hors MDR)

**Principe** : exercice à double dividende — l'effort de mémorisation **est** l'entraînement cognitif (rappel actif, mémoire de travail), et le contenu mémorisé constitue une compétence durable réellement transférable. Sert la transition thérapeutique → développement (cahier des charges §2.3) : contrairement à des drills abstraits, le contenu reste utile une fois les fonctions stabilisées, ce qui donne du sens à l'effort.

## Sous-arborescence

- `concepts/` — notions à comprendre et restituer : `bases/` (types, mutabilité, portée, f-strings…), `structures/` (listes, dicts, sets, tuples…), `controle/` (boucles, conditions, compréhensions…), `fonctions/` (signatures, générateurs, décorateurs…)
- `commandes/` — syntaxe et bibliothèque à automatiser : `builtins/` (len, sorted, enumerate, zip…), `syntaxe/` (mots-clés, opérateurs, gestion d'erreurs), `stdlib/` (collections, itertools, datetime… — paliers tardifs)
- `snippets/` — micro-patterns réutilisables (fichiers, itérations, erreurs…)

## Formats d'exercices — progression d'un item

1. **Entrée de palier (errorless)** : la commande correcte est montrée puis immédiatement restituée — pas d'échec au premier contact.
2. **Rappel actif (production)** : « écris la commande qui… », complétion de code, production depuis un énoncé — jamais de simple QCM de reconnaissance.
3. **Prédiction de sortie** : exécuter mentalement un court snippet. Format le plus « cognitif » du module — mémoire de travail et simulation mentale, dans la même logique que le soroban du cahier des charges.
4. **Interleaving** concepts/commandes une fois le socle acquis.

## Caps de complexité (garde-fou codé en dur)

- Phase initiale : **2 niveaux d'imbrication max** dans les snippets à prédire — imbriquer une boucle et une condition dépasse rapidement la mémoire de travail post-commotionnelle.
- Prérequis explicites via le graphe de connaissances (`backend/app/kg/`) : listes → compréhensions de liste, boucles → boucles imbriquées, fonctions → générateurs.

## Moteur

Identique aux autres modules : paliers Kumon-like (90 % × 3 sessions), FSRS, détection de fatigue. Aucun développement spécifique prévu.
