# Portage des correcteurs — issue #16

Import partiel, sans modification, de `backend/app/domain/correction/{text,dispatch,message}.py` depuis `heraisys-sas/remediation-cognitive@0ed9207e3dc7d13f03b0e283d34d1d627ab72fdd` (PR source #30).
Le moteur, FSRS et les contenus restent à leur référence de base ; `UPSTREAM.json` conserve cette base et documente les trois exceptions et leurs empreintes.

Les prises de message vérifient un fait avec variantes explicites et enveloppes neutres bornées. La proximité vectorielle ne valide plus ces faits. Le correcteur générique protège négations et permutations de mots inversant les rôles. Le seuil sémantique des autres réponses reste inchangé.

Les 70 cas synthétiques du corpus amont sont conservés dans `tests/fixtures/correction-0ed9207.json`, avec leurs résultats attendus. Le test vérifie aussi la cible du contenu pour détecter une dérive de référence. Des tests dédiés imposent les garde-fous même si la proximité sémantique retourne vrai, et interdisent son appel pour les faits. Ce corpus exploratoire ne constitue pas une calibration clinique indépendante.

Validation ordinateur : 224 tests Python et 69 tests JavaScript réussis. Revue indépendante favorable ; les trois correcteurs et le corpus sont identiques octet pour octet au commit source. Vérification des empreintes importées réussie. Aucun historique personnel importé ou recalculé ; les corrections enregistrées restent intactes. La recette vocale réelle et les embeddings Apple sur iPhone ne sont pas validés par cette suite ordinateur.

## Recette native du 22 octobre 2026

Compilation signée et exécution sur iPhone Air connecté : 10 tests XCTest réussis, zéro échec en 60,050 secondes. La sonde native rapporte `platform: ios`, `passed: 20`, `correction_cases: 70` et `http_server: false`. Le corpus est inclus par la préparation du pilote et son décompte exigé par XCTest. La revue indépendante confirme le chemin de ressource et les dépendances embarquées.

WebKit vérifie également les traits du chemin, le geste synthétique et le passage automatique (10,780 secondes), ainsi que les parcours complémentaires. Cela ne prouve pas le confort d’un geste réellement effectué au doigt ni une nouvelle dictée au microphone. Les avertissements du décodeur WebP déjà observés restent présents sans échec de la suite.

Preuves locales ignorées : `.local/correcteurs-device.log` et `.local/correcteurs-device.xcresult`. Les données synthétiques des essais sont isolées du stockage d’usage. L’application a été relancée après les tests. Aucune fusion ni publication App Store.
