# Remédiation cognitive — iPhone et iPad

Application autonome en préparation pour iPhone 17 et iPhone Air ; extension aux
iPad et autres appareils selon les capacités disponibles. Projet distinct de
[remediation-cognitive](https://github.com/heraisys-sas/remediation-cognitive).

Complément d'activités accompagnées pour adultes après traumatisme crânien.
Aucun exercice n'est présenté comme un test diagnostique validé.

## État réel

Le noyau Python a exécuté ses 60 tests sous iOS 26.5 sur simulateurs iPhone 17
et Air. Le nouveau lot local étend le pilote à 32 parcours classiques et quatre
protocoles de mémoire immédiate, avec contenu versionné, correcteurs d’origine
et sauvegarde transactionnelle. Voir [l’inventaire et la validation du lot](docs/30-technique/parcours-complementaires.md).
Les 213 tests Python et 56 contrôles JavaScript du lot passent sur ordinateur.
La compilation iOS est distincte de l’exécution sur simulateur et de la recette
sur appareil. Les nouveaux parcours restent à essayer sur iPhone.
La lecture et la dictée natives fonctionnent dans le pilote ; la validation
vocale automatique concerne Retrouver le mot, selon les règles du moteur.
PCC reste facultatif.

## Origine et suivi

`engine/` est une copie inchangée du moteur et de ses tests au commit `44acda5`
de la branche `dev` du dépôt source. `UPSTREAM.json` conserve cette référence
et les empreintes du noyau ainsi que du service et des contenus importés.
La licence BSD originale
est conservée dans `LICENSE`.

Les évolutions du dépôt source sont examinées avant portage : règles de correction,
FSRS, protocoles, identifiants de contenu et formats d'historiques doivent rester
compatibles. Pas de synchronisation aveugle ou de fusion automatique.

## Vérification sur ordinateur

Dans un environnement isolé :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=mobile/ios .venv/bin/python -m probe
```

Les tests utilisent des données synthétiques. Aucune donnée personnelle du dépôt
source n'est importée. Les détails de compilation iOS et limites de validation
sont dans `mobile/ios/README.md`.
