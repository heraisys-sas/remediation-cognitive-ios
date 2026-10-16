"""Repérage du jour courant dans le programme d'entraînement (logique pure).

Le programme est un contenu versionné (`content/programmes/`) ; ce module ne fait
que **situer une date** dans ce programme. Aucune progression n'est calculée ici :
le palier réel reste décidé par la maîtrise, dans le moteur.

Fonctions pures (date en entrée, plan en sortie) : testables sans serveur.
"""

from __future__ import annotations

from datetime import date

#: Types de jour du programme.
TYPE_SEANCE = "seance"
TYPE_LEGERE = "legere"
TYPE_REPOS = "repos"


def jour_du_programme(programme: dict, date_debut: date, aujourd_hui: date) -> dict | None:
    """Plan du jour correspondant à ``aujourd_hui`` (None hors période).

    - avant la date de début → None ;
    - au-delà de la dernière semaine → None (programme terminé).
    """
    if programme is None:
        return None
    semaines = programme.get("semaines") or []
    if not semaines or aujourd_hui < date_debut:
        return None
    ecart = (aujourd_hui - date_debut).days
    index_semaine, index_jour = divmod(ecart, 7)
    if index_semaine >= len(semaines):
        return None
    semaine = semaines[index_semaine]
    jours = semaine.get("jours") or []
    if index_jour >= len(jours):
        return None
    jour = jours[index_jour]
    return {
        "semaine": semaine.get("semaine"),
        "jour": jour.get("jour"),
        "type": jour.get("type"),
        "duree_min": jour.get("duree_min"),
        "themes": jour.get("themes") or [],
        "themes_extra": jour.get("themes_extra") or [],
        "plafond_palier": semaine.get("plafond_palier") or {},
        "jour_depuis_debut": ecart + 1,
        "jours_restants": (len(semaines) * 7) - (ecart + 1),
        "termine": False,
    }


def resume_programme(programme: dict, date_debut: date, aujourd_hui: date) -> dict:
    """Plan du jour + repères de progression (ou état « terminé »/« à venir »)."""
    plan = jour_du_programme(programme, date_debut, aujourd_hui)
    if plan is not None:
        return plan
    if aujourd_hui < date_debut:
        return {"type": "a_venir", "jour_depuis_debut": 0, "jours_restants": (len(programme.get("semaines") or []) * 7)}
    return {"type": "termine", "jour_depuis_debut": (aujourd_hui - date_debut).days + 1, "jours_restants": 0}
