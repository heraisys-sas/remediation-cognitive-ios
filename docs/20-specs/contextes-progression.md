# Progression Contextes — revue scientifique et conception

Issue source : https://github.com/heraisys-sas/remediation-cognitive/issues/34

## Objectif — cible dev macOS et parité iOS

Faire évoluer Contextes vers une difficulté progressive centrée sur l’association message–source. Banque cible : 200 scènes distinctes, réparties éditorialement en cinq ensembles de 40 (quatre séries de dix par palier). Une série éditoriale de dix ne force pas dix associations simultanées au début. Conserver les 20 scènes/IDs actuels. Demande utilisateur : partager cette évolution ici et l’appliquer sur macOS et iOS, via branches/PR sans fusion automatique.

## Revue scientifique ciblée

Revue déléguée à un sous-agent Astra, utilisant Consensus, puis PubMed/PMC/éditeurs après épuisement du quota du plugin. Revue non systématique. Aucun essai identifié ne valide notre exercice, ses 12 secondes, ses quatre choix, les cinq paliers ci-dessous ni un seuil de passage.

- INCOG 2.0 Memory (Velikonja 2023), recommandations après TCC : récupération active, stratégies adaptées et accompagnement ; preuves limitées pour entraînement informatisé restauratif seul. https://doi.org/10.1097/HTR.0000000000000837
- Morrow 2020 : 41 adultes TCC modéré/sévère et 41 témoins, liaisons visage–scène avec choix également familiers ; déficit relationnel. Étude descriptive, pas essai thérapeutique. https://doi.org/10.3389/fnhum.2020.00270
- Wright 2014 : 18 TCC sévères +18 témoins, activités faites/observées ; mémoire source proche du plafond malgré déficit de contenu. La difficulté dépend de la tâche. https://pmc.ncbi.nlm.nih.gov/articles/PMC4148421/
- Sumowski 2014 : 10 personnes TCC sévère, récupération active supérieure à réétude pour matériel entraîné ; petit échantillon, pas preuve de transfert quotidien. https://doi.org/10.1016/j.apmr.2013.10.021
- Haslam 2011 : récupération espacée et apprentissage sans erreur, associations visage–nom, population ABI mixte ; extrapolation à Contextes. https://pubmed.ncbi.nlm.nih.gov/21229436/
- Ownsworth 2017 : essai randomisé 54 TCC sévères, apprentissage avec analyse des erreurs utile dans activités exécutives ; pas de supériorité universelle du sans-erreur. https://doi.org/10.1177/1545968317740635
- ReMemBrIn 2019 : 328 adultes TCC, pas de bénéfice cliniquement important sur difficultés mnésiques quotidiennes à six mois, malgré certains objectifs individuels favorisés. https://pubmed.ncbi.nlm.nih.gov/31032782/
- Morrow 2026 : pilote TCC chronique par SMS, faisabilité et rétention des mots entraînés ; efficacité/transfert préliminaires. https://pubmed.ncbi.nlm.nih.gov/41606760/

## Paliers proposés — hypothèses de conception, non calibrées

1. Associations distinctes : scènes lisibles, sources nettement différentes, blocs courts, apprentissage explicite du lien.
2. Sources également familières : tous les choix ont été vus dans le bloc ; messages plausibles pour plusieurs sources, afin que la familiarité seule ne suffise pas.
3. Sources proches : contextes de même catégorie avec indice distinctif explicite ; lisibilité inchangée.
4. Interférence contrôlée : sources réutilisées pour messages différents, sans ambiguïté ; changer une seule dimension à la fois.
5. Maintien différé et variation : items intercalés ou rappel ultérieur, puis scènes inédites comparables ; transfert proche observé séparément.

Maintenir le message visible dans la question : demander simultanément son contenu ajouterait une autre exigence. Une déduction sémantique évidente ne doit pas remplacer la mémoire de source aux niveaux avancés. Ne pas rendre les images petites, les textes longs ou les gestes rapides pour simuler la difficulté.

## Garde-fous et mise en œuvre

- Choix initial du palier accompagné/manuellement ; aucune progression automatique présentée comme validée. Exemple 8/10 sur deux séries = suggestion arbitraire de prototype, pas norme clinique ni prescription.
- Exposition réglable/prolongeable ; enregistrer durée effective et maintenir ce paramètre lors des comparaisons.
- Découverte puis rappel final conservés ; ce dernier mesure une rétention après apprentissage/correction, pas une mémoire spontanée indépendante.
- Garder distincts : premières réponses découverte et rappel final, aides, correction/réponse aidée, délai, items intercalés, version du protocole et du matériel.
- Après échec, présenter la bonne paire et proposer une nouvelle récupération plus tard ; ne pas appeler cela strictement sans-erreur.
- Anciennes séances et contenus inchangés ; nouveaux IDs pour tout contenu modifié. Aucun historique réinterprété, aucun transfert quotidien déduit des scores du jeu.

## Critères de recette

- [ ] Spécification/ADR commune macOS–iOS, distinction preuves/hypothèses.
- [ ] Profil de difficulté versionné et paramètres enregistrés avec chaque nouvelle séance.
- [ ] Au niveau 2+, choix tous vus et également familiers ; pas d’ambiguïté de la bonne association.
- [ ] Aucun changement de lisibilité/voix/gestes imposé par le palier.
- [ ] 200 scènes/ressources originales, droits et provenance, ancien matériel préservé ; pas de duplications présentées comme nouvelles scènes.
- [ ] Ressources hors connexion, contraintes image/texte et absence de données réelles vérifiées.
- [ ] Tests de parité correction, aides, reprise, progression/FSRS et historique entre macOS et iOS.
- [ ] Recette adulte/orthophoniste des distracteurs et de l’effort ; transfert quotidien évalué séparément.

État initial : source dev 0ed9207 ; banque enrichie iOS dans PR #31 (dépôt remediation-cognitive-ios), 11 tests natifs réussis avec 20 images source. Génération des 180 nouvelles scènes suspendue pendant la définition scientifique. Cet état précède le premier lot fonctionnel décrit ci-dessous.

## Premier lot fonctionnel

Le premier lot se limite aux profils manuels `origine` et `sources-vues`, version `contextes-source-v2`, avec les scènes existantes. Les trois autres paliers demeurent des hypothèses de conception à matérialiser par des contenus distincts et une recette ; aucune génération de 180 photos ne précède cette validation de structure. Aucune règle automatique 8/10 appliquée.

La plupart des études citées portent sur des TCC modérés/sévères ou des lésions cérébrales acquises mixtes ; elles ne valident pas spécifiquement un protocole pour syndrome post-commotionnel. Le profil « sources-vues » utilise la même liste de candidats dans les deux passes, évitant qu’une intersection de deux listes différentes fournisse un indice involontaire.

Suivi commun : [issue source #34](https://github.com/heraisys-sas/remediation-cognitive/issues/34), [PR macOS vers dev #35](https://github.com/heraisys-sas/remediation-cognitive/pull/35). Import iOS partiel du commit source `61c0ffd` ; le point de référence global du moteur reste inchangé. Les anciennes séances sans profil conservent leur protocole. La découverte ne met pas à jour FSRS ; le rappel final conserve son fonctionnement existant.
