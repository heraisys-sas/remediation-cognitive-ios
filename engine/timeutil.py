"""Utilitaires temporels partagés — source unique (P1-B1).

`normaliser_utc` était dupliqué dans `engine.srs.fsrs` et
`engine.session.runner`. Une seule définition ici, consommée par les deux,
pour éviter toute divergence de gestion des fuseaux (un datetime naïf est
toujours supposé UTC).
"""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["normaliser_utc"]


def normaliser_utc(instant: datetime) -> datetime:
    """Normalise un datetime vers UTC (un datetime naïf est supposé UTC).

    - naïf            -> interprété comme UTC ;
    - avec fuseau     -> converti en UTC.
    """
    if instant.tzinfo is None:
        return instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(timezone.utc)
