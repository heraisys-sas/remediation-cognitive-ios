# ADR-050 — Expérimenter le moteur Python embarqué sur iOS

16 octobre 2026. Statut : expérimentation autorisée, architecture finale à confirmer.

## Contexte

L'utilisateur autorise une première version autonome, sur iPhone 17 et Air,
avec extension de compatibilité selon les capacités Apple. Voix et dictée doivent
s'exécuter sur l'appareil. Le moteur de séances et FSRS existe en Python pur ;
réécrire immédiatement ses règles en Swift créerait un risque de divergence.

## Décision

Éprouver CPython embarqué dans une app XCTest avant tout portage Swift.
La même suite `engine/tests` est copiée dans le bundle et exécutée sans HTTP.
Le runtime et les dépendances restent isolés dans `.local` du checkout iOS.
Le runtime macOS installé et les checkouts actifs ne sont pas modifiés.
Le banc d'essai ne copie aucun stockage personnel.

## Conséquences

Cette étape vérifie le packaging et prépare la preuve d'exécution iOS ; elle ne
livre pas encore un parcours, des correcteurs mobiles, une interface, une
persistance mobile, la voix ou la dictée. Une compilation n'est pas une preuve
d'exécution. Le choix Python/Swift reste conditionné aux mesures sur appareils.
Les APIs HTTP et les règles du moteur ne changent pas. Contextes conserve le
rappel final comme seule source de progression et PQRST son protocole séquencé.
PCC est optionnel pour l'accompagnement et ne fait pas partie du moteur autonome.
