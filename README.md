# Remédiation cognitive — iPhone et iPad

Application autonome en préparation pour iPhone 17 et iPhone Air ; extension aux
iPad et autres appareils selon les capacités disponibles. Projet distinct de
[remediation-cognitive](https://github.com/heraisys-sas/remediation-cognitive).

Complément d'activités accompagnées pour adultes après traumatisme crânien.
Aucun exercice n'est présenté comme un test diagnostique validé.

## État réel

Le noyau Python a exécuté ses 60 tests sous iOS 26.5 sur simulateurs iPhone 17
et Air. Le pilote propose Calcul mental, Retrouver le mot, PQRST guidé, Retrouver le
contexte, quatre parcours de stratégie et cinq parcours de mémoire visuelle. Il réutilise le service et les
correcteurs d’origine, avec contenu versionné, interface locale et sauvegarde
transactionnelle. Voir [le banc d'essai et le pilote](mobile/ios/README.md).
La validation du pilote sous iOS est distincte de celle du noyau ; consulter
les résultats du workflow avant de le considérer comme exécuté.
La lecture française et la dictée natives facultatives sont en cours de recette.
La dictée exige la reconnaissance sur l’appareil et laisse vérifier le texte
avant validation. PCC reste facultatif.

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
