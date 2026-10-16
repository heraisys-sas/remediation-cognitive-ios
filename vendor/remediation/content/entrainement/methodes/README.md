# Module « Méthodes » (méthodes et stratégies — hors MDR)

**Principe** : choisir des stratégies pour retenir et organiser ses actions, puis pratiquer PQRST dans une séquence guidée. Les exercices inspirés d’une méthode ne constituent pas son protocole complet. Voir la [revue des tâches et libellés](../../../docs/20-specs/revue-libelles-quotidien-methodes.md).

| Palier | Méthode | Ce qui est entraîné |
|---|---|---|
| 1 | **PQRST** — Parcourir, Question, Lire, énoncer, Tester | mémoire de textes : **deux questions de mémoire par texte** |
| 2 | **Goal Management Training** — but, étapes, vérification | planification : choisir le plan d'étapes cohérent |
| 3 | **Auto-instruction** (Meichenbaum) — « qu'est-ce que je dois faire ? comment ? vérifie » | autorégulation : la question à se poser avant d'agir |
| 4 | **Vérification de plan** — le « V » de GMT | croiser les contraintes et choisir la seule étape à déplacer |
| 5 | **Repérer l'information** — attention sélective | chercher dans un document qui reste visible avec la question |

12 items au palier 1, 8 dans chacun des paliers 2 à 5 et 4 séquences au palier 6, soit **48 items**.

Ces six familles sont accessibles comme **parcours indépendants** : leur ordre dans le tableau décrit le corpus, pas une difficulté commune. En particulier, « PQRST guidé pas à pas » est directement accessible sans devoir maîtriser auparavant les QCM de planification ou de recherche documentaire.

## Comment c'est entraîné

- **PQRST** : le texte s'affiche temporisé (25 s), puis disparaît — la question est posée de mémoire (`affichage` mode `texte`). La consigne rappelle la méthode, c'est elle qui est retenue.
- **GMT** : la situation est donnée, la bonne réponse est le **plan d'étapes cohérent** (et non une étape isolée) ; la consigne invite à vérifier son plan.
- **Auto-instruction** : la bonne réponse est la **première question à se poser** (portant sur le but et le moyen), pas sur le résultat attendu.

Les paliers 1 à 5 proposent des réponses à choix ; le palier 6 comprend aussi des productions libres. Pour les paliers 1 à 5, la consigne stratégique reste consultable dans le panneau « Une méthode possible ». Au palier 6, les cinq étapes PQRST sont déjà affichées dans le composant guidé : aucun panneau supplémentaire ne les double. Le triptyque d'auto-instruction appartient à l'exercice qui l'entraîne et n'est plus imposé aux autres familles.

## Génération

`tools/generer_methodes.py` (déterministe, mélange isolé par famille). Relecture orthophoniste à faire.


## PQRST mis en œuvre (palier 6, ADR-015)

Un item = **une séquence guidée** sur un texte de quatre phrases : Parcours (jugé), **Question à écrire** (non notée, modèle affiché), Lecture (sans chronomètre), **Reformulation** (jugée à **4 idées sur 5**, résumé modèle montré), Test (2 questions de mémoire). Les idées sont définies par des formulations bornées et des contradictions propres au texte ; une idée composée peut exiger plusieurs sous-faits. Le retour distingue ce qui est retrouvé, contredit ou non reconnu. Les deux productions — sa question, sa reformulation — sont ce que le palier entraîne. La **fiche méthode** (5 lignes) est reprise au résumé de séance.

## Proposition en attente


## Révision du 30 septembre 2026

P2 à P5 : 32 nouveaux items `mt3-…` remplacent les anciens. Les plans ont des précédences explicites ; les documents de P5 restent consultables sans chronomètre. Les QCM de P2/P3 s’appuient sur des contraintes précises. Voir [ADR-019](../../../docs/30-technique/adr/ADR-019-plans-verifiables-et-documents-consultables.md).

## Ordre de présentation

La liste des parcours commence par **PQRST guidé pas à pas**, puis **PQRST — répondre de mémoire** : découvrir les étapes avant de les mobiliser avec moins de guidage. Les parcours restent indépendants et les numéros historiques des sources ne changent pas.
