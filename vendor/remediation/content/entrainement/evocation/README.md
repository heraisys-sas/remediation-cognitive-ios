# Module « Retrouver le mot » (évocation — hors MDR)

**Principe** : entraîner l'**accès** à ce qui est déjà su. L'information est présente en mémoire, mais le chemin pour la retrouver est encombré : au lieu de réapprendre, on s'entraîne à déclencher le rappel avec de moins en moins d'aide. C'est le pendant pratique de la récupération indicée et de l'apprentissage sans erreur.

## Familles

- **Reconnaissance** (palier 1, 5) : la définition est affichée, la réponse se choisit parmi trois mots de la même famille — cran le plus facile, pour entrer sans échec.
- **Rappel indicé** (paliers 2, 3, 5) : la définition est seule ; l'utilisateur demande des indices **un par un** (catégorie → attaque phonologique → forme écrite). Le dernier cran affiche la réponse : l'essai se clôt alors **sans erreur** (le moteur l'enregistre comme non retrouvé, sans jamais signaler un échec).
- **Rappel de la source** (palier 4) : une fiche (contexte + information) est affichée de façon temporisée ; le stimulus disparaît, la question porte sur **le contexte dans lequel l'information a été vue** — entraîne la mémoire de la source.

Ces familles ne forment plus une échelle unique. L'accès lexical, la mémoire de la source, SFA et PCA sont quatre parcours indépendants. Le mode automatique de l'accès lexical commence par le rappel avec indices facultatifs ; le QCM de reconnaissance reste accessible au palier d'essai 1. SFA et PCA sont des stratégies proposées, jamais des passages obligatoires pour progresser en accès lexical.

## Structure

Le parcours **Retrouver le mot** comporte douze paliers de 24 mots :

1. QCM de soutien, mots usuels adultes.
2. Objets familiers — départ automatique, réponse orale ou clavier.
3. Mots précis et documents.
4. Notions courantes en contexte.
5. Verbes utiles dans les démarches et le travail.
6. Mots à mobiliser dans une situation courte.
7. Culture générale courante : arts, sciences, société.
8. Concepts de culture générale plus précis.
9. Nuances de langue soutenue.
10. Verbes de précision et d'argumentation.
11. Interprétation et raisonnement.
12. Nuances soutenues dans des situations discriminantes.

Les banques sont dans `palier-08..19.json`, avec identifiants `ev2-…` ; leurs numéros internes sont remappés en paliers 1–12 du parcours. Les fichiers 1–7 restent conservés pour les historiques et les autres parcours. Les séances contiennent 10/10/10/8/8/6 questions aux six premiers paliers, puis six questions à chaque palier supérieur selon le niveau, jamais les 24 mots d'un palier en une seule séance. La durée dépend du besoin d'indices et du rythme de la personne.

La difficulté n'est pas une échelle clinique : un terme inconnu ne témoigne pas d'une panne d'accès lexical. La progression relève de la familiarité, de la précision et de la formulation, sans imposer du jargon. Définitions et variantes sont à relire avec l'orthophoniste.

La banque source est `tools/banque_lexicale_adulte.json`. `python3 tools/generer_lexical_adulte.py` régénère uniquement l'extension. Le générateur général intègre aussi cette banque.

## Réponses attendues

- texte, comparé **sans tenir compte de la casse, des accents, des espaces et des guillemets** : un mot juste écrit sans accent reste juste (l'objectif est le rappel, pas l'orthographe) ;
- pour les items à choix, la réponse est la proposition sélectionnée.

## Garde-fous du contenu

- **Aucun indice ne contient la réponse** — contrôle automatisé dans `tools/validate_items.py` ; la révélation complète est un mode d'interface, pas un indice de plus.
- Les indices sont hiérarchisés et facultatifs : demander de l'aide fait partie de l'exercice, il n'y a pas de pénalité.
- Mesure utile côté séance : nombre d'items retrouvés **sans aide** (`resume.sans_aide`) et essais clos par affichage (`resume.assistees`).

## Génération

Contenu rédigé puis assemblé par `tools/generer_evocation_social.py` (déterministe, graine 20260920). Toute retouche manuelle met à jour `meta.relecture_ortho` ; la relecture orthophoniste formelle reste à faire.

## Analyse du mot : SFA et PCA (paliers 6 et 7)

L'enrichissement « remédiation » du manque du mot : au lieu de recevoir des indices, **l'utilisateur génère lui-même les attributs** du mot, puis le nomme. C'est le mécanisme actif des deux méthodes classiques de l'aphasiologie.

- **Palier 6 — SFA** (analyse sémantique) : à partir d'une définition, l'utilisateur décrit le mot par sa catégorie, son usage, le lieu où on le trouve, ce à quoi il pense — puis tape le mot.
- **Palier 7 — PCA** (analyse phonologique) : même principe, mais l'analyse porte sur les sons — premier son, nombre de syllabes, rime, dernier son — puis le mot.

Les notes saisies dans les étapes ne sont **pas** évaluées (elles ne servent qu'à débloquer le mot) : seule la réponse finale est corrigée, avec la tolérance habituelle (casse, accents). Cette absence de notation est volontaire : l'objectif est la génération des attributs, pas leur exactitude.

## Appuis et limites de la conception

Une réflexion ciblée GPT‑6 Astra a été relue pour construire la banque. Les recommandations INCOG 2.0 privilégient les objectifs individualisés et pertinents en situation ; leur population principale est celle des traumatismes modérés à sévères, et non un public post-commotionnel homogène. [Togher et al., 2023](https://pubmed.ncbi.nlm.nih.gov/36594860/).

Les difficultés lexicales après traumatisme léger peuvent être subtiles et dépendantes de la tâche ; une petite étude ne valide pas le présent classement. [King et al., 2006](https://pubmed.ncbi.nlm.nih.gov/16809205/).

Les travaux sur récupération active et espacement en aphasie concernent les mots entraînés et ne démontrent pas ici un transfert conversationnel post-commotionnel. [Middleton et al., 2019](https://pubmed.ncbi.nlm.nih.gov/31408823/).

## Retrouver le contexte — scènes illustrées (8 octobre 2026)

Les dix messages du palier 4 sont montrés dans des scènes générées. La phrase de contexte est remplacée par l’image ; le message seul est aussi transcrit pour rester lisible sur petit écran. « Afficher » révèle la scène pendant 12 secondes après son chargement ; image et transcription disparaissent avant le rappel.

Nouveaux IDs `ev-4-source-image-v1-*`, aucun changement des messages ni de leurs réponses. Correspondance et assets : `frontend/images/contextes/manifest.json`. Voir ADR-035. Ne pas régénérer tout le thème pour mettre à jour ces scènes.
