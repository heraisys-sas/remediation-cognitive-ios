"""Orchestration d'une séance (5–10 min).

Responsabilités :
- servir les items dans l'ordre : la sélection amont (règle adaptative +
  FSRS) est faite par l'appelant et injectée via ``items`` ;
- respecter le dosage : nombre d'items maximal et durée maximale. Ces
  garde-fous sont codés en dur : le moteur cesse de *proposer* des items,
  il n'interrompt jamais l'utilisateur en cours d'item ;
- surveiller la fatigabilité (dégradation du RT, montée du taux d'erreur)
  et **proposer** l'arrêt via un simple booléen — jamais forcé, jamais
  bloqué (règle clinique : la proposition n'arrête rien d'elle-même) ;
- produire un résumé de fin de séance.

Aucune notion de persistance ici : le backend s'en charge (ADR-002).
"""

from __future__ import annotations

from datetime import datetime, timezone
from numbers import Real

from engine.timeutil import normaliser_utc as _normaliser_utc

from engine.adaptive.rule import calculer_taux_glissant

# Seuils de fatigabilité (docs/10-clinique/protocoles.md) : la détection
# n'est qu'une proposition d'arrêt mise à disposition de l'UI.
FENETRE_FATIGUE = 5  # réponses récentes prises en compte
SEUIL_RT_FATIGUE = 1.25  # RT moyen glissant > 1,25 × baseline → proposition
SEUIL_TAUX_ERREUR = 0.40  # taux d'erreur glissant ≥ 0,40 → proposition
MIN_REPONSES_FATIGUE = 3  # anti-bruit : pas d'alerte avant ce nombre


def _extraire_item_id(item) -> str:
    """Extrait l'identifiant d'un item (attribut ``item_id`` ou clé de dict)."""
    if isinstance(item, dict):
        try:
            return item["item_id"]
        except KeyError as exc:
            raise ValueError("item dict sans clé 'item_id'") from exc
    item_id = getattr(item, "item_id", None)
    if item_id is None:
        raise ValueError("item sans identifiant : attribut 'item_id' requis")
    return item_id


