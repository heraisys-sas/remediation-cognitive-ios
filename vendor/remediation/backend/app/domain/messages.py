"""Séparation stricte des vocabulaires (garde-fou du cahier des charges).

- module bilan : vocabulaire clinique, disclaimers professionnels requis ;
- module rééducation : vocabulaire sobre, familial ;
- module entraînement : vocabulaire neutre, ludique modéré.

Aucune chaîne visible par l'utilisateur ne doit être construite hors de ce module.
"""

VOCABULAIRES = {
    "bilan": {
        "titre_session": "Bilan de suivi",
        "disclaimer": (
            "Ce bilan ne constitue pas un diagnostic. "
            "Partagez l'export avec votre professionnel de santé référent."
        ),
    },
    "reeducation": {
        "titre_session": "Séance de rééducation",
    },
    "entrainement": {
        "titre_session": "Session d'entraînement",
        "accompagnement_question": "Ta reformulation répond-elle à la question que tu t’étais posée ? Quel passage te permet de le vérifier ?",
        "accompagnement_objectif": "Quel était l'objectif ou l'idée principale du texte ? Comment l'as-tu exprimé avec tes mots ?",
        "accompagnement_contrainte": "Quelle condition ou précision était importante pour agir correctement ? Comment l'as-tu retenue ?",
        "accompagnement_verification": "Comment as-tu vérifié que ta reformulation reprenait l'essentiel, sans ajouter d'information ?",
        # Libellés des thèmes exposés par l'API (contrat GET /themes).
        "themes": {
            "calcul-mental": {
                "nom": "Calcul mental",
                "description": "Calculer de tête : quantités, durées et situations pratiques, avec des méthodes adaptées",
            },
            "series-entendues": {
                "nom": "Mémoriser des séries — mots entendus",
                "description": "Écouter des mots sans les lire, puis les rappeler librement",
            },
            "actualiser-consigne": {
                "nom": "Actualiser une consigne",
                "description": "Retenir une consigne, intégrer ses changements et restituer ce qui reste valable",
            },
            "comparer-documents": {
                "nom": "Comparer deux documents",
                "description": "Repérer les écarts utiles entre une demande et sa confirmation, documents sous les yeux",
            },
            "reperer-essentiel": {
                "nom": "Repérer l’essentiel",
                "description": "Garder un objectif et sélectionner les informations qui changent la tâche",
            },
            "anglais": {
                "nom": "Anglais — verbes irréguliers",
                "description": "Rappel actif : écris le verbe demandé, sans proposition de choix",
            },
            "python": {
                "nom": "Python",
                "description": "Commandes du langage et prédiction de sortie de snippets",
            },
            "memoire": {
                "nom": "Retenir et manipuler",
                "description": "Empans de chiffres et de mots, séquences et associations — mémorisation progressive",
            },
            "rappel-series": {
                "nom": "Mémoriser des séries",
                "description": "Deux parcours indépendants : mots lus ou entendus, puis rappel libre",
            },
            "quotidien": {
                "nom": "Au quotidien",
                "description": "Retenir un message, préparer ses actions et choisir des rappels dans des situations courantes",
            },
            "deduction": {
                "nom": "Déduction",
                "description": "Grilles logiques 3×3 puis 4×4 : placer les figures et les couleurs en croisant les informations",
            },
            "garder-cap": {
                "nom": "Garder le cap",
                "description": "Reprendre une tâche réellement interrompue, adapter un plan et vérifier avant de terminer",
            },
            "methodes": {
                "nom": "Méthodes pour retenir et s’organiser",
                "description": "Choisir une stratégie, vérifier un plan et pratiquer la lecture PQRST pas à pas",
            },
            "evocation": {
                "nom": "Retrouver des mots et leur contexte",
                "description": "Définitions, indices progressifs, mémoire du contexte — retrouver ce qu'on sait déjà",
            },
        },
        # Feedback immédiat guidé (correction serveur).
        "feedback_correcte": "Bien joué, réponse correcte !",
        "feedback_incorrecte": "Pas tout à fait — la réponse attendue s'affiche, on y reviendra.",
        "feedback_assiste": "Voici la réponse — on la reverra bientôt, sans indice cette fois.",
        "feedback_essaie_encore": "Pas tout à fait. Reprends : tu peux demander un indice.",
        # Messages d'erreur (clés : erreur_<code machine du contrat>).
        "erreur_palier_inconnu": "Ce palier n'existe pas pour ce thème.",
        "erreur_parcours_inconnu": "Ce parcours n'existe pas pour ce thème.",
        "erreur_theme_inconnu": "Thème inconnu.",
        "erreur_session_inconnue": "Séance introuvable (elle n'existe plus en mémoire).",
        "erreur_session_terminee": "Cette séance est déjà terminée.",
        "erreur_item_hors_seance": "Cet item ne fait pas partie de la séance en cours.",
        "erreur_reponse_invalide": "Réponse ou temps invalide.",
    },
    "missions": {
        "titre_session": "Missions dans la vraie vie",
        "mission_inconnue": "Mission inconnue.",
        "journal_entree_invalide": "Note invalide (texte manquant ou trop long).",
    },
}


