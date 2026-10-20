# Module « Au quotidien » (remédiation fonctionnelle — hors MDR)

**Principe** : situations courantes pour rappeler une information ou choisir une stratégie. Les choix sur écran ne démontrent pas leur mise en œuvre dans la vie réelle. Voir la [revue des tâches et libellés](../../../docs/20-specs/revue-libelles-quotidien-methodes.md).

## Familles et paliers

| Palier | Famille | Objectif proposé | Exemple |
|---|---|---|---|
| 1 | **Retenir un message** | rappel d’une information | retenir *qui / quoi / quand*, puis répondre de mémoire |
| 2 | **Étape suivante** | planification | choisir la prochaine étape d'une tâche |
| 3 | **Estimation de durée** | anticipation | « combien de minutes pour… », accepté dans une fourchette |
| 4 | **Par où commencer** | initiation | la première action qui débloque la suite |
| 5 | **Prévoir un rappel** | choisir une routine ou un repère | accrocher l'action à un repère précis (implémentation d'intention) |
| 6 | **Meilleure solution** | résolution de problème | l’action qui répond au problème et aux contraintes indiquées |
| 7 | **Aide externe adaptée** | mémoire prospective | choisir le bon support, au bon endroit, au bon moment |
| 8 | **Prioriser quand le temps manque** | organisation | choisir l’essentiel quand le temps presse |

88 items au total (12, 12, 12, 12, 12, 12, 8, 8).

## Pourquoi pas d'exercice chronométré « de vitesse »

La vitesse de traitement ne s'entraîne pas en accélérant sous contrainte : les exercices chronométrés sont fatigants, anxiogènes, et leur transfert est faible. Ce qui aide en situation, c'est de **gérer la demande** — simplifier, prioriser, préparer à l'avance. C'est l'objet du palier 8 (gestion de la pression temporelle, inspiré du *Time Pressure Management*), cohérent avec le garde-fou « on ne chronomètre pas le rappel ».

## Aide externe : la règle enseignée

Une bonne aide est **au bon endroit, au bon moment, et visible juste avant l'action** : l'alarme réglée pour jeudi 20 h, un rappel fixé près de la poignée sans encombrer le passage, le dossier près des clés. Compter sur sa mémoire ou noter dans un carnet qu'on ne relit pas ne sont pas des aides.

## Réponses attendues

Choix parmi les propositions (comparaison tolérante) ; l'estimation de durée est acceptée dans une fourchette ; la prise de message tolère nombres en lettres ou en chiffres et les écritures d'heure (« deux » = « 2 », « 14 h 30 » = « 14h30 » = « 14:30 »).

## Génération

`tools/generer_quotidien.py` (déterministe). Relecture orthophoniste à faire.

## Révision du 30 septembre 2026

64 items de P2/P4/P5/P6/P7/P8 remplacés (`qo2-…`) : contraintes explicites, choix liés à la même situation, repères événement-action pour P5 et supports externes pour P7. Les messages et estimations de durée ne sont pas modifiés. Voir [ADR-019](../../../docs/30-technique/adr/ADR-019-plans-verifiables-et-documents-consultables.md).
