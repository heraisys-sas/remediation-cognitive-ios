"""Détection de fatigabilité cognitive (garde-fou clinique).

Indicateur : dégradation du temps de réaction (RT) et montée du taux d'erreur
en cours de session — fréquent en SPC → proposition d'arrêt (jamais forcée).
"""


def alerter_fatigue(
    rt_glissant: list[float],
    baseline_rt: float,
    taux_erreur_glissant: float = 0.0,
    seuil_rt: float = 1.25,
    seuil_erreur: float = 0.4,
) -> bool:
    """True si une alerte de fatigue doit être proposée à l'utilisateur.

    Heuristique v1 : RT glissant > seuil × baseline OU taux d'erreur > seuil.
    À calibrer avec les premières données réelles.
    """
    if not rt_glissant:
        return False
    rt_moyen = sum(rt_glissant) / len(rt_glissant)
    return rt_moyen > baseline_rt * seuil_rt or taux_erreur_glissant > seuil_erreur