def texte(cle_module: str, cle_message: str) -> str:
    """Retourne un texte du vocabulaire du module — erreur si le module inconnu."""
    return VOCABULAIRES[cle_module][cle_message]


PQRST_INTERFACE = {
    "P": "1. Parcourir — repérez le sujet du texte",
    "Q": "2. Questionner — quelle question vous posez-vous ?",
    "R": "3. Lire — cherchez la réponse à votre question",
    "S": "4. Reformuler — sans le texte, redisez l’essentiel",
    "retour-S": "Votre reformulation et un résumé possible",
    "T": "5. Se tester — question {numero} sur {total}",
    "pret": "Cinq étapes, à votre rythme. Vous pourrez faire une pause ou terminer la séance.",
    "commencer": "Commencer le parcours",
    "valider": "Valider cette réponse",
    "continuer": "Continuer",
    "sans_reponse": "Je ne sais pas",
    "sans_question": "Je ne sais pas quoi demander",
    "question": "Votre question — sans score",
    "question_modele": "Une question possible : {modele}",
    "sujet_attendu": "Le sujet proposé est : {sujet}.",
    "vers_lecture": "Passer à la lecture",
    "vers_reformulation": "Passer à la reformulation",
    "vers_test": "Passer au test",
    "reformulation": "Votre reformulation",
    "relire": "Enregistrer ma tentative et relire",
    "absence_relire": "Je ne sais pas — relire avec une aide",
    "relecture": "Relecture demandée — la première réponse reste conservée",
    "fin_relecture": "Masquer le texte et répondre avec cette aide",
    "retour_s": "Comparez votre formulation au résumé. La correction automatique, limitée aux idées reconnues, sera disponible après le test.",
    "production": "Votre réponse : {reponse}",
    "absence": "Absence de réponse déclarée.",
    "modele": "Résumé possible : {modele}",
    "test_condition": "Rappel après le résumé modèle, sans le rouvrir.",
    "aidee": "Tentative après relecture ; la première réponse est conservée.",
    "pause": "Faire une pause",
    "pause_titre": "Séquence en pause",
    "pause_detail": "Les supports sont retirés. Une reprise pendant un rappel sera signalée dans le résultat.",
    "reprendre": "Reprendre",
    "fin": "Les deux réponses sont verrouillées. La correction peut être affichée.",
    "envoyer": "Afficher la correction",
    "resultat": "Séquence terminée — résultats par étape",
    "condition": "PQRST séquencé · texte masqué au rappel · test après résumé modèle",
    "reprise_corrigee": "Reprise d’un texte déjà corrigé pendant cette séance.",
    "idees_reconnues": "{nombre} idées reconnues automatiquement sur {total} ; comparez avec le résumé.",
    "reformulation_initiale": "Reformulation — première réponse",
    "reformulation_aidee": "Reformulation — après relecture",
    "test_initial": "Test {numero} — première réponse",
    "test_aide": "Test {numero} — après relecture",
    "correcte": "Réponse exacte",
    "incorrecte": "Réponse différente de celle attendue",
    "a_verifier": "À vérifier avec le résumé : certaines idées n’ont pas été reconnues automatiquement",
    "compatible": "Le seuil d’idées reconnues est atteint ; ce retour automatique reste limité",
    "contradiction": "Un point à vérifier avec le résumé a été repéré",
    "sans_relecture": "sans relecture supplémentaire",
    "apres_relecture": "après relecture",
    "reprise_interrompue": "après interruption",
    "interruptions": "Interruptions signalées : {nombre}.",
    "aide_limite": "Une relecture est disponible par rappel ; les reprises restent séparées.",
    "retour_question": "Question personnelle : {question} — sans score.",
    "indisponible": "Cette séquence ne peut pas être affichée. Revenez à l’accueil puis relancez la séance.",
}
