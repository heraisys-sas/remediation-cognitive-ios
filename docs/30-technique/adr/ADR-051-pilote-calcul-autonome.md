# ADR-051 — Premier parcours autonome et sauvegarde transactionnelle

16 octobre 2026. Statut : pilote de développement, pas livraison clinique.

## Contexte

L'audit souligne que `engine/` ne contient pas les règles applicatives complètes.
La correction et l'application de FSRS résident dans le service Python amont.
Sa persistance JSON historique est atomique par fichier, pas pour la clôture
complète et le checkpoint mobile réunis.

## Décision

Importer le service, ses correcteurs et ses dépendances Python pures sans
modifier les algorithmes. Le seul marqueur de package adapté évite l'import
de FastAPI. Premier parcours exposé : Calcul mental. Les contrats Contextes et
PQRST sont testés séparément avant tout futur élargissement de l'interface.

Réutiliser les formats métier du stockage JSON à travers un adaptateur SQLite.
Chaque commande locale inclut la mise à jour métier et le checkpoint dans une
transaction unique. L'état mémoire est reconstruit depuis le dernier checkpoint
au début de la commande : une écriture échouée ne laisse pas le moteur mémoire
en avance sur le stockage. Clôture et renvoi de réponse sont idempotents.

Le checkpoint est explicitement lié aux structures internes du service et du
runner ; il porte un schéma et la référence amont. Aucun pickle, eval ou code
téléchargé. Une autre référence demande une migration, jamais une
réinterprétation silencieuse des historiques.

## Conséquences

Le pont de faisabilité est Objective-C/C API Python, dans une file GCD sérialisée.
Il remplace le transport HTTP, pas les règles métier. L'interface HTML locale
est sobre et adaptable, avec origines et actions bornées. Une saisie validée
est durable avant retour au client ; un brouillon non validé peut être perdu.
Le pilote reste au clavier : voix et dictée doivent être développées et testées
sur appareils réels dans un lot suivant. Le stockage est dans le conteneur de
l'app, protégé par iOS et exclu de la sauvegarde iCloud pour ce pilote.

La CI du noyau et celle du parcours sont distinctes : tests desktop, exécution
Python sous iOS, pont WebKit, service et sauvegarde. Aucun succès simulateur
ne démontre le confort réel, le micro ou les performances sur iPhone physique.
