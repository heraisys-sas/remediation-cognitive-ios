# Première preuve du moteur embarqué

Cible produit : iPhone 17 et iPhone Air, puis iPad et extension selon capacités.
Cette première étape compile le **moteur Python existant dans une app XCTest**,
sans FastAPI, sans Mac serveur, sans Cloudflare et sans appel PCC.
Ce n'est pas encore une application d'exercices utilisable.

## Validation du 16 octobre 2026

- Les 60 tests du moteur passent sur le Mac et dans GitHub Actions (Linux).
- `build-for-testing` réussit pour iOS Simulator arm64, cible iOS 26,
  avec le SDK iOS 27.1 et Python 3.13.16.
- Aucun runtime de simulateur iOS n'est installé sur le poste : la suite n'a
  **pas encore été exécutée sous iOS**, ni sur iPhone physique.
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

## Sources

- [CPython sur iOS](https://docs.python.org/3/using/ios.html)
- [Runtime BeeWare](https://github.com/beeware/Python-Apple-support)
- [Règles de distribution Apple](https://developer.apple.com/app-store/review/guidelines/)
