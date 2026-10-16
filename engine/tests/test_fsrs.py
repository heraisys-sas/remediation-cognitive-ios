"""Tests du module FSRS (répétition espacée des items déclaratifs).

Le planificateur étant déterministe (fuzzing désactivé), toutes les
échéances attendues sont stables.
"""

from datetime import datetime, timedelta, timezone

import pytest

from engine.srs.fsrs import CarteFSRS, est_due, planifier

T0 = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)


def _carte_en_revision(note: int = 3) -> tuple[CarteFSRS, datetime]:
    """Carte sortie de l'apprentissage (2 révisions réussies consécutives).

    Retourne (carte, instant_de_la_derniere_revision) ; la carte est en
    état « revision » avec une échéance loin dans le futur.
    """
    carte = CarteFSRS("item-test")
    carte, echeance_1 = planifier(carte, note, T0)  # pas d'apprentissage
    carte, echeance_2 = planifier(carte, note, echeance_1)  # graduation
    return carte, echeance_2


# -- état initial et est_due -------------------------------------------------


def test_nouvelle_carte_est_due_immediatement():
    carte = CarteFSRS("t1")
    # une carte neuve est due dès sa création
    assert est_due(carte, datetime.now(timezone.utc)) is True
    assert carte.etat == "apprentissage"
    assert carte.stabilite is None  # jamais revue


def test_est_due_avant_et_apres_echeance():
    carte = CarteFSRS("t2")
    carte, echeance = planifier(carte, 3, T0)
    assert est_due(carte, echeance - timedelta(seconds=1)) is False
    assert est_due(carte, echeance) is True  # l'échéance exacte compte
    assert est_due(carte, echeance + timedelta(days=30)) is True


# -- évolution des échéances ---------------------------------------------------


def test_echeance_croit_apres_rappel_reussi():
    carte = CarteFSRS("t3")
    carte, e1 = planifier(carte, 3, T0)
    carte, e2 = planifier(carte, 3, e1)
    assert e1 > T0
    assert e2 > e1
    # sortie d'apprentissage : l'intervalle dépasse largement le pas court
    assert (e2 - e1) > (e1 - T0)
    assert carte.etat == "revision"


def test_echeance_retombe_apres_echec():
    carte = CarteFSRS("t3b")
    carte, e1 = planifier(carte, 3, T0)   # pas d'apprentissage : un jour
    carte, e2 = planifier(carte, 3, e1)   # graduation : plusieurs jours
    intervalle_avant = e2 - e1
    carte, e3 = planifier(carte, 1, e2)   # échec à l'échéance
    intervalle_apres = e3 - e2
    assert intervalle_apres < intervalle_avant      # régression nette
    assert intervalle_apres <= timedelta(days=1)    # retour dès la séance suivante
    assert carte.etat == "reapprentissage"


def test_une_carte_revue_aujourdhui_n_est_pas_due_aujourd_hui():
    """L'unité de ce logiciel est la séance quotidienne, pas la minute.

    Régression constatée : les pas d'apprentissage par défaut de FSRS (1 min, 10 min)
    faisaient revenir tout un palier à chaque séance de la journée.
    """
    for note in (1, 3, 4):
        carte, echeance = planifier(CarteFSRS("t4"), note, T0)
        assert not est_due(carte, T0 + timedelta(hours=2)), note
        assert not est_due(carte, T0 + timedelta(hours=12)), note
        assert echeance >= T0 + timedelta(days=1) - timedelta(seconds=1), note
    # Un échec revient à la séance suivante, pas dans l'heure.
    carte, _ = planifier(CarteFSRS("t4b"), 1, T0)
    assert est_due(carte, T0 + timedelta(days=1) + timedelta(minutes=1))


def test_note_facile_allonge_plus_que_bon():
    carte, instant = _carte_en_revision()
    _, e_bon = planifier(carte, 3, instant)
    _, e_facile = planifier(carte, 4, instant)
    assert e_facile > e_bon


def test_difficulte_baisse_plus_avec_facile_quavec_bon():
    carte, instant = _carte_en_revision()
    bon, _ = planifier(carte, 3, instant)
    facile, _ = planifier(carte, 4, instant)
    assert facile.difficulte < bon.difficulte


# -- contrat d'interface -------------------------------------------------------


def test_planifier_ne_mute_pas_la_carte_recue():
    carte = CarteFSRS("t4")
    avant = carte.echeance
    _, _ = planifier(carte, 4, T0)
    assert carte.echeance == avant  # style immuable
    assert carte.etat == "apprentissage"


def test_note_invalide_est_rejetee():
    carte = CarteFSRS("t5")
    for note in (0, 5, -1):
        with pytest.raises(ValueError):
            planifier(carte, note, T0)


def test_type_invalide_est_rejete():
    with pytest.raises(TypeError):
        planifier("pas une carte", 3, T0)
    with pytest.raises(TypeError):
        est_due(None, T0)


def test_datetime_naif_interprete_comme_utc():
    carte = CarteFSRS("t6")
    carte, echeance = planifier(carte, 3, T0.replace(tzinfo=None))
    assert echeance.tzinfo is not None  # sortie normalisée UTC
    assert est_due(carte, (echeance - timedelta(seconds=1)).replace(tzinfo=None)) is False
    assert est_due(carte, echeance.replace(tzinfo=None)) is True


def test_roundtrip_serialisation():
    carte, _ = _carte_en_revision()
    data = carte.to_dict()
    assert data["item_id"] == "item-test"
    copie = CarteFSRS.from_dict(data)
    assert copie.item_id == carte.item_id
    assert copie.echeance == carte.echeance
    assert copie.stabilite == carte.stabilite
    assert copie.difficulte == carte.difficulte
    assert copie.etat == carte.etat


def test_from_dict_sans_item_id_est_rejete():
    with pytest.raises(ValueError):
        CarteFSRS.from_dict({"stability": 3.0})


def test_echeance_iso():
    carte = CarteFSRS("t7")
    assert isinstance(carte.echeance_iso(), str)
    carte, echeance = planifier(carte, 3, T0)
    assert carte.echeance_iso() == echeance.isoformat()
