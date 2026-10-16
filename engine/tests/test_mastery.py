from engine.mastery.criteria import palier_maitrise, palier_maitrise_historique


# -- palier_maitrise (critère historique, 90 % × 3 sessions) ----------------------


def test_pas_assez_de_sessions():
    assert not palier_maitrise([0.95, 0.92])


def test_maitrise_3_sessions():
    assert palier_maitrise([0.95, 0.91, 0.93])


def test_echec_si_une_session_sous_seuil():
    assert not palier_maitrise([0.95, 0.85, 0.95])


def test_seulement_les_dernieres_sessions_comptent():
    # 2 sessions faibles anciennes, 3 dernières au-dessus du seuil
    assert palier_maitrise([0.5, 0.6, 0.95, 0.91, 0.93])


def test_parametres_surchargeables():
    assert palier_maitrise([0.8, 0.85], seuil=0.8, sessions_consecutives=2)
    assert not palier_maitrise([0.8, 0.85], seuil=0.9, sessions_consecutives=3)


# -- palier_maitrise_historique (suivi par palier) ---------------------------------


def test_historique_vide_non_maitrise():
    assert not palier_maitrise_historique([])


def test_maitrise_palier_courant():
    historique = [(1, 0.5), (1, 0.95), (1, 0.92), (1, 0.93)]
    assert palier_maitrise_historique(historique) is True


def test_non_maitrise_si_pas_assez_de_sessions_sur_le_palier():
    historique = [(1, 0.95), (2, 0.95), (2, 0.95)]
    # palier courant 2 : 2 sessions seulement
    assert not palier_maitrise_historique(historique)


def test_changement_de_palier_reinitialise_le_comptage():
    historique = [(1, 0.95), (1, 0.95), (1, 0.95), (2, 0.5), (2, 0.95), (2, 0.95)]
    # palier courant 2 : les 3 sessions à ≥ 0,9 du palier 1 ne comptent pas
    assert not palier_maitrise_historique(historique)
    # en revanche le palier 1 a été maîtrisé à son époque
    assert palier_maitrise_historique(historique, palier=1)


def test_cassure_dans_les_dernieres_sessions():
    historique = [(1, 0.95), (1, 0.85), (1, 0.95), (1, 0.95)]
    assert not palier_maitrise_historique(historique)


def test_palier_explicite_dans_historique_melange():
    historique = [(2, 0.95), (1, 0.95), (1, 0.95), (1, 0.95)]
    assert palier_maitrise_historique(historique, palier=1) is True
    assert palier_maitrise_historique(historique, palier=2) is False
