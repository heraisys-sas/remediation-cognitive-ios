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

## Stratégies — lot du 18 octobre 2026

Quatre parcours du thème `methodes` sont accessibles : `choisir-plan`,
`auto-instruction`, `verifier-plan` et `chercher-information`. Les contenus,
correcteurs, règles de second essai et effets de progression viennent du
service inchangé au commit source `44acda5`. Le plan à vérifier garde l’ordre
de ses étapes ; le document à consulter reste visible pendant la réponse.

Une première erreur sur les trois parcours de raisonnement laisse répondre une
seconde fois sans révéler la réponse. Le résultat intermédiaire et les essais
sont sauvegardés, sans créer de correction finale ni carte à ce stade. Une
relance conserve le second essai. Les segments de temps validés s’additionnent,
sans reconstituer un segment perdu lors d’un arrêt du processus. Les révisions
rendent le renvoi d’un appel idempotent même si le temps recalculé diffère.
Les reprises avec la réponse déjà fournie suivent le comportement amont.

Les historiques sont séparés par parcours ; le plafond de séances du thème
`methodes` reste partagé comme dans la source. Les tests utilisent des dossiers
synthétiques séparés pour respecter cette règle. Aucun historique personnel
n’est réinterprété et aucune dérogation de dosage n’est ajoutée à l’interface.
Les ajustements d’ergonomie et d’aides sont toujours reportés à la fin.

Validation Mac : 107 tests Python (dont 60 du noyau), 18 tests JavaScript et
15 contrôles de la sonde. Les audits Sol et Astra sont favorables après ajout
du plan ordonné manquant. Le test WebKit natif couvre choisir un plan et chercher
dans un document ; la sonde Python couvre les quatre nouveaux parcours.
La compilation signée pour l’iPhone réussit ; le lancement des tests reste
bloqué par le téléphone verrouillé. Aucune nouvelle exécution physique de ce
lot n’est revendiquée. La recette est reportée au prochain point de test.

## Mémoire visuelle — lot suivant du portage

Cinq parcours `memoire` sont disponibles : `chiffres-endroit`, `chiffres-envers`,
`mots`, `associations` et `position`. Les 216 items des douze banques, leurs
identifiants et leurs paliers sont importés directement du commit source
`44acda5`, avec empreintes dans `UPSTREAM.json`. Aucun contenu local non commité
ni historique personnel n’est importé. Les services et correcteurs restent
inchangés.

La présentation conserve les durées du contenu : un chiffre, mot ou élément à
la fois, alternant avec les blancs de la source ; les associations restent en
liste pendant leur durée prévue. Le pont n’expose que le stimulus courant,
puis la question sans la séquence ni les associations. Le bouton Passer reprend
la possibilité déjà présente dans le client source. Les reprises après
correction donnent la réponse pour la réancrer, sans la compter comme une
première récupération indépendante.

Les transitions, la position, le reliquat de présentation et les segments de
temps de réponse validés sont sauvegardés dans la même transaction. Une
interruption masque la présentation, demande une reprise explicite et conserve
l’étape enregistrée. Les interruptions et présentations passées sont signalées
dans l’état local ; aucun temps perdu lors d’un arrêt brutal n’est inventé.
La reprise peut réafficher le stimulus courant pour le reliquat enregistré :
elle n’est pas présentée comme une exposition continue sans interruption.
Une clôture sans réponse ne crée ni correction ni carte. La progression et FSRS
suivent le service d’origine, avec des historiques séparés par parcours et le
plafond de séances partagé par le thème.

Le support est masqué dès l’expiration prévue, avant la sauvegarde de l’avance.
Si cette sauvegarde échoue, un réessai renvoie exactement la transition sans
réexposer le stimulus. Un retour perdu après validation retrouve l’état durable.

Validation Mac : 117 tests Python (dont 60 du noyau), 23 tests JavaScript et
20 contrôles de la sonde. Les cinq parcours comparent correction, reprises,
maîtrise, cartes FSRS et temps de référence au service source. Les tests couvrent
également la minuterie, les blancs, les interruptions, les renvois, l’annulation
de transaction et une séance vide. Le test WebKit natif est étendu à une
présentation complète de cinq chiffres (20 secondes), puis au rappel masqué.
La compilation finale `build-for-testing` iOS Simulator arm64 réussit pour le
code `f25cf00`. Les contrôles GitHub restent bloqués avant exécution par la
facturation ; aucun essai natif de ce lot n’est revendiqué. L’ergonomie reste
reportée à la fin du portage.

## Recette native mémoire visuelle — 18 octobre 2026

Le code du lot `f25cf00` (documentation `20a31ea`) a été compilé, signé et
exécuté sur l’iPhone Air connecté. Les sources sont synchronisées dans le projet
Xcode local signé ; seul le chemin de stockage est remplacé localement par un
dossier de test vierge. Aucun réglage personnel de signature n’est commité.

Résultat : **3 tests XCTest réussis, zéro échec**, dont la sonde Python qui
indique `platform: ios`, `passed: 20`, `http_server: false`. Les cinq parcours
mémoire passent leurs contrôles embarqués : présentation, interruption,
restauration, rappel masqué, correction et cartes FSRS. Les parcours de stratégie
sont également couverts par la sonde ; le test WebKit traverse choisir un plan
et chercher dans un document.

Le test WebKit réel vérifie une présentation complète de cinq chiffres sur
20 secondes, puis le masquage du support au rappel et l’enregistrement d’une
réponse. La méthode WebKit dure 22,128 secondes et la suite 23,544 secondes.
Cela complète les tests Mac ; VoiceOver, le confort et une recette visuelle
complète de chaque banque restent à vérifier. Les avertissements du décodeur
WEBP déjà observés sur Contextes restent présents sans échec du contrôle de
chargement.