class SessionRunner:
    """Déroulé d'une séance : servir, enregistrer, surveiller, résumer.

    Paramètres :
    - ``items`` : séquence ordonnée d'items déjà choisis par l'appelant
      (chaque item expose ``item_id`` comme attribut ou comme clé de dict) ;
    - ``max_items`` : quota d'items de la séance (défaut 12) ;
    - ``duree_max_s`` : durée maximale en secondes (défaut 600 = 10 min) ;
    - ``baseline_rt_ms`` : temps de réaction de référence en ms (défaut
      1000) ; la baseline réelle de l'utilisateur est une responsabilité
      backend, cette valeur n'est qu'un point de départ paramétrable ;
    - ``depart`` : instant de départ injectable (tests, reprise de séance) ;
      par défaut l'instant de construction.

    Contrat « fatigue » : ``doit_proposer_arret`` ne fait que renvoyer un
    booléen ; elle n'interrompt, ne bloque et ne lève jamais rien. Les
    seules conditions d'arrêt de service d'items sont le quota, la durée
    et la fin de liste — jamais la fatigue.
    """

    def __init__(
        self,
        items,
        max_items: int = 12,
        duree_max_s: float = 600.0,
        baseline_rt_ms: float = 1000.0,
        depart: datetime | None = None,
    ) -> None:
        self.items = list(items)
        self.max_items = int(max_items)
        self.duree_max_s = float(duree_max_s)
        self.baseline_rt_ms = float(baseline_rt_ms)
        if self.max_items < 0:
            raise ValueError("max_items ne peut pas être négatif")
        if self.duree_max_s <= 0:
            raise ValueError("duree_max_s doit être strictement positif")
        if self.baseline_rt_ms <= 0:
            raise ValueError("baseline_rt_ms doit être strictement positif")
        # Fail-fast : un item sans identifiant est une erreur de contrat.
        self._ids = [_extraire_item_id(item) for item in self.items]
        self._index = 0  # nombre d'items servis
        self._reponses: list[dict] = []
        self._depart = (
            _normaliser_utc(depart) if depart is not None else datetime.now(timezone.utc)
        )
        self._terminee = False

    # -- déroulé -----------------------------------------------------------

    def prochain_item(self):
        """Retourne l'item suivant à présenter, ou None si séance pleine.

        None si : tous les items servis, quota ``max_items`` atteint, durée
        maximale atteinte ou séance déjà terminée. La fatigue NE fait PAS
        partie des conditions d'arrêt (proposition seulement).
        """
        if self._terminee:
            return None
        if self._index >= len(self.items) or self._index >= self.max_items:
            return None
        if self._secondes_ecoulees() >= self.duree_max_s:
            return None
        item = self.items[self._index]
        self._index += 1
        return item

    def enregistrer_reponse(self, item_id: str, correcte: bool, temps_ms: float) -> dict:
        """Enregistre une réponse et retourne un dict de feedback.

        Le feedback contient : item_id, correcte, temps_ms, nb_reponses,
        taux_reussite_glissant, rt_moyen_glissant_ms et alerte_fatigue
        (indicateur booléen destiné à l'UI — une proposition, jamais une
        interruption).

        Une réponse par item servi est le flux nominal ; des réponses
        supplémentaires (reprises errorless) sont comptabilisées comme essais.
        Lève ValueError si l'item n'a pas été servi ou si temps_ms est invalide.
        """
        servis = self._ids[: self._index]
        if item_id not in servis:
            raise ValueError(f"réponse pour un item non proposé : {item_id!r}")
        if isinstance(temps_ms, bool) or not isinstance(temps_ms, Real):
            raise ValueError("temps_ms doit être un nombre de millisecondes")
        if temps_ms < 0:
            raise ValueError("temps_ms ne peut pas être négatif")
        reponse = {
            "item_id": item_id,
            "correcte": bool(correcte),
            "temps_ms": float(temps_ms),
        }
        self._reponses.append(reponse)
        fenetre = self._reponses[-FENETRE_FATIGUE:]
        return {
            "item_id": item_id,
            "correcte": bool(correcte),
            "temps_ms": float(temps_ms),
            "nb_reponses": len(self._reponses),
            "taux_reussite_glissant": calculer_taux_glissant(
                [r["correcte"] for r in fenetre], fenetre=FENETRE_FATIGUE
            ),
            "rt_moyen_glissant_ms": sum(r["temps_ms"] for r in fenetre) / len(fenetre),
            "alerte_fatigue": self.doit_proposer_arret(),
        }

    def doit_proposer_arret(self) -> bool:
        """Fatigue détectée : True si l'UI doit *proposer* l'arrêt.

        Critères (sur la fenêtre glissante, après MIN_REPONSES_FATIGUE
        réponses pour éviter le bruit statistique) :
        - RT moyen glissant > 1,25 × baseline_rt_ms, OU
        - taux d'erreur glissant ≥ 0,40.

        Garde-fou clinique : simple indicateur. Cette méthode n'interrompt
        jamais la séance, ne bloque aucun appel et ne lève jamais.
        """
        fenetre = self._reponses[-FENETRE_FATIGUE:]
        if len(fenetre) < MIN_REPONSES_FATIGUE:
            return False
        rt_moyen = sum(r["temps_ms"] for r in fenetre) / len(fenetre)
        taux_erreur = 1.0 - sum(1 for r in fenetre if r["correcte"]) / len(fenetre)
        return (
            rt_moyen > SEUIL_RT_FATIGUE * self.baseline_rt_ms
            or taux_erreur >= SEUIL_TAUX_ERREUR
        )

    def terminer(self) -> dict:
        """Clôt la séance et retourne le résumé (persisté par le backend).

        Clés : items (servis), correctes, erreurs, duree_s, taux_reussite
        (sur l'ensemble des essais ; 0.0 si aucune réponse), rt_moyen_ms
        (None si aucune réponse), alerte_fatigue (proposition, jamais
        forcée). Après terminer(), plus aucun item n'est servi.
        """
        self._terminee = True
        nb_reponses = len(self._reponses)
        correctes = sum(1 for r in self._reponses if r["correcte"])
        return {
            "items": self._index,
            "correctes": correctes,
            "erreurs": nb_reponses - correctes,
            "duree_s": round(self._secondes_ecoulees(), 1),
            "taux_reussite": correctes / nb_reponses if nb_reponses else 0.0,
            "rt_moyen_ms": (
                round(sum(r["temps_ms"] for r in self._reponses) / nb_reponses, 1)
                if nb_reponses
                else None
            ),
            "alerte_fatigue": self.doit_proposer_arret(),
        }

    # -- interne -------------------------------------------------------------

    def _secondes_ecoulees(self) -> float:
        """Secondes écoulées depuis le départ de la séance."""
        return (datetime.now(timezone.utc) - self._depart).total_seconds()
