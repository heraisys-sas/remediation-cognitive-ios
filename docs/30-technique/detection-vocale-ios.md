# Détection vocale sur iOS

Portage basé sur `remediation-cognitive` dev `44acda5df5d689fe4de022e9c194655ff5fdce01`.

## Retrouver le mot

L’autorisation vocale est demandée au démarrage explicite de la séance. La reconnaissance exige la disponibilité du mode sur appareil. Le module `dictee-auto.js` est importé sans modification depuis l’amont et contrôlé par `UPSTREAM.json`.

La lecture de la consigne précède l’écoute. Le moteur audio et la tâche de reconnaissance sont préarmés pendant la lecture, après autorisation. Les buffers du microphone sont jetés tant que la synthèse parle : aucun son de la consigne n’est transmis au reconnaisseur. Le callback natif de fin de synthèse ouvre directement ce flux, sans délai supplémentaire. Le rappel de 150 ms du module amont reste une activation idempotente du micro déjà ouvert ; il ne retarde pas l’écoute réelle. Chaque hypothèse doit rester stable pendant 700 ms avant un précontrôle. Une hypothèse rejetée ne constitue pas un essai. Une hypothèse acceptée passe ensuite par l’action normale de réponse, qui applique la correction et la persistance habituelles.

Le précontrôle `verify-dictation` ne sauvegarde rien. Il vérifie la séance et l’item actifs, l’absence de réponse déjà validée, puis appelle `verifier_dictee` du service amont. Les négations sont rejetées selon les règles amont. Le correcteur lexical conserve ses mots attendus, variantes déclarées et tolérances orthographiques ; la similarité sémantique ne remplace pas ce correcteur.

Une interruption arrête lecture et capture, annule les délais et invalide les résultats tardifs. La reprise explicite réarme l’écoute. « Répondre au clavier » désactive l’automatisme pour l’item courant. Une erreur de reconnaissance rend le clavier pour le reste de la séance. Les autres activités conservent la dictée manuelle et la vérification du brouillon.

## Similarité des phrases libres

Le module natif `_rc_semantics` expose les vecteurs français de `NaturalLanguage.NLEmbedding`, lorsqu’ils sont installés. Le raccord Python conserve la formule cosinus, l’arrondi à quatre décimales et le seuil historique **0,78** du moteur amont. Sans modèle disponible, le repli lexical amont reste actif. Aucun téléchargement n’est déclenché par ce raccord.

Ce seuil concerne les réponses libres pour lesquelles le correcteur amont autorise la similarité. Il ne s’applique pas à la détection lexicale ci-dessus. Une révision de modèle Apple ou une autre version d’OS peut changer les scores : le raccord ne prouve pas une calibration identique entre appareils. Le module expose `revision()` pour les diagnostics.

## Vérifications du 20 octobre 2026

- 120 tests Python réussis, dont un contrôle du contenu des fichiers avant/après les précontrôles acceptés et rejetés, et des tests de frontière du seuil avec des vecteurs synthétiques.
- 42 tests JavaScript réussis, dont préarmement pendant la lecture, absence de démarrage à froid après la lecture, stabilité de 700 ms, refus sans soumission, acceptation unique, interruption, reprise et choix du clavier.
- Compilation native arm64 pour simulateur réussie ; aucun simulateur exécuté.
- Audits Sol et Astra initiaux : aucun défaut concret identifié. Relecture Sol du préarmement natif effectuée ; les buffers antérieurs à l’ouverture sont également filtrés par horodatage.
- Tests natifs réussis sur iPhone Air : 4 XCTest sans échec, dont 20 contrôles Python embarqués et le parcours WebKit (22,902 s). Résultat local : `.local/automatic-flow-device.xcresult`. App relancée après les tests. La reconnaissance automatique avec une voix réelle et sa latence ressentie restent à vérifier par un essai utilisateur.

Les tests WebKit du parcours général désactivent uniquement l’autorisation automatique dans leur propre script, afin de ne pas ouvrir le micro pendant un test synthétique. Ils ne constituent donc pas une preuve de reconnaissance vocale réelle.

## Retours et passage entre questions

Tous les retours finaux proposent désormais une suite automatique, avec un délai adapté au texte (2,2 à 12 secondes ; au moins 4 secondes pour une réponse incorrecte). « Continuer » reste disponible pour avancer immédiatement. « Prendre le temps » conserve le retour sans limite et reste actif après pause/reprise du même retour.

La suite automatique attend la fin d’une lecture vocale. Pour Contextes, elle attend la révélation enregistrée de la photo ; une erreur de chargement ne provoque aucun passage automatique. Les temporisations d’exposition et les étapes PQRST de lecture, de formulation ou de rappel conservent leurs transitions pédagogiques. Aucun nouvel essai ni aucune réponse n’est inventé par la navigation.

Les transitions, interruptions et changements d’item annulent les timers obsolètes. Le retour est présenté dans un encadré discret. Les tests ciblés vérifient le passage unique, le maintien explicite, l’interruption, l’attente de lecture vocale et la révélation Contextes.

## Routage de lecture et micro préarmé

Le mode de capture est `AVAudioSessionModeDefault`, avec `PlayAndRecord`, `DefaultToSpeaker`, `AllowBluetoothHFP` et `AllowBluetoothA2DP`. Le mode `Measurement` précédent réduit le traitement dynamique et peut diminuer le niveau de lecture ; il ne convenait pas à cette interaction parlée.

Après activation, si la seule sortie choisie par iOS reste `BuiltInReceiver`, un repli ponctuel sélectionne le haut-parleur. Une sortie casque, Bluetooth, USB ou AirPlay n’est pas remplacée. Le test natif couvre la décision pour chacune de ces sorties et pour les routes multiples. Le niveau réellement entendu et les transitions avec un casque doivent être contrôlés sur l’appareil.

Validation du correctif de routage : 5 XCTest réussis sur iPhone Air, sans échec, dont la politique de préservation des accessoires et le parcours WebKit. Preuve locale : `.local/audio-routing-final-device.xcresult`. Relecture Sol favorable. Le volume entendu et le casque réel restent à confirmer par l’utilisateur.
