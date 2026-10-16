# Contrats PQRST importés de remediation-cognitive@44acda5 ; tests DOM exclus.
import copy
import json

import pytest

from backend.app.domain.contenu import ChargeurContenu
from backend.app.domain.correction.sequence import (
    ETAPES_PQRST, corriger_sequence, normaliser_observation_pqrst,
)
from backend.app.domain.messages import PQRST_INTERFACE

ITEM = ChargeurContenu().item("methodes", "mt2-6-pqrst-01")
ETAPES = {e["etape"]: e for e in ITEM["contenu"]["etapes"]}


def payload():
    reponse = {"1": ETAPES[1]["bonne"], "2": "Que retenir ?", "4": ETAPES[4]["modele"],
               "5": [q["bonne"] for q in ETAPES[5]["questions"]]}
    reponse["_pqrst"] = {
        "version": "pqrst-sequence-v1", "etapes_realisees": list(ETAPES_PQRST),
        "phase": "fin", "modele_avant_test": True, "reprise_apres_correction": False,
        "statuts": dict.fromkeys(("1", "2", "4", "5.0", "5.1"), "reponse"),
        "tentatives": {k: [{"reponse": reponse["4"] if k == "4" else reponse["5"][int(k[-1])],
                            "condition": "sans_relecture", "modalite": "clavier" if k == "4" else "choix"}]
                        for k in ("4", "5.0", "5.1")},
        "relectures": [], "interruptions": {},
    }
    return reponse


def test_premiere_reformulation_preservee_apres_aide_correcte():
    r = payload()
    r["4"] = "Le colis."
    m = r["_pqrst"]
    m["tentatives"]["4"][0]["reponse"] = r["4"]
    m["tentatives"]["4"].append({"reponse": ETAPES[4]["modele"], "condition": "apres_relecture", "modalite": "clavier"})
    m["relectures"] = ["4"]
    avant = copy.deepcopy(r)
    correcte, detail = corriger_sequence(ITEM, r)
    assert not correcte
    essais = detail["observation"]["tentatives"]["4"]
    assert essais[0]["correction"]["etat"] == "a_verifier"
    assert essais[1]["correction"]["correcte"] is True
    assert r == avant


def test_absence_declaree_non_notee_question_et_distincte_reformulation():
    r = payload()
    r["2"] = r["4"] = r["5"][0] = None
    for k in ("2", "4", "5.0"):
        r["_pqrst"]["statuts"][k] = "absence_declaree"
        if k != "2":
            r["_pqrst"]["tentatives"][k][0]["reponse"] = None
    _, detail = corriger_sequence(ITEM, r)
    assert detail["2"]["non_notee"]
    for k in ("4", "5.0"):
        assert detail["observation"]["tentatives"][k][0]["correction"]["etat"] == "absence_declaree"


def test_checkpoint_partiel_ne_produit_pas_de_correction():
    r = payload()
    r.pop("4")
    r["5"] = []
    m = r["_pqrst"]
    m.update(etapes_realisees=["P", "Q", "R"], phase="4", modele_avant_test=False,
             statuts={"1": "reponse", "2": "reponse"}, tentatives={})
    observation = normaliser_observation_pqrst(ITEM, r)
    assert observation["statut"] == "partielle"
    assert observation["tentatives"] == {}
    assert observation["question"] == r["2"]
    assert "correcte" not in observation
    with pytest.raises(ValueError):
        corriger_sequence(ITEM, r)


@pytest.mark.parametrize("modifier", [
    lambda r: r["_pqrst"].update(version="inconnue"),
    lambda r: r["_pqrst"].update(modele_avant_test=False),
    lambda r: r["_pqrst"].update(phase=[]),
    lambda r: r["_pqrst"]["statuts"].update({"4": "absence_declaree"}),
    lambda r: r["_pqrst"]["tentatives"]["4"][0].update(reponse="autre première réponse"),
    lambda r: r["_pqrst"]["tentatives"]["4"].append(copy.deepcopy(r["_pqrst"]["tentatives"]["4"][0])),
    lambda r: r["_pqrst"]["relectures"].extend(["4", "4"]),
    lambda r: r["_pqrst"]["interruptions"].update({"4": True}),
    lambda r: r["_pqrst"]["interruptions"].update({"4": 10001}),
    lambda r: r["_pqrst"]["tentatives"]["5.0"][0].update(condition="reprise_interrompue"),
    lambda r: r["_pqrst"]["tentatives"]["5.0"][0].update(modalite="dictée"),
    lambda r: r["5"].append("réponse supplémentaire"),
    lambda r: r.update({"2": "a" * 2001}),
    lambda r: r["_pqrst"].update(secret="champ non prévu"),
])
def test_trace_incoherente_ou_hors_bornes_refusee(modifier):
    r = payload()
    modifier(r)
    with pytest.raises(ValueError):
        normaliser_observation_pqrst(ITEM, r)


def test_payload_historique_ne_devient_pas_protocole_masque():
    r = payload()
    del r["_pqrst"]
    correcte, detail = corriger_sequence(ITEM, r)
    assert correcte
    assert "observation" not in detail

