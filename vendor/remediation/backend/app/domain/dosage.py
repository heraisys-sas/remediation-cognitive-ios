"""Dosage des séances (garde-fou clinique).

Règles issues de docs/10-clinique/protocoles.md :
- séance courte 5–10 min ;
- limite de sessions par fenêtre (jour, ou semaine pour l'évaluation),
  dérogation explicite possible — ADR-021 ;
- cap de difficulté configurable avec justification pédagogique explicite
  (anti sur-sollicitation post-commotionnelle).
"""

from datetime import date, timedelta


def verifier_droit_de_session(nb_sessions_du_jour: int, limite: int) -> bool:
    return nb_sessions_du_jour < limite


# Garde-fous chiffrés du sprint 1 (docs/30-technique/api-contract.md) —
# paramétrables ici uniquement, jamais côté client.
LIMITE_SESSIONS_DEFAUT = 3
FENETRE_SESSIONS_DEFAUT = "jour"
MAX_ITEMS_PAR_SEANCE = 12
DUREE_MAX_SEANCE_S = 600

#: Paramètres de séance par thème, quand la **nature de l'exercice** le justifie.
#:
#: Le cadre clinique reste « séance courte, ≤ 10 min » (docs/10-clinique/cadre-usage.md)
#: et « 5-10 min » (protocoles.md). Ce qu'on ajuste par thème, c'est le **nombre
#: d'exercices** : une grille de déduction demande une chaîne de raisonnement complète
#: (mémoire de travail + fonctions exécutives) et dure bien plus longtemps qu'un item
#: de calcul mental — douze grilles ne tiendraient pas dans une séance.
from .catalog import PARAMETRES_THEME

PARAMETRES_SEANCE_DEFAUT: dict[str, int | bool] = {
    "max_items": MAX_ITEMS_PAR_SEANCE,
    "duree_max_s": DUREE_MAX_SEANCE_S,
    "duree_proposee": True,
}


def parametres_seance(theme: str) -> dict[str, int | bool]:
    return {**PARAMETRES_SEANCE_DEFAUT, **PARAMETRES_THEME.get(theme, {})}


def duree_proposee(theme: str) -> bool:
    """La durée maximale est-elle une **proposition** pour ce thème ?

    Oui, partout (ADR-010) : au-delà de la durée, la séance **propose** l'arrêt — elle ne
    se ferme pas d'elle-même, la personne décide de continuer ou non. Le garde-fou de
    sur-sollicitation reste : la limite de séances par jour, et le nombre d'exercices
    par séance. Le paramètre subsiste pour qu'un thème puisse un jour demander une limite
    ferme (le code de clôture existe toujours).
    """
    return bool(parametres_seance(theme)["duree_proposee"])

#: Nombre maximal de reprises par séance : un exercice manqué revient **une fois**, en fin
#: de séance, avec la réponse fournie avant le nouvel essai (errorless learning : ré-encoder
#: une erreur la renforce). Plafonné pour ne pas doubler la durée de la séance — au-delà, les
#: exercices manqués reviennent à la séance suivante, par la répétition espacée.
MAX_REPRISES_PAR_SEANCE = 4

#: Plafond de séances par CATÉGORIE de thème : limite et fenêtre de comptage.
#: L'évaluation est limitée à une séance par **semaine** (fenêtre du lundi au
#: dimanche) : répéter une mesure la fausse (effet d'apprentissage), l'espacer
#: d'une semaine la protège mieux qu'un plafond quotidien ; l'entraînement de
#: remédiation, lui, gagne à être régulier (3 par jour).
LIMITES_SESSIONS: dict[str, dict[str, int | str]] = {
    "entrainement": {"limite": 3, "fenetre": "jour"},
    "cible": {"limite": 3, "fenetre": "jour"},
    "evaluation": {"limite": 1, "fenetre": "semaine"},
}


def appliquer_cap_difficulte(palier_demande: int, cap_actif: int) -> int:
    """Ne jamais dépasser le cap de difficulté actif."""
    return min(palier_demande, cap_actif)


def limite_sessions(categorie: str) -> int:
    return int(LIMITES_SESSIONS.get(categorie, {}).get("limite", LIMITE_SESSIONS_DEFAUT))


def limite_sessions_theme(theme: str, categorie: str) -> int:
    return int(parametres_seance(theme).get("limite_sessions", limite_sessions(categorie)))


def fenetre_sessions(categorie: str) -> str:
    return str(LIMITES_SESSIONS.get(categorie, {}).get("fenetre", FENETRE_SESSIONS_DEFAUT))


def debut_fenetre(fenetre: str, reference: date) -> date:
    """Premier jour de la fenêtre de comptage qui contient ``reference``.

    « jour » → la date elle-même ; « semaine » → le lundi de la semaine
    calendaire (lundi–dimanche).
    """
    if fenetre == "semaine":
        return reference - timedelta(days=reference.weekday())
    return reference
