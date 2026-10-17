# Première preuve du moteur embarqué

Cible produit : iPhone 17 et iPhone Air, puis iPad et extension selon capacités.
Cette première étape compile le **moteur Python existant dans une app XCTest**,
sans FastAPI, sans Mac serveur, sans Cloudflare et sans appel PCC.
Ce n'est pas encore une application d'exercices utilisable.

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

## Pilote Calcul mental et Retrouver le mot

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
idempotente et transaction annulée. Les contrats Contextes et PQRST restent
testés sans rendre ces parcours accessibles dans le pilote. Sous iOS, le
workflow vérifie aussi le pont réel WebKit→natif→Python et conserve une capture
de l'écran initial. Un passage sur iPhone réel, le clavier, VoiceOver, les
grands caractères et le confort en séance restent nécessaires.

## Sources

- [CPython sur iOS](https://docs.python.org/3/using/ios.html)
- [Runtime BeeWare](https://github.com/beeware/Python-Apple-support)
- [Règles de distribution Apple](https://developer.apple.com/app-store/review/guidelines/)
