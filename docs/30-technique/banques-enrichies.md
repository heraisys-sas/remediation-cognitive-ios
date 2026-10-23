# Banques enrichies — issue #17

Import partiel exact de 35 fichiers depuis `heraisys-sas/remediation-cognitive@0ed9207e3dc7d13f03b0e283d34d1d627ab72fdd` : 13 JSON de contenu, un catalogue, le manifeste Contextes et 20 WebP. Origine par fichier et empreintes dans UPSTREAM.json ; moteur, FSRS et service inchangés.

90 nouveaux exercices : Contextes 10, SFA 12, PCA 12, Garder le cap adapter 8 et vérifier 8, PQRST guidé 8, séries lues 16 et entendues 16. Aucun ancien exercice supprimé ou modifié. Les huit changements de métadonnées de palier concernent leurs compteurs. Le contenu conserve son statut source de relecture ; il ne s’agit pas d’une validation clinique.

Le catalogue limite Contextes à dix scènes par séance dans une banque de vingt, avec découverte puis rappel final seul pris en compte pour la progression. Les anciens identifiants et ressources restent présents. Le moteur de correction et les formats d’historique sont conservés ; aucune migration ni réinterprétation des anciennes séances.

Les 16 nouvelles séries entendues réutilisent 43 mots dont les fichiers audio sont déjà embarqués. Les 20 images nouvelles et leurs variantes 640/960 sont copiées par la préparation native existante. Aucun téléchargement n’est nécessaire pour accéder aux contenus.

Validation ordinateur : 238 tests existants réussis, quatre nouveaux contrôles d’intégrité et ressources réussis ; 72 contrôles JavaScript. Le manifeste de référence figé vérifie les 50 anciens exercices des banques modifiées, inchangés, et les 90 ajouts. Toutes les images principales correspondent à leur SHA-256 et les ressources audio référencées existent. Le test natif supplémentaire demande le décodage des 20 nouveaux WebP dans WebKit. La recette physique de tous les nouveaux exercices et la relecture des rédactions restent distinctes.

Revue indépendante favorable : fichiers importés identiques à la source figée, dépendances déjà présentes, aucune modification supplémentaire des adaptateurs requise. Aucune fusion ni publication automatique.
