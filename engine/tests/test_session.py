"""Tests de l'orchestration de séance (dosage, fatigue proposée, résumé)."""

from datetime import datetime, timedelta, timezone

import pytest

from engine.session.runner import SessionRunner


class _Item:
    """Item minimal : un identifiant suffit au runner."""

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id


def _items(n: int) -> list[_Item]:
    return [_Item(f"item-{i}") for i in range(n)]


def _derouler(runner: SessionRunner, reponses: list[tuple[bool, float]]) -> None:
    """Sert puis enregistre séquentiellement une liste (correcte, temps_ms)."""
    for correcte, temps in reponses:
        item = runner.prochain_item()
        assert item is not None
        runner.enregistrer_reponse(item.item_id, correcte, temps)


# -- service des items ---------------------------------------------------------


def test_sert_les_items_dans_lordre():
    runner = SessionRunner(_items(3))
    servis = [runner.prochain_item() for _ in range(4)]
    assert [item.item_id for item in servis[:3]] == ["item-0", "item-1", "item-2"]
    assert servis[3] is None


def test_seance_pleine_au_quota_max_items():
    runner = SessionRunner(_items(10), max_items=2)
    assert runner.prochain_item() is not None
    assert runner.prochain_item() is not None
    assert runner.prochain_item() is None  # quota atteint


def test_liste_vide_ne_leve_jamais():
    runner = SessionRunner([])
    assert runner.prochain_item() is None


def test_duree_max_cesse_de_servir_sans_erreur():
    depart = datetime.now(timezone.utc) - timedelta(seconds=601)
    runner = SessionRunner(_items(5), duree_max_s=600, depart=depart)
    assert runner.prochain_item() is None  # dosage : plus de service


def test_items_sous_forme_de_dict():
    runner = SessionRunner([{"item_id": "a"}, {"item_id": "b"}])
    assert runner.prochain_item()["item_id"] == "a"
    runner.enregistrer_reponse("a", True, 800)
    assert runner.prochain_item()["item_id"] == "b"


def test_item_sans_identifiant_rejete_a_l_init():
    with pytest.raises(ValueError):
        SessionRunner(["nu"])


def test_parametres_invalides_rejetes():
    with pytest.raises(ValueError):
        SessionRunner(_items(1), max_items=-1)
    with pytest.raises(ValueError):
        SessionRunner(_items(1), duree_max_s=0)
    with pytest.raises(ValueError):
        SessionRunner(_items(1), baseline_rt_ms=0)


# -- enregistrement des réponses -----------------------------------------------


def test_reponse_item_non_propose_rejetee():
    runner = SessionRunner(_items(2))
    with pytest.raises(ValueError):
        runner.enregistrer_reponse("item-0", True, 900)  # pas encore servi
    runner.prochain_item()
    runner.enregistrer_reponse("item-0", True, 900)  # OK une fois servi


def test_temps_ms_invalide_rejete():
    runner = SessionRunner(_items(1))
    runner.prochain_item()
    with pytest.raises(ValueError):
        runner.enregistrer_reponse("item-0", True, -5)
    with pytest.raises(ValueError):
        runner.enregistrer_reponse("item-0", True, "lent")


def test_feedback_contient_les_indicateurs():
    runner = SessionRunner(_items(3), baseline_rt_ms=1000)
    item = runner.prochain_item()
    feedback = runner.enregistrer_reponse(item.item_id, True, 800)
    assert feedback["item_id"] == "item-0"
    assert feedback["correcte"] is True
    assert feedback["temps_ms"] == 800.0
    assert feedback["nb_reponses"] == 1
    assert feedback["taux_reussite_glissant"] == 1.0
    assert feedback["rt_moyen_glissant_ms"] == 800.0
    assert feedback["alerte_fatigue"] is False


# -- détection de fatigue (proposition, jamais forcé) ----------------------------


def test_fatigue_proposee_si_rt_degrade():
    runner = SessionRunner(_items(10), baseline_rt_ms=1000)
    _derouler(runner, [(True, 1300)] * 5)  # RT moyen 1300 > 1,25 × 1000
    assert runner.doit_proposer_arret() is True


