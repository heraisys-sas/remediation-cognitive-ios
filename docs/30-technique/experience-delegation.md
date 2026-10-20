# Essai de délégation — Comparer des documents

20 octobre 2026. Objectif : évaluer un intermédiaire produisant du pseudo-code
pour un agent moins coûteux, face à une réalisation directe de difficulté égale.

## Protocole

Même exercice réel, même référence amont, même cahier des charges figé,
même interface de mixin Python et de rendu JavaScript. Deux réalisations séparées,
sans échange de code entre candidats. Les candidats ne modifiaient pas le runtime
racine ; la même adaptation de test était appliquée aux deux. Les tests communs
ont été écrits indépendamment des tests produits par les candidats.

| Voie | Modèle et effort | Durée active observée |
| --- | --- | --- |
| Directe | gpt-6-luna, high | 166 s (2 min 46) |
| Pseudo-code | gpt-6-sol, medium | 82 s |
| Réalisation guidée | gpt-6-luna, high | 173 s |
| Chaîne guidée totale | pseudo-code puis réalisation | 255 s (4 min 15) |

La voie directe a travaillé de 13:27:45 à 13:30:31 UTC ; le pseudo-code de
13:28:01 à 13:29:23 ; la réalisation guidée de 13:29:52 à 13:32:45.
La chaîne guidée prend 284 s de temps écoulé si l’on inclut les 29 s de dispatch.
Ces mesures excluent le brief commun, l’intégration, les tests externes,
la revue et les corrections finales. Ce n’est donc pas une mesure du coût total.

## Résultats

Les 12 cas d’acceptation communs donnent 11/12 pour la version directe et 12/12
pour la version guidée. La version directe accumulait le temps de réponse du
premier item dans celui du suivant (100 puis 200 devenaient 100 puis 300 ms).
Les tests de chaque candidat seuls n’avaient pas révélé cette différence.

La version guidée a été retenue. Une revue complémentaire a trouvé un bouton
restant désactivé après un rendu pendant une requête ou une reprise ; le correctif
et un test JavaScript sont dans le code intégré. Les deux voies ont donc nécessité
une correction. Le succès des tests Python ne suffit pas pour comparer la qualité
complète des interfaces.

## Interprétation

Sur cet échantillon, le pseudo-code n’a pas raccourci la durée de production.
Il a accompagné une meilleure isolation du temps entre items, mais un seul exercice
ne permet pas d’attribuer causalement ce résultat à la méthode. Les tokens facturés,
les tarifs effectifs et le coût des corrections par voie ne sont pas disponibles :
**aucune économie financière démontrée**. Un essai ultérieur devrait répéter les
paires sur plusieurs exercices, comptabiliser les tokens et mesurer jusqu’à
l’acceptation finale avec audit et tests UI identiques.

Les snapshots bruts, le brief, le pseudo-code et les tests communs sont conservés
localement dans `.local/comparison-experiment/` ; ils ne sont pas du code livré.
Le code retenu et corrigé est dans `mobile/comparison_runtime.py` et
`mobile/ios/pilot/comparison.js`, avec ses tests dans `tests/`.
