# Parcours complémentaires — 20 octobre 2026

## Périmètre

Le lot ajoute les 19 parcours classiques manquants et quatre protocoles de mémoire
immédiate aux 13 parcours du pilote précédent. Les 36 cartes sont filtrables
par 12 compétences dans les paramètres de l’accueil. Missions, carnet,
programme de huit semaines et Repères sont des fonctions transversales et ne
font pas partie de ce lot d’exercices.

Référence du contenu : `dev` au commit `44acda5df5d689fe4de022e9c194655ff5fdce01`
du dépôt `heraisys-sas/remediation-cognitive`. Les empreintes de tous les fichiers
importés figurent dans `UPSTREAM.json`. Aucun historique personnel n’est importé.
Le moteur reste inchangé ; les adaptations sont dans `mobile/`.

| Identifiant classique | Carte |
| --- | --- |
| `calcul-mental` | Calcul mental |
| `deduction` | Déduction |
| `anglais` | Verbes irréguliers anglais |
| `python` | Lire du Python |
| `acces-lexical` | Retrouver le mot |
| `memoire-source` | Retrouver le contexte |
| `pqrst-guide` | PQRST guidé |
| `cap-adapter` | Adapter un plan |
| `cap-verifier` | Vérifier avant de terminer |
| `choisir-plan` | Choisir un plan |
| `auto-instruction` | Se guider avant d’agir |
| `verifier-plan` | Vérifier un plan |
| `chercher-information` | Chercher dans un document |
| `pqrst-rappel` | Répondre de mémoire après lecture |
| `quotidien` | Situations du quotidien |
| `series-lues-immediat` | Séries lues — rappel immédiat |
| `series-lues-differe` | Séries lues — rappel après attente |
| `series-lues-premiere-serie` | Séries lues — première série |
| `series-entendues-immediat` | Séries entendues — rappel immédiat |
| `series-entendues-differe` | Séries entendues — rappel après attente |
| `series-entendues-premiere-serie` | Séries entendues — première série |
| `chiffres-endroit` | Chiffres dans l’ordre |
| `chiffres-envers` | Chiffres en ordre inverse |
| `mots` | Mots — ordre et ordre inverse |
| `associations` | Associations mot–nombre |
| `position` | Position dans une séquence |
| `strategie-semantique` | Stratégie sémantique (SFA) |
| `strategie-phonologique` | Stratégie phonologique (PCA) |
| `actualiser-consigne` | Actualiser une consigne |
| `comparer-documents` | Comparer des documents |
| `reperer-essentiel` | Repérer l’essentiel |
| `cap-reprendre` | Garder le cap — reprendre après une interruption |

Les protocoles séparés `mi-code`, `mi-chemin`, `mi-changement`, `mi-objets`
utilisent les générateurs et corrections du module amont de mémoire immédiate.
Ils ne produisent pas de progression FSRS. Les exemples, premières réponses et
essais aidés restent distincts ; une interruption pendant l’encodage ou le
maintien remplace le stimulus avec un lien vers l’essai interrompu. Le plafond
quotidien et les blocs terminés sont conservés entre activités classiques.

## Contrats préservés

- SFA/PCA : notes préparatoires non notées, puis réponse au correcteur lexical.
- Actualiser : seul le message courant est visible ; les messages sont masqués
  lors de la restitution finale structurée.
- Comparer : les deux documents restent consultables ; tous les champs sont
  requis et la correction reste celle du service original.
- Repérer : classement séquentiel ; Reprendre : diversion non notée puis reprise
  sans révéler la réponse attendue.
- PQRST rappel : présentation puis questions sans texte. Séries : rappel immédiat,
  différé de 20 secondes pouvant être écourté explicitement, ou première série.
- Séries entendues : fichiers audio embarqués ; chaque pause commence après
  la fin effective du clip. Une erreur audio demande un redémarrage explicite,
  sans afficher les mots comme remplacement silencieux.
- Déduction : grille et réponse canonique du module source. Python : comparaison
  sensible à la casse, aucune exécution du code, pas de dictée française.
- Les transitions utilisent session, item et révision ; les renvois de commande
  ne doivent pas enregistrer deux réponses. Le temps d’interruption est exclu.

## Validation et limites

`pytest tests engine/tests -q` : **213 tests réussis** sur ordinateur, dont
48 intégrations avec les contenus réels (démarrage des 32 parcours classiques,
correction source des nouvelles présentations, conservation des blocs et quotas).
`node --test tests/test_active_clock.cjs tests/test_pilot_render.cjs tools/test_immediate.cjs` :
**56 contrôles réussis**, dont la reprise du brouillon de comparaison, le masquage
au rappel et l’envoi du marqueur d’essai aidé. `check_upstream.py` valide les empreintes.

La compilation générique arm64 pour simulateur vérifie aussi les sources natives
et la cible XCTest ; elle ne constitue pas une exécution. Le 20 octobre, neuf tests natifs passent sur iPhone Air en iOS 27.0.1,
avec les 20 contrôles du moteur embarqué. Le test complémentaire vérifie les
deux documents, l’activation de la validation, la correction et, pour Code,
le masquage, le second essai aidé et la conservation de la première réponse.
Aucun simulateur n’a été exécuté pour ce lot. La lisibilité réelle, VoiceOver, la disposition sur iPad, les délais
et les transitions audio restent à vérifier sur appareil. Ce contrôle représentatif ne valide pas l’ensemble des 36 parcours.
Le résultat local est dans `.local/complete-parcours-device-isolated.xcresult`
(neuf tests, zéro échec, 49,2 secondes) et son journal homonyme `.log`.
Les scénarios XCTest disposent désormais d’un stockage temporaire distinct,
conditionné au chargement de XCTest et à l’argument `ios_probe`, afin de ne
pas consommer les quotas du pilote utilisé à la main.

La dernière revue par sous-agents a été interrompue par le quota d’usage.
Elle a néanmoins identifié le marqueur d’essai aidé manquant dans la commande JS,
corrigé avec un test de non-régression. Ne pas présenter cet audit final comme complet.

Voir [l’essai de délégation](experience-delegation.md) pour la comparaison contrôlée.