def test_fatigue_proposee_si_taux_erreur_haut():
    runner = SessionRunner(_items(10))
    _derouler(runner, [(False, 500), (False, 500), (True, 500), (False, 500), (False, 500)])
    # 4 échecs / 5 → taux d'erreur 0,8 ≥ 0,40
    assert runner.doit_proposer_arret() is True


def test_pas_dalerte_si_performance_stable():
    runner = SessionRunner(_items(10), baseline_rt_ms=1000)
    _derouler(runner, [(True, 900)] * 5)
    assert runner.doit_proposer_arret() is False


def test_seuil_rt_est_strictement_superieur():
    runner = SessionRunner(_items(10), baseline_rt_ms=1000)
    _derouler(runner, [(True, 1250)] * 5)  # 1250 == 1,25 × 1000 → pas d'alerte
    assert runner.doit_proposer_arret() is False


def test_seuil_erreur_est_inclusif():
    runner = SessionRunner(_items(10))
    _derouler(runner, [(False, 500), (False, 500), (True, 500), (True, 500), (True, 500)])
    # 2 échecs / 5 → taux d'erreur 0,40 exactement → alerte
    assert runner.doit_proposer_arret() is True


def test_pas_dalerte_avec_peu_de_donnees():
    """Anti-bruit : 2 réponses désastreuses ne suffisent pas à alerter."""
    runner = SessionRunner(_items(10), baseline_rt_ms=1000)
    _derouler(runner, [(False, 5000), (False, 5000)])
    assert runner.doit_proposer_arret() is False


def test_la_fatigue_ninterrompt_jamais_la_seance():
    """Garde-fou clinique : l'alerte ne bloque aucun service d'item."""
    runner = SessionRunner(_items(8), baseline_rt_ms=1000)
    _derouler(runner, [(False, 4000)] * 5)  # alerte fatiguée certaine
    assert runner.doit_proposer_arret() is True
    # l'utilisateur continue : les 3 items restants sont servis normalement
    restants = [runner.prochain_item() for _ in range(4)]
    assert all(item is not None for item in restants[:3])
    assert restants[3] is None  # fin de liste, pas de blocage fatigue
    # le résumé reste cohérent et consultable
    resume = runner.terminer()
    assert resume["items"] == 8
    assert isinstance(resume["alerte_fatigue"], bool)


def test_la_fatigue_ne_leve_aucune_exception():
    runner = SessionRunner(_items(3))
    assert runner.doit_proposer_arret() is False  # zéro réponse
    runner.prochain_item()
    runner.enregistrer_reponse("item-0", False, 9999)
    assert isinstance(runner.doit_proposer_arret(), bool)  # un seul booléen


# -- résumé de fin de séance ---------------------------------------------------


def test_resume_coherent():
    depart = datetime.now(timezone.utc) - timedelta(seconds=120)
    runner = SessionRunner(_items(6), depart=depart)
    _derouler(runner, [(True, 800), (True, 900), (True, 1000), (True, 850), (False, 950)])
    resume = runner.terminer()
    assert resume["items"] == 5
    assert resume["correctes"] == 4
    assert resume["erreurs"] == 1
    assert resume["taux_reussite"] == pytest.approx(0.8)
    assert 100 <= resume["duree_s"] <= 200  # départ injecté il y a ~120 s
    assert resume["rt_moyen_ms"] == pytest.approx(900.0)
    assert resume["alerte_fatigue"] is False  # RT ok, 1 erreur / 5
    # après terminer(), plus aucun item n'est servi
    assert runner.prochain_item() is None


def test_resume_session_vide():
    runner = SessionRunner([])
    resume = runner.terminer()
    assert resume["items"] == 0
    assert resume["correctes"] == 0
    assert resume["taux_reussite"] == 0.0
    assert resume["rt_moyen_ms"] is None
    assert resume["alerte_fatigue"] is False


def test_resume_alerte_fatigue_reflete_la_detection():
    depart = datetime.now(timezone.utc)
    runner = SessionRunner(_items(6), baseline_rt_ms=1000, depart=depart)
    _derouler(runner, [(False, 1300)] * 5)  # RT > seuil ET erreurs
    resume = runner.terminer()
    assert resume["alerte_fatigue"] is True
    assert resume["taux_reussite"] == 0.0
