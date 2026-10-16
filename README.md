# Remédiation cognitive — iPhone et iPad

Application autonome en préparation pour iPhone 17 et iPhone Air ; extension aux
iPad et autres appareils selon les capacités disponibles. Projet distinct de
[remediation-cognitive](https://github.com/heraisys-sas/remediation-cognitive).

Complément d'activités accompagnées pour adultes après traumatisme crânien.
Aucun exercice n'est présenté comme un test diagnostique validé.

## État réel

Première expérimentation : exécuter le moteur Python existant dans le processus
d'une app iOS, sans FastAPI et sans Mac serveur. Ce dépôt ne livre pas encore
une application d'exercices utilisable. Voir [le banc d'essai](mobile/ios/README.md).
La voix et la dictée natives, les correcteurs, les contenus et la persistance
mobile restent à intégrer. PCC sera facultatif pour l'accompagnement.

## Origine et suivi

`engine/` est une copie inchangée du moteur et de ses tests au commit `44acda5`
de la branche `dev` du dépôt source. `UPSTREAM.json` conserve cette référence
et les empreintes de tous les fichiers Python importés. La licence BSD originale
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
