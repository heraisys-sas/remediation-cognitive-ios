# ADR-052 — Accès lexical autonome sur iOS

## Décision — 17 octobre 2026

Exposer le parcours existant `evocation/acces-lexical` dans le pilote, avec
sélection d'activité hors séance. Le service, la banque, leurs identifiants,
les corrections et FSRS restent ceux de `UPSTREAM.json` (44acda5).

L'adaptateur conserve le parcours dans le checkpoint, retrouve la séance active
avant tout nouveau démarrage et déduit le thème des commandes de cette séance.
Les anciennes sauvegardes de calcul sans clé `activity` restent lisibles.
Les historiques lexicaux utilisent la clé amont `evocation--acces-lexical`.

Les indices sont révélés un à un et leur nombre est sauvegardé avant retour à
l'interface. La validation transmet ce nombre au service ; l'affichage du mot
transmet `nombre_indices + 1` et clôt l'item comme assisté. La première réponse
et le niveau d'aide conservent l'autorité sur progression, FSRS et baseline RT.
Une reprise après erreur continue de montrer la réponse déjà fournie.

La page ouverte hors du conteneur natif affiche une explication de lancement.
Le moteur ne reçoit aucun remplacement de démonstration dans le navigateur.

## Vérification

- 31 tests Python d'adaptation/parité et 60 tests du noyau passent sur Mac.
- 7 tests JavaScript passent, dont indices gradués et absence de pont natif.
- La parité lexicale compare correction, résumé, maîtrise, temps de référence,
  stabilité, difficulté et échéance FSRS avec un service amont direct.
- Restauration des indices, affichage assisté, clôture répétée, commande périmée
  et séparation des activités sont vérifiés sur données synthétiques.
- Compilation `build-for-testing` arm64 simulateur, cible iOS 26 : réussie.
- XCTest étend le contrôle du pont réel au choix lexical, à un indice et à
  l'affichage assisté. La sonde Python native contrôle également la restauration.
  L'exécution iOS est à vérifier dans la CI du commit, séparément de la compilation.
- Les artefacts du workflow incluent explicitement les chemins cachés `.local`
  (liste de fichiers de preuve uniquement), auparavant ignorés par upload-artifact.

Sol a approuvé le code métier et ses tests. Recette physique, saisie vocale,
VoiceOver et confort réel restent à effectuer. Contextes, PQRST, SFA et PCA ne
sont pas rendus accessibles par ce lot.
