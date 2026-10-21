# Recette et ergonomie — 21 octobre 2026

Ce lot corrige deux défauts trouvés lors de la revue des 36 parcours et réduit les
commandes secondaires visibles. Le moteur, ses contenus, les correcteurs et les
historiques restent inchangés.

## Corrections

- **Refaire le chemin** : la classe appliquée pendant la présentation ne
  correspondait à aucun style. La case active reçoit désormais la surbrillance
  définie dans la feuille de style, puis la perd pendant l’intervalle.
- **Les quatre mémoires immédiates** : la suite automatique exigeait `item`,
  alors que ces protocoles identifient l’essai par `item_id`. Le retour avance
  désormais automatiquement, avec possibilité de choisir « Prendre le temps »
  ou de demander l’essai aidé avant le passage. Le maintien du retour est lié à
  l’essai et à la phase, pas à la révision d’une interruption.
- **PQRST guidé** : les informations intermédiaires sur le sujet attendu et la
  question modèle avancent seules après un délai lisible. Lecture, résumé modèle
  et relecture conservent une commande explicite, pour laisser lire et mémoriser
  à son rythme. Les aides à la relecture sont regroupées dans un volet fermé.
- **Toutes les questions** : la méthode se referme à la nouvelle question mais
  conserve son ouverture sur le même item. « Terminer et enregistrer » reste
  accessible dans « Options de la séance ». Le texte d’introduction de l’accueil
  est masqué pendant une activité. Aucun bouton Pause ajouté aux exercices sans
  temps imposé ; la gestion des interruptions demeure active.
- Les boutons secondaires des mémoires immédiates utilisent le même style que
  ceux des autres parcours. Une ancienne proposition d’arrêt d’activité classique
  ne reste plus affichée dans un bloc de mémoire immédiate.

Les retours ont un délai calculé selon le texte, de 2,2 à 12 secondes, avec au
moins quatre secondes pour une réponse incorrecte. Une lecture audio en cours
retarde la suite. « Prendre le temps » permet de lire sans limite.

## Validation

- 213 tests Python réussis, dont démarrage des 32 parcours classiques avec les
  contenus réels, tests de correction/parité par famille et blocs complets des
  quatre mémoires immédiates. Ce sont des contrôles du moteur et des adaptateurs,
  pas une recette visuelle de 36 parcours.
- 64 contrôles JavaScript réussis : huit nouveaux scénarios vérifient les quatre
  retours de mémoire immédiate, la surbrillance du chemin, les transitions PQRST,
  la fermeture des méthodes et les commandes repliées.
- Empreintes `UPSTREAM.json` conformes au commit `44acda5`.
- Nouvelle vérification XCTest : surbrillance effective du chemin par comparaison
  des couleurs calculées dans WebKit, rappel après masquage, commande de maintien
  accessible et passage automatique au prochain essai. Dix tests natifs réussis sur iPhone Air (59,1 secondes, zéro échec), dont ce
  scénario et la conservation de la première réponse lors de l’essai aidé.
  Preuve locale : `.local/ergonomie-device.xcresult`.
- GitHub Actions : moteur et noyau simulateurs iPhone 17/Air réussis ; pilote
  iPhone Air réussi. Le pilote iPhone 17 échoue dans le scénario de test lors
  du passage de Contextes aux stratégies (bouton absent). Le test attend désormais
  la fin des écritures asynchrones avant ses commandes de clôture/démarrage ;
  cette correction du scénario reste à confirmer sur le runner.

## Recette encore nécessaire

La suite précédente comporte neuf tests natifs réussis sur iPhone Air. Elle ne
valide pas exhaustivement les 36 parcours. Pour chaque famille, restent à
observer le confort de lecture, le clavier, les retours et l’accès aux aides à
plusieurs tailles de texte. VoiceOver, iPad, casque réel, latence vocale perçue et
mode avion restent à recetter. Ne pas déduire leur validation des tests sur Mac.

L’audit final indépendant du lot précédent reste incomplet après interruption
par quota. Ce lot a reçu une revue locale et des tests de régression ; il ne
constitue pas cette revue indépendante manquante.
