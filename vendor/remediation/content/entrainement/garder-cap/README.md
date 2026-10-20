# Garder le cap

20 situations originales réparties dans trois parcours indépendants, accessibles depuis l’accueil patient :

1. Reprendre après une interruption : 12 contrôles en quatre points réellement commencés, interrompus par un bref message non noté, puis repris après identification du prochain point.
2. Adapter le plan : actualiser une action sans perdre le but ni les contraintes valables.
3. Vérifier avant de terminer : comparer le résultat à la demande, repérer une discordance.

Dans les parcours Adapter et Vérifier, les informations restent visibles et une première erreur autorise un second essai sans dévoiler la réponse (`but-etapes`). Dans Reprendre, le dossier est visible pendant le contrôle, masqué pendant l’interruption et pendant le choix du point de reprise, puis restauré. L’interruption exige une réponse pour produire un vrai détour attentionnel mais n’entre pas dans la réussite ; le point de reprise et les quatre contrôles sont corrigés séparément. Aucun chronomètre de réponse. Quatre situations par séance. Les trois parcours ont des progressions indépendantes : leurs numéros ne sont pas des degrés de sévérité clinique.

Le choix parmi trois actions constitue une initiation au raisonnement explicite. Il ne remplace ni l’exécution d’une tâche personnelle, ni le programme complet de Goal Management Training. L’objectif proposé est pédagogique ; l’efficacité clinique de ces items n’a pas été mesurée. Relecture orthophoniste à faire.

## Sources et limites de transposition

- Jeffay et al., **INCOG 2.0, fonctions exécutives** (2023), DOI 10.1097/HTR.0000000000000834, [résumé primaire](https://pubmed.ncbi.nlm.nih.gov/36594859/). Recommandations de stratégies métacognitives et d’auto-surveillance après traumatisme crânien modéré à sévère. Elles soutiennent le principe de travail, pas ce logiciel ni ces QCM ; leur application au syndrome post-commotionnel léger n’est pas démontrée par cette référence. Une notice d’erratum 2024 est signalée par PubMed ; aucun niveau de recommandation précis n’est revendiqué ici.
- Tornås et al., **Rehabilitation of Executive Functions…** (2016), [essai randomisé](https://pubmed.ncbi.nlm.nih.gov/26812574/). Programme GMT avec rappels externes et régulation émotionnelle chez des personnes présentant une lésion cérébrale acquise chronique. Résultats les plus marqués sur les mesures auto-rapportées à six mois ; impossible d’attribuer ces effets à une vignette isolée ou à une composante unique.
- Bertens et al., **Do Old Errors Always Lead to New Truths?** (2015), [essai randomisé](https://pubmed.ncbi.nlm.nih.gov/26346836/). 67 patients avec atteinte exécutive après lésion cérébrale non progressive depuis au moins trois mois, entraînement de tâches du quotidien. Le contexte individuel et la réalisation de tâches réelles limitent la transposition à un QCM autonome.

Recherche effectuée le 30 septembre 2026 à partir des notices/résumés primaires. Pas de reproduction d’items propriétaires ni de prétention à une revue systématique exhaustive.

## Matrice de conception

| Famille | Objectif fonctionnel | Analogie avec les sources | Limite |
|---|---|---|---|
| Reprise | Éviter de recommencer ou sauter une étape après interruption | Recentrage sur le but et suivi de tâche (INCOG/GMT) | L’interruption est provoquée dans une simulation écran, sans démonstration de transfert à une tâche personnelle |
| Adaptation | Réviser le plan après une information nouvelle | Gestion du but et résolution de problèmes (INCOG/GMT) | La flexibilité est sollicitée par le choix, pas mesurée isolément |
| Contrôle | Repérer un destinataire, horaire ou état de fichier incorrect | Auto-surveillance et vérification (INCOG) | Pas de mesure de généralisation au quotidien |

Générateur : `python3 tools/generer_garder_cap.py`. Les reprises réellement interrompues portent des identifiants `cap-2-reprise-…` ; les anciens QCM de reprise conservent leur historique sans être resservis.

## Ajustement au public post-commotionnel de niveau antérieur élevé

Les situations livrées demandent de recouper plusieurs contraintes, distinguer un état achevé d’un état périmé et comparer des solutions plausibles : budget/délai, acompte/solde, version source/export, livraison/durée. La difficulté vient du contrôle de l’action, sans exiger de connaissances professionnelles spécialisées ni accélérer la réponse. Les informations visibles évitent de transformer chaque exercice en test de rappel. Le niveau intellectuel antérieur ne suffit pas à déterminer la charge actuellement tolérée ; ces familles ne sont pas des niveaux normés.

Références plus proches du traumatisme léger :

- **VA/DoD, prise en charge du mTBI post-aigu (2021)**, [recommandations officielles](https://www.healthquality.va.gov/guidelines/Rehab/mtbi/VADODmTBICPGFinal508.pdf) : propose un essai bref de réadaptation cognitive dirigée par un clinicien pour les difficultés persistantes de mémoire, attention ou fonctions exécutives, après prise en compte des autres facteurs contributifs. Cela ne valide pas un logiciel autonome.
- **GOALS, vétérans avec PTSD et antécédent de mTBI** : [essai randomisé, 40 participants](https://pubmed.ncbi.nlm.nih.gov/33019861/), deux groupes de cinq semaines, éducation à la santé cérébrale comme contrôle actif. Pertinent pour l’approche centrée sur les buts et l’autorégulation, mais population militaire avec PTSD et programme accompagné ; ne permet pas de revendiquer un effet de nos vignettes chez des adultes civils sans PTSD, ni un effet spécifique aux personnes de niveau intellectuel antérieur élevé.

Une nouvelle publication GOALS sur mTBI (PMID 41838854, 2026) a été repérée, mais sa notice complète était inaccessible au moment de cette revue ; elle n’est pas utilisée pour affirmer un résultat supplémentaire.
