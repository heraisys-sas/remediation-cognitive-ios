from datetime import datetime, timezone

import pytest

from engine.adaptive.rule import ajuster_palier, calculer_taux_glissant

T0 = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)


# -- ajuster_palier ------------------------------------------------------------


def test_progres_si_reussite_haute():
    assert ajuster_palier(3, 0.95) == 4


def test_recule_si_reussite_basse():
    assert ajuster_palier(3, 0.4) == 2


def test_stable_si_zone_neutre():
    assert ajuster_palier(3, 0.75) == 3


def test_ne_descend_pas_sous_palier_1():
    assert ajuster_palier(1, 0.1) == 1


# -- calculer_taux_glissant ------------------------------------------------------


def test_taux_glissant_historique_vide():
    assert calculer_taux_glissant([]) == 0.0


def test_taux_glissant_fenetre_par_defaut_8():
    # [T ×10, F ×2] : la fenêtre (8 dernières) ignore les 4 plus anciens
    historique = [True] * 10 + [False] * 2
    assert calculer_taux_glissant(historique) == pytest.approx(6 / 8)


def test_taux_glissant_fenetre_plus_grande_que_historique():
    assert calculer_taux_glissant([True, False, True], fenetre=8) == pytest.approx(2 / 3)


def test_taux_glissant_fenetre_personnalisee():
    historique = [True, False, False, False]
    assert calculer_taux_glissant(historique, fenetre=2) == 0.0
    assert calculer_taux_glissant(historique, fenetre=4) == pytest.approx(0.25)


def test_taux_glissant_fenetre_invalide():
    with pytest.raises(ValueError):
        calculer_taux_glissant([True], fenetre=0)
    with pytest.raises(ValueError):
        calculer_taux_glissant([True], fenetre=-3)


def test_taux_glissant_bornees():
    assert calculer_taux_glissant([True] * 8) == 1.0
    assert calculer_taux_glissant([False] * 8) == 0.0
