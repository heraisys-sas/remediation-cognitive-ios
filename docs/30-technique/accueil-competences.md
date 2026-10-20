# Accueil par compétences et cartes

Les paramètres de l’accueil permettent de cocher plusieurs compétences. Sous chaque choix, une description courte précise la tâche et la liste des cartes affichées. Le choix est enregistré localement dès modification. Sans préférence antérieure, toutes les activités disponibles sont proposées ; un choix explicitement vide reste vide et invite à revenir aux paramètres.

Chaque carte lance directement une séance du parcours associé. Les préférences changent uniquement la visibilité sur l’accueil : elles ne sélectionnent aucun niveau, ne modifient aucun résultat, aucune progression et aucun historique. Une séance en cours reste accessible même si une préférence antérieure ne concerne pas son activité.

## Classement

| Compétence affichée | Cartes disponibles |
| --- | --- |
| Calculer de tête | Calcul mental |
| Retrouver les mots | Retrouver le mot |
| Retenir et manipuler des informations | Chiffres dans l’ordre ; Chiffres en ordre inverse ; Suites de mots ; Associations mot–nombre ; Position dans une séquence |
| Associer une information à son contexte | Retrouver le contexte |
| Préparer et vérifier une action | Choisir un plan ; Se guider avant d’agir ; Vérifier un plan |
| Repérer une information | Chercher dans un document |
| Lire et retenir un texte | Lire avec PQRST, pas à pas |

Les intitulés décrivent une pratique, sans présenter les résultats comme une mesure de capacité globale. Les cartes précisent ce que la personne fait : chiffres/mots lus à l’écran, rappel direct ou inverse, choix de stratégie parmi des propositions, document consultable, reconnaissance du contexte et rappel PQRST après un résumé modèle. Les exercices seulement spécifiés dans le dépôt source ne sont pas annoncés comme disponibles.

## Sources éditoriales

Dépôt macOS `heraisys-sas/remediation-cognitive`, référence du portage `44acda5` :

- `docs/20-specs/corrections-exercices-existants.md` : tableau des tâches réelles et conditions de présentation.
- `docs/10-clinique/referentiel-exercices.md` : distinction rétention immédiate, ordre, manipulation et associations ; statuts des propositions.
- `docs/30-technique/adr/ADR-042-cadre-cognitif-et-autoevaluation.md` : pratique et observation distinguées.
- `content/entrainement/{memoire,methodes,evocation,calcul-mental}/README.md` : déroulement et limites de chaque famille.

Relecture Astra : classement des 7 compétences et 13 cartes cohérent ; descriptions de Contextes, PQRST et Position précisées selon ses observations. Cette relecture éditoriale ne constitue pas une validation clinique.

## Implémentation et contrôles

`home.js` contient les libellés et les correspondances. Les préférences natives `RCEnabledCompetenciesV1` ne contiennent que des identifiants de compétences, validés contre une liste fermée ; liste vide autorisée, doublons et identifiants inconnus refusés. La voix conserve sa préférence indépendante. Aucun contenu de séance n’est transmis au pont de préférences.

53 tests JavaScript réussis, dont couverture unique des 13 parcours, filtre, liste explicative, choix vide, sauvegarde refusée, démarrage direct, protection d’une séance en cours et éléments absents du DOM. L’audit Sol a relevé l’accès à des cartes non montées ; les mises à jour vérifient maintenant l’existence des commandes. Un test natif vérifie également le filtre et la persistance dans le véritable DOM WebKit, en restaurant les préférences initiales.

## Exécution sur iPhone Air — 20 octobre 2026

Huit XCTest réussis, zéro échec, dont le filtre réel WebKit (2 cartes, puis 1, puis aucune), la sauvegarde/relecture des préférences et le démarrage direct d’une séance depuis une carte. Le moteur embarqué conserve ses 20 contrôles réussis. Preuves locales : `.local/home-competencies-final-device.log` et `.local/home-competencies-final-device.xcresult`. Une première exécution avait conservé l’attente de l’ancien titre d’accueil dans un test ; cette attente a été mise à jour avant l’exécution complète réussie.

La vérification visuelle via navigateur local n’a pas pu être exécutée, le navigateur refusant les URL `file:` ; aucune capture visuelle de l’accueil n’est revendiquée. L’ergonomie perçue reste à confirmer à l’usage sur l’iPhone.
