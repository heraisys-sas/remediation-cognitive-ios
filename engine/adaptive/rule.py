"""Règle adaptative v1 : ajustement ±1 palier selon le taux de réussite glissant.

Interface prête pour une migration IRT (Phase 4 de la feuille de route,
quand les données utilisateur le permettront).
"""


def ajuster_palier(
    palier_actuel: int,
    taux_reussite_glissant: float,
    seuil_bas: float = 0.6,
    seuil_haut: float = 0.9,
) -> int:
    """Ajuste le palier : +1 si fluide, -1 si en difficulté, stable sinon."""
    if taux_reussite_glissant >= seuil_haut:
        return palier_actuel + 1
    if taux_reussite_glissant < seuil_bas:
        return max(1, palier_actuel - 1)
    return palier_actuel


def calculer_taux_glissant(historique: list[bool], fenetre: int = 8) -> float:
    """Taux de réussite sur les ``fenetre`` derniers essais.

    - ``historique`` : résultats chronologiques (True = réussite) ;
    - ``fenetre`` : taille de la fenêtre glissante (défaut 8).

    Si la fenêtre dépasse la taille de l'historique, tout l'historique est
    utilisé ; un historique vide vaut 0.0 ; ``fenetre < 1`` lève ValueError.
    """
    if fenetre < 1:
        raise ValueError(f"fenetre invalide : {fenetre} (attendu >= 1)")
    if not historique:
        return 0.0
    dernieres = historique[-fenetre:]
    return sum(1 for reussite in dernieres if reussite) / len(dernieres)
