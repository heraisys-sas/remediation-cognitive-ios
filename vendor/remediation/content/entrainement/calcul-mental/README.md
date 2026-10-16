# Calcul mental — calcul pur et applications adultes

320 items, douze paliers. Le mode Auto démarre au palier 5 ; les quatre premiers paliers restent un socle facultatif accessible par le sélecteur. Aucun chronomètre imposé. L’énoncé reste visible ; on sollicite le calcul mental sans transformer la lecture en test de mémoire.

| Palier | Contenu | Exemple |
|---|---|---|
| 1–4 | Socle conservé : compléments, doubles, additions et soustractions dans 20 | 13 − 5 |
| 5 | Compensation, décomposition et écarts | 143 − 68 ; 68 + 27 − 18 |
| 6 | Produits, divisions, facteur manquant et lots | 24 × 7 ; 186 ÷ 6 |
| 7 | Deux transformations, calcul inverse, stock et moyenne | 23 × 6 − 37 |
| 8 | Décimales, montants, prix unitaires et produits | 37,5 + 18,75 ; achats avec remise fixe |
| 9 | Proportions, durées, cadence ; calcul direct | Durée de plusieurs interventions avec pauses entre elles |
| 10 | Pourcentages, base initiale et opérations avec parenthèses | 15 % de 240 ; retrouver le prix avant remise |
| 11 | Comparaisons de coûts, seuils et rendement ; calcul direct | Deux tarifs avec frais fixes et coût par utilisation |
| 12 | Synthèse, variations successives et calcul composé | Hausse de 20 % puis baisse de 10 % ; (77,5 + 18,75) × 8 |

Le calcul pur reste une composante centrale : au moins un tiers des items de chaque palier adulte, et davantage aux paliers 5–7. Les applications complètent les opérations directes. Les familles alternent dans le contenu initial ; les révisions restent sélectionnées selon leur échéance, donc cette proportion n’est pas garantie dans chaque séance de révision.

Chaque item propose une méthode facultative adaptée, sans révéler de résultat intermédiaire. La difficulté augmente par la structure du calcul, les conversions et les décisions à effectuer, pas seulement par la taille des nombres. Ce classement est pédagogique, non étalonné : un calcul de pourcentage peut rester facile pour certains utilisateurs. Le palier peut être choisi manuellement.

## Génération et contrôle

`python3 tools/generate_items.py` conserve les fichiers P1–4 et reconstruit P5–12 depuis `tools/calcul_adulte.py` (252 items, identifiants `cm4-…`). `tools/verifier_calcul_adulte.py` recalcule indépendamment les réponses depuis les seuls énoncés ; il est intégré au validateur général. Décimales exactes, seuil inclus de livraison et changements successifs sont testés.

Les anciens identifiants `cm3-…` P5–12 ne sont plus servis. Leurs historiques restent conservés ; ils ne prouvent pas la maîtrise du nouveau corpus. Les nouvelles réussites sont comptées séparément pour la progression, sans remettre à zéro le palier choisi ni effacer les données.

## Portée

On entraîne ici le calcul et ses stratégies. L’intérêt pratique du calcul pur ne suppose pas de démontrer un transfert global vers l’intelligence. Les applications s’inspirent du principe de tâches pertinentes et de stratégies explicites ; ce corpus n’a pas de validation clinique propre. Voir ADR-024 pour les références et leurs limites de population. Relecture informelle du nouveau contenu encore à réaliser.
