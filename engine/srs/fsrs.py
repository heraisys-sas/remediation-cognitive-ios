"""Répétition espacée FSRS (successeur open-source de SM-2).

Encapsulation de la bibliothèque officielle `fsrs` (open-spaced-repetition,
v6.x) derrière une interface propre, indépendante du backend : le moteur de
session ne manipule que `CarteFSRS`, `planifier` et `est_due`.

Décisions de conception :
- Planificateur déterministe (fuzzing désactivé) : les échéances sont
  reproductibles, ce qui est requis pour les tests et le suivi clinique.
- `planifier` ne mute pas la carte reçue : elle retourne une nouvelle
  `CarteFSRS` (style immuable, la carte d'origine reste consultable).
- Les datetimes naïfs sont interprétés comme UTC ; toutes les échéances
  produites sont des datetimes utc-aware.
- Aucune I/O ici : la persistance passe par `to_dict` / `from_dict` et
  reste de la responsabilité du backend (ADR-002).

Note d'installation : le paquet `fsrs` (pip3 install fsrs, v6.3.2, Python
3.13) s'installe correctement ; le fallback SM-2 prévu en cas d'échec n'a
pas été nécessaire.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fsrs import Card, Rating, Scheduler, State

from engine.timeutil import normaliser_utc

#: Pas d'apprentissage et de réapprentissage, à l'échelle de CE logiciel.
#:
#: Les pas par défaut de FSRS (1 minute, 10 minutes) viennent des applications de
#: révision continue (Anki) : ils font revenir une carte plusieurs fois dans la même
#: heure. Ici, l'unité est la **séance quotidienne** — une carte revue aujourd'hui n'a
#: pas à revenir aujourd'hui, sinon chaque séance ressert la même série (constaté en
#: usage : tout un palier revenait à chaque séance, les cartes restant en phase
#: d'apprentissage avec une échéance de dix minutes).
#:
#: Un pas d'un jour laisse la main au programme, qui propose chaque thème environ deux
#: fois par semaine : les cartes redeviennent dues quand le thème revient, et une séance
#: ne ressert plus ce qui vient d'être vu.
_PAS_APPRENTISSAGE = (timedelta(days=1),)
_PAS_REAPPRENTISSAGE = (timedelta(days=1),)

# Planificateur partagé, déterministe (fuzzing désactivé).
# desired_retention reste au défaut FSRS (0.9) : l'ajustement clinique
# éventuel se fera via un ADR dédié, pas en silice ici.
_PLANIFICATEUR = Scheduler(
    learning_steps=_PAS_APPRENTISSAGE,
    relearning_steps=_PAS_REAPPRENTISSAGE,
    enable_fuzzing=False,
)

# Note utilisateur (1..4) -> évaluation FSRS.
# 1 = encore (Again), 2 = difficile (Hard), 3 = bon (Good), 4 = facile (Easy).
_NOTE_VERS_RATING: dict[int, Rating] = {
    1: Rating.Again,
    2: Rating.Hard,
    3: Rating.Good,
    4: Rating.Easy,
}

# État FSRS -> libellé français (l'état « nouveau » est couvert par
# Learning sans step dans fsrs v6).
_LIBELLES_ETAT: dict[State, str] = {
    State.Learning: "apprentissage",
    State.Review: "revision",
    State.Relearning: "reapprentissage",
}


class CarteFSRS:
    """Item déclaratif (table, verbe, commande Python) et son état FSRS.

    Attributs publics :
    - ``item_id`` : identifiant stable de l'item (côté contenu/backend) ;
    - ``stabilite`` / ``difficulte`` : paramètres FSRS (None tant que la
      carte n'a pas été revue) ;
    - ``echeance`` : datetime UTC de la prochaine présentation ;
    - ``etat`` : libellé français de l'état FSRS courant.

    L'état FSRS interne (`fsrs.Card`) est encapsulé : les couches
    appelantes n'y accèdent jamais directement.
    """

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        # Carte FSRS interne : une nouvelle carte est immédiatement due
        # (fsrs initialise `due` à la création).
        self._card = Card()

    # -- état exposé ------------------------------------------------------

    @property
    def stabilite(self) -> float | None:
        """Stabilité FSRS (jours), None tant que la carte n'a pas été revue."""
        return self._card.stability

    @property
    def difficulte(self) -> float | None:
        """Difficulté FSRS (1..10), None tant que la carte n'a pas été revue."""
        return self._card.difficulty

    @property
    def echeance(self) -> datetime | None:
        """Prochaine présentation (datetime UTC), None si jamais planifiée."""
        return self._card.due

    @property
    def etat(self) -> str:
        """Libellé français de l'état FSRS (apprentissage/revision/...)."""
        return _LIBELLES_ETAT.get(self._card.state, "inconnu")

    def echeance_iso(self) -> str | None:
        """Échéance au format ISO-8601 (pratique pour la persistance JSON)."""
        return self._card.due.isoformat() if self._card.due is not None else None

    # -- sérialisation (le backend persiste, le moteur ne sait pas lire) --

    def to_dict(self) -> dict:
        """Sérialise la carte (item_id + état FSRS) pour le backend."""
        return {"item_id": self.item_id, **self._card.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "CarteFSRS":
        """Reconstruit une carte depuis `to_dict`."""
        donnees = dict(data)
        item_id = donnees.pop("item_id", None)
        if item_id is None:
            raise ValueError("champ 'item_id' manquant")
        carte = cls(item_id)
        carte._card = Card.from_dict(donnees)
        return carte

    def __repr__(self) -> str:
        return (
            f"CarteFSRS(item_id={self.item_id!r}, etat={self.etat!r}, "
            f"echeance={self.echeance_iso()!r})"
        )


def planifier(
    carte: CarteFSRS,
    note: int,
    maintenant: datetime,
) -> tuple[CarteFSRS, datetime]:
    """Applique une révision FSRS et retourne ``(carte_mise_a_jour, echeance)``.

    - ``note`` : auto-évaluation 1..4 — 1 = encore, 2 = difficile,
      3 = bon, 4 = facile ;
    - ``maintenant`` : instant de la révision (naïf = interprété UTC) ;
    - ``echeance`` : datetime UTC de la prochaine présentation.

    La carte reçue n'est pas modifiée : une nouvelle instance est retournée.
    Lève ``TypeError`` si ``carte`` n'est pas une ``CarteFSRS`` et
    ``ValueError`` si la note est hors 1..4.
    """
    if not isinstance(carte, CarteFSRS):
        raise TypeError("planifier attend une instance de CarteFSRS")
    rating = _NOTE_VERS_RATING.get(note)
    if rating is None:
        raise ValueError(f"note invalide : {note!r} (attendu 1 à 4)")
    instant = normaliser_utc(maintenant)
    carte_fsrs, _journal = _PLANIFICATEUR.review_card(
        carte._card, rating, review_datetime=instant
    )
    mise_a_jour = CarteFSRS(carte.item_id)
    mise_a_jour._card = carte_fsrs
    return mise_a_jour, carte_fsrs.due


def est_due(carte: CarteFSRS, maintenant: datetime) -> bool:
    """True si la carte doit être présentée à l'instant ``maintenant``.

    Une carte jamais planifiée (échéance absente) est considérée due.
    L'échéance exacte compte comme due (>=).
    """
    if not isinstance(carte, CarteFSRS):
        raise TypeError("est_due attend une instance de CarteFSRS")
    if carte.echeance is None:
        return True
    return carte.echeance <= normaliser_utc(maintenant)
