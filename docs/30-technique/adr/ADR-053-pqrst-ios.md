# ADR-053 — PQRST guidé autonome

## Décision — 17 octobre 2026

Exposer `methodes/pqrst-guide` sans modifier le service, le correcteur, les
contenus ou FSRS importés au commit 44acda5. Le comportement de référence est
`frontend/src/exercises/sequence.js` de ce même commit, lu depuis Git.

L'adaptateur `mobile/pqrst_protocol.py` porte l'ordre P → Q → R → S → retour-S
→ T1 → T2 et les demandes de relecture. La page ne reçoit que les supports de
l'étape active. Les réponses P, Q, S et T initiales restent immuables dans la
trace ; les tentatives après relecture sont conservées séparément. Q reste sans
score. Le résumé modèle est présenté avant les deux tests, conformément à l'amont.

Chaque commande possède une révision et une identité de contenu. Un renvoi avec
un temps recalculé retrouve son résultat sans avancer ou ajouter de temps. Une
commande différente sur une ancienne révision est refusée. Le client relit
l'état durable après un retour perdu et retrouve la nouvelle étape.

Les transitions, les observations partielles validées par `observer` et le
checkpoint sont enregistrés ensemble dans SQLite. Seule l'action de correction
finale appelle `repondre`. Arrêter au milieu ne note pas la trace partielle.
La progression et les cartes sont isolées sous `methodes--pqrst-guide`.

Une pause cache les supports et conserve les brouillons dans la page. Une pause
pendant un appel est enregistrée après sa réponse. Si l'enregistrement échoue,
la reprise attend sa confirmation durable et le rappel reste caché. Après une
relance du processus, une étape active reprend en pause avec interruption notée ;
les brouillons en mémoire sont perdus. Le temps non validé n'est pas reconstitué.
Les checkpoints précédents Calcul/lexical restent lisibles.

## Vérifications et revue

- 36 tests Python d'adaptation/parité, 60 tests moteur et 13 tests JavaScript.
- Parité PQRST avec le service direct : feedback, résumé, maîtrise, FSRS et
  absence de baseline RT pour le protocole.
- Traces partielles sans progression, reprise après interruption, relectures et
  premières réponses, refus de correction anticipée, commandes périmées,
  idempotence avec temps différent, annulation d'une transaction simulée.
- Tests UI : brouillon/choix conservés en pause, supports masqués, refus de reprise
  si pause non enregistrée, synchronisation après retour perdu, résultat P visible
  et absence de compteurs lexicaux dans le résumé PQRST.
- Sol et Astra ont relu le lot ; leurs défauts reproduits sont corrigés et testés.
- La sonde native couvre neuf contrôles de persistance sur données temporaires.
  XCTest étend le pont réel WebKit → Python au parcours PQRST avec pause, brouillon,
  relecture, test final et retour P. L'exécution iOS du commit reste à confirmer
  dans la CI, séparément des tests sur Mac et de la compilation.

La recette sur appareil physique et la voix/dictée restent à effectuer. Aucun
historique personnel ni donnée du dépôt source n'est importé ou réinterprété.
