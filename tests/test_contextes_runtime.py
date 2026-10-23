"""Parité des deux passes et des interruptions, avec données d'essai uniquement."""
import json
from datetime import datetime, timezone

import pytest
from mobile.application_runtime import ApplicationRuntime
from backend.app.api.entrainement.service import GestionnaireSessions
from backend.app.storage.store import StockageJSON

KEY = "evocation--memoire-source"


def call(runtime, action, **kwargs):
    return json.loads(runtime.call(json.dumps({"action": action, **kwargs})))


def step(runtime, operation, value=None, elapsed=100):
    view = call(runtime, "view")
    return call(runtime, "contextes-step", session_id=view["session_id"], item_id=view["item"]["id"],
                revision=view["contextes"]["revision"], operation=operation, value=value, elapsed_ms=elapsed)


def expose(runtime):
    step(runtime, "show")
    step(runtime, "loaded")
    return step(runtime, "hide", elapsed=12000)


def test_two_passes_match_source_and_only_recall_changes_progress(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc)
    from engine.session.runner import SessionRunner
    monkeypatch.setattr(SessionRunner, "_secondes_ecoulees", lambda self: 0)
    original = GestionnaireSessions.__init__
    def fixed(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.horloge = lambda: now
    monkeypatch.setattr(GestionnaireSessions, "__init__", fixed)
    runtime = ApplicationRuntime(str(tmp_path / "mobile"))
    source = GestionnaireSessions(stockage=StockageJSON(tmp_path / "source"))
    session = call(runtime, "start", activity="memoire-source")
    reference = source.demarrer("evocation", parcours="memoire-source")
    assert [i["id"] for i in session["items"]] == [i["id"] for i in reference["items"]]
    assert "images/" not in json.dumps(session)
    for passe in ("decouverte", "rappel"):
        for index, item in enumerate(reference["items"]):
            view = call(runtime, "view")
            assert view["contextes"]["pass"] == passe
            assert "image" not in view["contextes"]
            if passe == "decouverte":
                expose(runtime)
            answer = item["contenu"]["options"][index % len(item["contenu"]["options"])]
            view = step(runtime, "answer", answer, elapsed=1500)
            expected = source.repondre("evocation", reference["session_id"], item["id"], answer, 1500,
                memorisation=passe == "decouverte", observation_contextes={"passe": passe, "ordre": index+1})
            assert view["feedback"] == expected
            step(runtime, "next")
        if passe == "decouverte":
            assert not runtime.store.lire_cartes(KEY)
            assert not runtime.store.lire_temps_reference(KEY)
            assert not runtime.store.lire_maitrise(KEY).get("historique")
    summary = call(runtime, "view")["summary"]
    expected = source.terminer("evocation", reference["session_id"])
    assert summary["resume"] == expected["resume"]
    assert runtime.store.lire_maitrise(KEY) == source.stockage.lire_maitrise(KEY)
    assert runtime.store.lire_temps_reference(KEY) == source.stockage.lire_temps_reference(KEY)
    actual = runtime.store.lire_observations(session["session_id"])["contextes"]
    other = source.stockage.lire_observations(reference["session_id"])["contextes"]
    for passe in actual:
        for first, second in zip(actual[passe], other[passe]):
            assert first["premiere_reponse"] == second["premiere_reponse"]
    for key, card in runtime.store.lire_cartes(KEY).items():
        other_card = source.stockage.lire_cartes(KEY)[key]
        assert (card.echeance, card.stabilite, card.difficulte) == (other_card.echeance, other_card.stabilite, other_card.difficulte)
    assert call(runtime, "finish", session_id=session["session_id"]) == summary
    assert not runtime.store.lire_cartes("evocation--acces-lexical")
    # Même jour : si tous les rappels sont réussis, aucune carte ne sera due.
    # Le scénario courant peut garder des échecs ; le cas vide est testé séparément.


def test_exposure_interruption_and_retry_are_durable(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start", activity="memoire-source")
    view = step(runtime, "show")
    assert view["contextes"]["image"]["src"].endswith(".webp")
    step(runtime, "loaded")
    step(runtime, "pause", elapsed=4000)
    restored = ApplicationRuntime(str(tmp_path))
    view = call(restored, "view")
    assert view["contextes"]["paused"]
    assert "image" not in view["contextes"]
    view = step(restored, "resume", elapsed=800000)
    assert view["contextes"]["remaining_ms"] == 8000
    step(restored, "hide", elapsed=8000)
    view = call(restored, "view")
    payload = dict(session_id=view["session_id"], item_id=view["item"]["id"],
                   revision=view["contextes"]["revision"], operation="answer",
                   value=view["contextes"]["options"][0], elapsed_ms=1500)
    first = call(restored, "contextes-step", **payload)
    payload["elapsed_ms"] = 9999
    assert call(restored, "contextes-step", **payload) == first
    observation = restored.store.lire_observations(session["session_id"])["contextes"]["decouverte"][0]
    assert observation["premiere_reponse"]["temps_ms"] == 1500
    summary = call(restored, "finish", session_id=session["session_id"])
    assert summary["resume"]["items"] == 0
    assert not restored.store.lire_cartes(KEY)


def test_recall_never_reveals_photo_before_first_answer(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start", activity="memoire-source")
    for _ in session["items"]:
        expose(runtime)
        view = call(runtime, "view")
        step(runtime, "answer", view["contextes"]["options"][0])
        step(runtime, "next")
    view = call(runtime, "view")
    assert view["contextes"]["pass"] == "rappel"
    assert "image" not in view["contextes"]
    with pytest.raises(ValueError):
        step(runtime, "show")
    restored = ApplicationRuntime(str(tmp_path))
    assert call(restored, "view")["contextes"]["paused"]
    step(restored, "resume")
    assert "image" not in call(restored, "view")["contextes"]
    item = restored._session().items_par_id[view["item"]["id"]]
    wrong = next(o for o in item["contenu"]["options"] if o != item["reponse"]["valeur"])
    view = step(restored, "answer", wrong)
    assert view["contextes"]["image"]
    step(restored, "reveal-loaded")
    facts = restored.store.lire_observations(session["session_id"])["contextes"]["rappel"][0]
    assert facts["photo_apres_erreur"] is True
    assert facts["premiere_reponse"]["reponse"] == wrong
    with pytest.raises(ValueError):
        step(restored, "answer", item["reponse"]["valeur"])


def test_missing_photo_and_transaction_failure_cannot_advance(tmp_path, monkeypatch):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start", activity="memoire-source")
    with pytest.raises(ValueError):
        step(runtime, "answer", "inconnu")
    step(runtime, "show")
    step(runtime, "image-error")
    view = call(runtime, "view")
    assert view["contextes"]["phase"] == "pret"
    assert view["contextes"]["image_failed"]
    expose(runtime)
    original = runtime.store._ecrire_json
    def fail(path, value):
        if path == runtime.checkpoint:
            raise OSError("stockage indisponible")
        return original(path, value)
    monkeypatch.setattr(runtime.store, "_ecrire_json", fail)
    view = runtime._view()
    with pytest.raises(OSError):
        call(runtime, "contextes-step", session_id=view["session_id"], item_id=view["item"]["id"],
             revision=view["contextes"]["revision"], operation="answer",
             value=view["contextes"]["options"][0], elapsed_ms=1500)
    monkeypatch.setattr(runtime.store, "_ecrire_json", original)
    assert call(runtime, "view")["contextes"]["phase"] == "question"
    facts = runtime.store.lire_observations(session["session_id"])["contextes"]["decouverte"][0]
    assert "premiere_reponse" not in facts


def test_empty_due_session_closes_without_indexing_a_missing_item(tmp_path, monkeypatch):
    runtime = ApplicationRuntime(str(tmp_path))
    original = GestionnaireSessions.demarrer
    def empty(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        result["items"] = []
        return result
    monkeypatch.setattr(GestionnaireSessions, "demarrer", empty)
    session = call(runtime, "start", activity="memoire-source")
    assert session["items"] == []
    assert call(runtime, "view")["finished"]
    assert call(ApplicationRuntime(str(tmp_path)), "view")["finished"]
