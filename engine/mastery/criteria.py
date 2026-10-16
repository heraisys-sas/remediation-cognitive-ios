"""Critère de maîtrise : pas de passage au palier suivant sans fluidité.

Défaut : 90 % de réussite sur 3 sessions consécutives (paramétrable).
Un suivi par palier est fourni pour les historiques où l'utilisateur a
changé de palier en cours de route (baisse, remontée) : les sessions
comptent par palier, pas globalement.
"""


def palier_maitrise(
    taux_par_session: list[float],
    seuil: float = 0.9,
    sessions_consecutives: int = 3,
) -> bool:
    """True si les N dernières sessions consécutives atteignent le seuil."""
    if len(taux_par_session) < sessions_consecutives:
        return False
    return all(t >= seuil for t in taux_par_session[-sessions_consecutives:])


def palier_maitrise_historique(
    historique: list[tuple[int, float]],
    palier: int | None = None,
    seuil: float = 0.9,
    sessions_consecutives: int = 3,
) -> bool:
    """Suivi de maîtrise par palier sur un historique chronologique.

    - ``historique`` : liste de couples ``(palier, taux_de_reussite)``
      dans l'ordre chronologique des sessions ;
    - ``palier`` : palier à évaluer ; None = le palier le plus récent ;
    - applique le même critère que ``palier_maitrise`` (N dernières
      sessions consécutives au seuil), restreint aux sessions passées
      à ce palier : un changement de palier réinitialise le comptage.

    Un historique vide, ou un palier avec moins de ``sessions_consecutives``
    sessions, n'est jamais maîtrisé.
    """
    if not historique:
        return False
    cible = palier if palier is not None else historique[-1][0]
    taux = [taux for p, taux in historique if p == cible]
    if len(taux) < sessions_consecutives:
        return False
    return all(t >= seuil for t in taux[-sessions_consecutives:])