Preuves locales ignorées par Git : `.local/memory-device.log` et
`.local/memory-device.xcresult`. Aucun diagnostic de l’appareil n’est publié.
L’app testée est relancée sur l’iPhone à la fin de l’essai.

## Voix et dictée natives — premier agrément d’usage

Deux commandes contextuelles sont ajoutées : Écouter/Arrêter la lecture et,
seulement lorsqu’une réponse libre est attendue, Dicter/Arrêter la dictée.
La lecture utilise les voix françaises ordinaires disponibles via
AVSpeechSynthesizer, sans demander de Voix personnelle. Le texte provient
uniquement de la vue courante : consigne, question, document/plan visible,
options ou indices déjà demandés. Les stimuli mémoire ne sont pas lus ; le
support PQRST masqué et les photos Contextes ne sont pas transmis au lecteur.
La lecture est arrêtée avant un changement d’étape.

La dictée utilise SFSpeechRecognizer pour `fr-FR`, uniquement si
`supportsOnDeviceRecognition` est vrai, puis exige
`requiresOnDeviceRecognition = YES`. Aucun repli vers une reconnaissance réseau
n’est effectué, ni aucun mot attendu fourni au reconnaisseur. Si la capacité
locale n’est pas disponible, le clavier continue de fonctionner. Les permissions
microphone et reconnaissance sont demandées uniquement après le choix Dicter.
Un refus ou une interruption libère la saisie et conserve le brouillon visible.

Les transcriptions partielles restent des brouillons modifiables. Il faut
arrêter la dictée et vérifier le texte avant de valider ; aucune transcription
ne déclenche de correction automatiquement. Le flux audio est traité en mémoire
sans fichier audio créé par l’app ; seul le texte explicitement validé suit le
stockage habituel du moteur. La capture est limitée à 45 secondes, puis la clôture
à 2 secondes. Une pause, une sortie en arrière-plan, un changement de route audio
ou une interruption arrête l’audio. Les tokens natifs et générations front
invalident les permissions et résultats tardifs, y compris un démarrage qui
attendait encore une annulation native.

La préparation Xcode ajoute les sources natives et les deux descriptions de
permission sans modifier les paramètres personnels de signature. Le pont audio
applique la même vérification d’origine locale et de frame principale que le
pont moteur. Aucun service du moteur, correcteur, contenu ou historique n’est
modifié par ce lot.

Validation Mac à ce stade : 117 tests Python et 31 tests JavaScript réussis.
Audits Sol et Astra favorables après correction d’une course au démarrage audio.
Un quatrième test XCTest couvre les capacités sans ouvrir le micro, le refus
avant permissions si la reconnaissance locale est indisponible et l’invalidation
d’une autorisation en attente. Le test WebKit interroge le pont audio et exerce
la commande de lecture/arrêt si une voix française est disponible.
La première demande de permissions, l’écoute réelle et la reconnaissance au
microphone restent à recetter sur iPhone. La réussite des tests de garde ne
constitue pas une preuve de transcription réelle ni de fonctionnement en mode
avion.

Références : [exiger le traitement local](https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest/requiresondevicerecognition),
[capacité de reconnaissance locale](https://developer.apple.com/documentation/speech/sfspeechrecognizer/supportsondevicerecognition),
[permission microphone](https://developer.apple.com/documentation/avfaudio/avaudioapplication/requestrecordpermission(completionhandler:)).

## Exécution native du lot vocal — 18 octobre 2026

La version `aa402ed` a exécuté ses quatre tests XCTest sur l’iPhone Air :
zéro échec, et 20 contrôles Python embarqués réussis (`platform: ios`). Le pont
WebKit confirme les capacités vocales booléennes, puis exerce lecture/arrêt.
L’appareil déclare une voix française et la reconnaissance sur l’appareil
pour la dictée. La méthode WebKit complète dure 22,534 secondes.

Le quatrième test refuse une dictée lorsque la capacité locale est absente,
avant toute demande de permission, et vérifie qu’une annulation invalide un
token encore en attente. Le microphone n’est pas ouvert par cette suite.
Le premier scénario a repris une séance de test interrompue ; le scénario
suivant a détecté un format numérique au lieu d’un booléen dans les capacités.
Ces deux échecs sont distingués de la dernière exécution réussie, faite sur un
stockage neuf avec le format corrigé.

L’app est relancée pour la recette humaine de la lecture, des permissions et
du microphone. La transcription réelle et le mode avion ne sont pas encore
validés. Le journal contient les avertissements WebP déjà connus ainsi qu’un
avertissement iOS 27 sur l’activation/désactivation synchrone de la session audio ;
ils n’ont pas fait échouer les tests et restent à suivre pour la réactivité.

Preuves locales ignorées par Git : `.local/speech-device-verified.log` et
`.local/speech-device-verified.xcresult`. Aucun diagnostic ou enregistrement
vocal personnel n’est publié.

### Confirmation de l’essai utilisateur

Le 18 octobre 2026, après ouverture de la version testée, l’utilisateur confirme :
« Lecture et dictée fonctionnent ». L’essai demandé consistait à écouter une
consigne puis dicter un court texte en français dans Retrouver le mot, à arrêter
la dictée et à vérifier la transcription sans la valider comme réponse.
La lecture audible et la transcription réelle au microphone sont donc confirmées
sur cet iPhone Air. Aucun enregistrement ni contenu personnel de l’essai n’est
copié au dépôt. Un essai explicite en mode avion reste à faire.
