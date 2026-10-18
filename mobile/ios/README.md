# Moteur embarqué et parcours autonomes

Cible produit : iPhone 17 et iPhone Air, puis iPad et extension selon capacités.
Le pilote propose Calcul mental, Retrouver le mot, PQRST guidé et Retrouver le contexte avec le moteur
Python dans le processus de l'app. Il fonctionne sans FastAPI, Mac serveur,
Cloudflare ou appel PCC. La saisie est au clavier. Les étapes ci-dessous
conservent aussi l'historique de la première preuve XCTest.

## Validation du 16 octobre 2026

- Les 60 tests du moteur passent sur le Mac et dans GitHub Actions (Linux).
- `build-for-testing` réussit pour iOS Simulator arm64, cible iOS 26,
  avec le SDK iOS 27.1 et Python 3.13.16.
- La sonde corrigée a exécuté ses 60 tests sous iOS 26.5 sur simulateurs
  iPhone 17 et Air dans [GitHub Actions](https://github.com/heraisys-sas/remediation-cognitive-ios/actions/runs/38957640524).
  Aucun essai sur iPhone physique n'est revendiqué.
- La compilation inclut le moteur Python et FSRS, pas les correcteurs backend,
  les items, la persistance mobile ou les capacités vocales.

## Préparer

Utiliser Python 3.13 dans un environnement isolé avec `requirements-test.txt`.
Le verrou `probe-lock.json` fixe le runtime, l'archive et l'arbre extrait ainsi
que les wheels de toutes les dépendances de test, avec leurs empreintes SHA-256.
L'expérimentation utilise Python-Apple-support 3.13-b16 (Python 3.13.16).
Le runtime reste ignoré par Git ; aucun binaire n'est commité.

```sh
python -m pip download --no-deps -r requirements-test.txt --dest .local/locked-wheels
python tools/ios/fetch_runtime.py
python tools/ios/prepare_engine_probe.py --support .local/ios-python
```

La préparation refuse d'écraser un projet existant. Elle copie uniquement
`engine/`, la sonde et les dépendances Python pures de test. Elle ne copie ni
`backend/data`, ni les environnements locaux, ni les réglages du navigateur.
Le préparateur ne copie aucun paquet de l'environnement du poste : il extrait
seulement les wheels vérifiés. Le manifeste conserve versions, empreintes du
bundle et des paquets, référence amont et commit iOS.

## Vérifier

Sur le poste, avant essai iOS :

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=mobile/ios python -m probe
```

Compiler l'app et la suite pour simulateur, sans compte Apple :

```sh
xcodebuild build-for-testing \
  -project .local/engine-ios-probe/iOSTestbed.xcodeproj \
  -scheme iOSTestbed -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .local/ios-derived ARCHS=arm64 \
  IPHONEOS_DEPLOYMENT_TARGET=26.0 CODE_SIGNING_ALLOWED=NO \
  EXPANDED_CODE_SIGN_IDENTITY=-
```

Pour exécuter, il faut un runtime simulateur installé et un appareil simulé
disponible. Ouvrir le projet généré dans Xcode, choisir iPhone 17 ou Air et lancer
Product > Test. Sur appareil réel, une signature de développement est nécessaire.
Vérifier dans la sortie `platform: ios`, puis tous les tests moteur réussis.
Une compilation seule **ne prouve pas** le fonctionnement sur iPhone.
La commande cible un Mac Apple Silicon. Pour un Mac Intel, remplacer `arm64`
par `x86_64`. Le tiret impose la signature ad hoc des extensions Python du
banc d'essai ; aucun certificat personnel n'est utilisé pour le simulateur.

Le workflow `Exécution moteur sous iOS` prépare et exécute la sonde sur des
simulateurs iPhone 17 et Air équipés d'iOS 26 ou ultérieur. Les logs, résultats
XCTest et manifeste sont conservés comme artefacts. L'absence de runtime,
l'échec d'exécution ou un nombre différent de 60 tests réussis fait échouer
la vérification. Le lancement neutralise les options/plugins pytest externes.
Cela ne remplace pas la recette sur un iPhone physique.

## Critères de décision

- Même suite adaptatif/maîtrise/séances/fatigue/FSRS/UTC sur ordinateur et iOS.
- Exécution dans le processus de l'app, réseau désactivé ; pas de sous-processus.
- Emballer ensuite un parcours complet avec ses correcteurs et ses items réels.
- Mesurer démarrage, mémoire et réactivité sur iPhone 17 et Air.
- Tester sauvegarde, interruption et restauration dans un stockage d'essai séparé.
- Voix et dictée natives restent une étape à développer et à essayer au micro réel.
- Aucun résultat du modèle génératif ne remplace une correction déterministe.
- Vérifier licences, frameworks signés et règles Apple avant distribution.

## Parcours du pilote

```sh
python tools/ios/prepare_pilot.py
python tools/ios/run_simulator_probe.py --device 'iPhone 17' --probe .local/calculation-pilot
```

Le projet généré `.local/calculation-pilot/iOSTestbed.xcodeproj` construit une
app appelée « Remédiation ». L'interface WKWebView n'a accès qu'à ses fichiers
locaux ; son pont appelle le service Python dans une file native sérialisée.
Il n'y a ni serveur, ni tunnel, ni appel PCC. La saisie est au clavier.

Le choix d'activité est disponible avant le démarrage et après la clôture. Une
séance active est reprise avec son parcours d'origine. Retrouver le mot utilise
le parcours amont `evocation/acces-lexical` et son départ automatique au palier 2.
Les indices sont facultatifs, progressifs et sauvegardés. « Afficher le mot et
continuer » clôt l'essai comme assisté selon le service d'origine : le mot affiché
ne devient pas une récupération sans aide. Les historiques et cartes sont
séparés sous `evocation--acces-lexical`, sans modifier ceux du calcul.

Le fichier HTML ouvert directement dans un navigateur explique maintenant qu'il
faut lancer l'app native. Il n'exécute pas un moteur de démonstration.
Pour conserver un projet déjà configuré dans Xcode, générer un autre projet avec
`python tools/ios/prepare_pilot.py --destination .local/lexical-pilot`.

PQRST guidé utilise le parcours `methodes/pqrst-guide`. Le séquencement local
présente P, Q, R, S, le retour avec résumé modèle, puis deux questions T sans
rouvrir le support. Les premières réponses sont conservées séparément des essais
après relecture. La question Q est enregistrée sans score ; les corrections de
reformulation restent limitées aux idées reconnues par le correcteur amont.

Chaque transition conserve une observation partielle et sa position dans la même
transaction SQLite. Ces traces ne créent aucune correction, progression ou carte
FSRS. La correction complète est demandée explicitement après les deux tests.
Une clôture anticipée conserve les observations partielles sans les transformer
en réponses. L'historique est séparé sous `methodes--pqrst-guide`.

Les brouillons PQRST et les choix non validés survivent aux pauses dans la page,
mais restent en mémoire : une fermeture du processus ne les sauvegarde pas.
Une relance retrouve l'étape validée et demande une reprise explicite ; une
interruption au rappel est signalée dans l'observation. L'interface reste masquée
si l'enregistrement d'une pause échoue. Le temps actif est conservé par segments
validés ; le segment perdu lors d'un arrêt du processus n'est pas reconstitué.

Le service, les correcteurs et les items viennent du commit source enregistré
dans `UPSTREAM.json`. Le point d'entrée de package a été adapté pour ne pas
importer les routes FastAPI. Les fonctions d'accompagnement macOS ne sont pas
appelées par le pilote.

Les réponses validées et la position sont enregistrées dans une transaction
SQLite, avec les effets de clôture sur la maîtrise et FSRS. Une relance retrouve
la séance ; les brouillons non validés ne sont pas sauvegardés. Une sortie en
arrière-plan masque l'exercice et demande une reprise explicite ; le temps
d'interruption n'est pas présenté comme une mesure continue. Le compteur de
dosage n'est pas incrémenté une seconde fois lors de la reprise.

L'adaptateur de sauvegarde est lié à la version du service : les états actifs
d'une autre référence amont sont conservés et refusés, en attendant une
migration explicitement testée. Aucun historique personnel n'est importé.

Les tests du pilote couvrent correction, sauvegarde/relecture, clôture
idempotente et transaction annulée. PQRST compare aussi les traces partielles,
premières réponses, essais aidés et résultats au service amont. Le parcours
Contextes compare aussi les deux passes, les premières réponses et la progression
au service amont. Sous iOS, le
workflow vérifie aussi le pont réel WebKit→natif→Python et conserve une capture
de l'écran initial. Un passage sur iPhone réel, le clavier, VoiceOver, les
grands caractères et le confort en séance restent nécessaires.

## Portage Contextes — lot du 18 octobre 2026

« Retrouver le contexte » reprend `evocation/memoire-source`. Une première passe
montre chaque scène locale pendant la durée prévue par le contenu (12 secondes,
avec possibilité de passer après chargement), puis demande son contexte. Après
la découverte de toutes les scènes, les mêmes questions reviennent sans photo.
Les options et la correction proviennent du contenu et du service inchangés.
Seuls les rappels finaux alimentent maîtrise, FSRS et temps de référence.

Les premières réponses des deux passes et les faits de présentation sont
conservés séparément. Après une erreur au rappel, la photo peut réapparaître
avec la correction ; ce chargement est enregistré sans écraser la réponse.
Une clôture pendant la découverte ne crée aucun rappel ni progrès fictif.
Une séance sans carte due est clôturée sans indexer d'item absent.

La position, les réponses et les transitions sont transactionnelles. Une
interruption masque les scènes et suspend le temps actif ; une reprise conserve
le reliquat d'exposition déjà enregistré. Après arrêt brutal, le segment non
validé reste inconnu et n'est pas reconstitué. Les brouillons et choix non validés
ne sont pas ajoutés à l'historique. Les chargements échoués sont signalés et
permettent de réessayer ou terminer sans fabriquer une exposition réussie.

Les 22 ressources `frontend/images/contextes` (photos WebP, manifeste et notice)
sont extraites directement du commit source `44acda5`, avec leurs empreintes dans
`UPSTREAM.json`. Aucun fichier de travail local ni historique personnel n'est
importé. La politique WebKit autorise les images locales seulement et conserve
l'interdiction du réseau.

Validation locale : 101 tests Python (dont les 60 tests du noyau), 15 tests
JavaScript et 11 contrôles de la sonde. Le test WebKit natif est étendu aux
photos locales, au passage découverte/rappel et au masquage lors d'une reprise.
La compilation `build-for-testing` iOS Simulator arm64 réussit. GitHub Actions
refuse toutefois de démarrer tous les jobs (paiement du compte échoué ou plafond
de dépenses à augmenter dans Billing & plans, exécution 39124033098). Aucun test
iOS de ce lot n’a donc été exécuté. La recette sur iPhone réel reste aussi à
confirmer ; le premier essai physique précédent portait sur l'ébauche antérieure.
Les ajustements des aides dépliables et des boutons de pause attendent la fin
du portage, selon la demande utilisateur.

## Premier lancement physique — 18 octobre 2026

L'app a été compilée et signée depuis Xcode, puis lancée sur un iPhone réel
après activation du Mode développeur et approbation du certificat sur l'appareil.
Un premier écran vide venait du contrôle de chemin : NSBundle exposait
`/private/var/...` alors que WebKit utilisait `/var/...`. Les deux côtés utilisent
désormais le chemin résolu pour la navigation et l'origine du pont, avec une
limite inchangée au dossier des ressources. Le chargement de `index.html` et son
titre ont été vérifiés dans le débogueur. Cela ne vaut pas recette complète des
exercices sur appareil physique.

Les tests natifs vérifient l'alias pointant vers les ressources et le refus des
URL réseau, dossiers voisins, traversées et liens symboliques sortants.

## Références

- [CPython sur iOS](https://docs.python.org/3/using/ios.html)
- [Runtime BeeWare](https://github.com/beeware/Python-Apple-support)
- [Règles de distribution Apple](https://developer.apple.com/app-store/review/guidelines/)

## Exécution physique Contextes — 18 octobre 2026

Le lot `53a7851` (documentation ensuite `57e5609`) a été compilé et signé
avec le projet Xcode local déjà configuré, puis exécuté sur l’iPhone Air connecté.
L’utilisateur a autorisé la réinitialisation des séances de test. Après
réapprobation du certificat de développement, `test-without-building` a réussi :
3 tests XCTest, zéro échec, et `PILOT_RESULT` indique `platform: ios`, `passed: 11`,
`http_server: false`.

La suite vérifie les limites des URL locales, le moteur et la persistance Python,
puis le pont réel WebKit pour Calcul mental, accès lexical, PQRST et Contextes.
Pour Contextes, les dix scènes locales sont chargées, leur exposition est passée
explicitement, puis le rappel revient sans photo et conserve ce masquage après
interruption/reprise. Le test Python embarqué parcourt aussi les deux passes,
vérifie l’absence de cartes après découverte et la clôture du rappel.
Cette exécution ne valide pas encore visuellement le confort, VoiceOver ou la
durée réelle complète de chaque exposition. Le journal WebKit contient des
messages de son décodeur WEBP (`err=-50`) malgré les contrôles de chargement
réussis ; ils restent à examiner si un défaut visuel est constaté.

Preuves locales ignorées par Git : `.local/contextes-device-retry.log` et
`.local/contextes-device-retry.xcresult`. Les diagnostics de l’appareil ne sont
pas publiés. Les tests GitHub restent bloqués par la facturation, indépendamment
de cette réussite sur appareil physique.
