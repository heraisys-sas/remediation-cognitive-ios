"""Parité de la séquence mobile et absence de progression des traces partielles."""
import copy
import json
from datetime import datetime, timezone

import pytest

from mobile.application_runtime import ApplicationRuntime
from backend.app.api.entrainement.service import GestionnaireSessions
from backend.app.storage.store import StockageJSON


def call(runtime, action, **values):
    return json.loads(runtime.call(json.dumps({"action": action, **values})))


def start(runtime):
    session = call(runtime, "start", activity="pqrst-guide")
    assert session["items"] and "etapes" not in session["items"][0]["contenu"]
    return call(runtime, "view")


def command(view, operation, value=None, elapsed_ms=100):
    return dict(session_id=view["session_id"], item_id=view["item"]["id"], revision=view["protocol"]["revision"],
                operation=operation, value=value, elapsed_ms=elapsed_ms)


def step(runtime, operation, value=None):
    return call(runtime, "pqrst-step", **command(call(runtime, "view"), operation, value))


def to_reformulation(runtime):
    view = start(runtime)
    item = runtime._session().items_par_id[view["item"]["id"]]
    steps = {e["etape"]:e for e in item["contenu"]["etapes"]}
    step(runtime, "continue")
    step(runtime, "respond", steps[1]["bonne"])
    step(runtime, "continue")
    step(runtime, "respond", "Que retenir ?")
    step(runtime, "continue")
    step(runtime, "continue")
    return item, steps


def complete(runtime, steps):
    step(runtime, "respond", steps[4]["modele"])
    step(runtime, "continue")
    for question in steps[5]["questions"]:
        step(runtime, "respond", question["bonne"])
    return step(runtime, "submit")


def test_pqrst_complete_matches_service_and_preserves_first_answer(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc)
    original = GestionnaireSessions.__init__
    def init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.horloge = lambda:now
    monkeypatch.setattr(GestionnaireSessions, "__init__", init)
    runtime = ApplicationRuntime(str(tmp_path / "mobile"))
    item, steps = to_reformulation(runtime)
    first = "Le colis."
    step(runtime, "reread", first)
    assert step(runtime, "continue")["protocol"]["phase"] == "4"
    view = complete(runtime, steps)
    state = runtime.ui["protocols"]["0"]
    answer = copy.deepcopy(state["answer"])
    assert answer["4"] == first
    assert answer["_pqrst"]["tentatives"]["4"][1]["reponse"] == steps[4]["modele"]
    reference = GestionnaireSessions(stockage=StockageJSON(tmp_path / "source"))
    session = reference.demarrer("methodes", parcours="pqrst-guide")
    assert session["items"][0]["id"] == item["id"]
    expected = reference.repondre("methodes", session["session_id"], item["id"], answer, state["elapsed_ms"])
    assert view["feedback"] == expected
    assert view["feedback"]["sequence"]["observation"]["tentatives"]["4"][0]["reponse"] == first
    actual_summary = call(runtime, "finish", session_id=view["session_id"])
    expected_summary = reference.terminer("methodes", session["session_id"])
    assert actual_summary["resume"] == expected_summary["resume"]
    key = "methodes--pqrst-guide"
    assert runtime.store.lire_maitrise(key) == reference.stockage.lire_maitrise(key)
    for key_id, card in runtime.store.lire_cartes(key).items():
        other = reference.stockage.lire_cartes(key)[key_id]
        assert (card.echeance, card.stabilite, card.difficulte) == (other.echeance, other.stabilite, other.difficulte)
    assert runtime.store.lire_temps_reference(key) == []
    assert call(ApplicationRuntime(str(tmp_path / "mobile")), "finish", session_id=view["session_id"]) == actual_summary


def test_partial_restore_pauses_hides_support_and_never_grades(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    item, steps = to_reformulation(runtime)
    before = runtime.store.lire_maitrise("methodes--pqrst-guide")
    call(runtime, "view")
    restored = ApplicationRuntime(str(tmp_path))
    view = call(restored, "view")
    assert view["protocol"]["paused"] is True
    assert item["contenu"]["texte"] not in json.dumps(view, ensure_ascii=False)
    assert restored.store.lire_cartes("methodes--pqrst-guide") == {}
    assert restored.store.lire_maitrise("methodes--pqrst-guide") == before
    assert restored.store.lire_temps_reference("methodes--pqrst-guide") == []
    step(restored, "resume")
    view = complete(restored, steps)
    observation = view["feedback"]["sequence"]["observation"]
    assert observation["interruptions"]["4"] == 1
    assert observation["tentatives"]["4"][0]["condition"] == "reprise_interrompue"


def test_pqrst_replay_stale_commands_and_early_submit(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    view = start(runtime)
    request = command(view, "continue")
    changed = call(runtime, "pqrst-step", **request)
    assert call(runtime, "pqrst-step", **request) == changed
    assert call(runtime, "pqrst-step", **{**request, "elapsed_ms": 900}) == changed
    assert runtime.ui["protocols"]["0"]["elapsed_ms"] == 100
    with pytest.raises(ValueError):
        call(runtime, "pqrst-step", **{**request, "operation":"respond", "value":"inconnu"})
    with pytest.raises(ValueError):
        step(runtime, "submit")
    with pytest.raises(ValueError):
        call(runtime, "answer", session_id=view["session_id"], item_id=view["item"]["id"], answer="inconnu", elapsed_ms=100)
    assert call(runtime, "view") == changed
    summary = call(runtime, "finish", session_id=view["session_id"])
    assert summary["resume"]["items"] == 0
    assert runtime.store.lire_cartes("methodes--pqrst-guide") == {}
    assert runtime.store.lire_observations(view["session_id"])["pqrst"][view["item"]["id"]]["statut"] == "partielle"


def test_pqrst_test_relecture_keeps_first_choices_and_condition(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    _, steps = to_reformulation(runtime)
    step(runtime, "respond", steps[4]["modele"])
    step(runtime, "continue")
    wrong = next(x for x in steps[5]["questions"][0]["options"] if x != steps[5]["questions"][0]["bonne"])
    step(runtime, "reread", wrong)
    step(runtime, "continue")
    step(runtime, "respond", steps[5]["questions"][0]["bonne"])
    step(runtime, "respond", None)
    view = step(runtime, "submit")
    observed = view["feedback"]["sequence"]["observation"]
    assert observed["tentatives"]["5.0"][0]["reponse"] == wrong
    assert observed["tentatives"]["5.0"][1]["condition"] == "apres_relecture"
    assert observed["tentatives"]["5.1"][0]["condition"] == "apres_relecture"
    assert observed["statuts"]["5.1"] == "absence_declaree"


def test_pqrst_checkpoint_failure_rolls_back_transition(tmp_path, monkeypatch):
    runtime = ApplicationRuntime(str(tmp_path))
    view = start(runtime)
    original = runtime._save
    def fail():
        raise OSError("interruption simulée")
    monkeypatch.setattr(runtime, "_save", fail)
    with pytest.raises(OSError):
        step(runtime, "continue")
    monkeypatch.setattr(runtime, "_save", original)
    assert call(runtime, "view") == view
