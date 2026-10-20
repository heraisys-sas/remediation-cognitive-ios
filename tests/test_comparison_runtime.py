"""Tests du parcours guidé avec le vrai moteur métier."""

import copy
import json
from datetime import datetime, timezone

import pytest

from mobile import application_runtime
from mobile.application_runtime import ApplicationRuntime
from backend.app.api.entrainement.service import GestionnaireSessions
from backend.app.storage.store import StockageJSON
from mobile.comparison_runtime import COMPARISON_ACTIVITIES, ComparisonRuntime


ComparisonTestRuntime = ApplicationRuntime


@pytest.fixture(autouse=True)
def register_activity(monkeypatch):
    monkeypatch.setitem(application_runtime.ACTIVITIES, "comparer-documents",
                        COMPARISON_ACTIVITIES["comparer-documents"])


def call(runtime, action, **kwargs):
    return json.loads(runtime.call(json.dumps({"action": action, **kwargs})))


def view(runtime):
    return call(runtime, "view")


def answer_payload(current, answer, elapsed=1000):
    return {
        "session_id": current["session_id"],
        "item_id": current["item"]["id"],
        "revision": current["comparison"]["revision"],
        "operation": "answer",
        "answer": answer,
        "elapsed_ms": elapsed,
    }


def no_answer_leak(value):
    serialized = json.dumps(value, ensure_ascii=False).lower()
    assert '"reponse"' not in serialized
    assert '"valeur"' not in serialized
    assert '"attendue"' not in serialized


def test_public_start_and_view_show_two_documents_without_solution(tmp_path):
    runtime = ComparisonTestRuntime(str(tmp_path / "mobile"))
    started = call(runtime, "start", activity="comparer-documents")
    no_answer_leak(started)
    assert all(set(item) == {"id", "type", "contenu"} for item in started["items"])
    current = view(runtime)
    no_answer_leak(current)
    original = runtime._session().items_par_id[current["item"]["id"]]
    assert current["comparison"]["documents"] == original["contenu"]["documents"]
    assert current["comparison"]["champs"] == original["contenu"]["champs"]
    assert len(current["comparison"]["documents"]) == 2
    assert current["item"]["contenu"] == {
        key: original["contenu"][key]
        for key in ("enonce", "consigne", "methode") if key in original["contenu"]
    }


def test_answer_uses_source_feedback_and_matches_progress(tmp_path, monkeypatch):
    fixed_now = datetime.now(timezone.utc)
    original_init = GestionnaireSessions.__init__

    def fixed_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.horloge = lambda: fixed_now

    monkeypatch.setattr(GestionnaireSessions, "__init__", fixed_init)
    runtime = ComparisonTestRuntime(str(tmp_path / "mobile"))
    started = call(runtime, "start", activity="comparer-documents")
    source = GestionnaireSessions(stockage=StockageJSON(tmp_path / "source"))
    source_start = source.demarrer("comparer-documents", parcours=None)
    source_session = source._sessions[source_start["session_id"]]
    expected_by_id = {item["id"]: source_session.items_par_id[item["id"]]["reponse"]["valeur"]
                      for item in source_start["items"]}
    assert [item["id"] for item in started["items"]] == [item["id"] for item in source_start["items"]]

    for index, source_item in enumerate(source_start["items"]):
        current = view(runtime)
        expected_answer = expected_by_id[source_item["id"]]
        supplied = expected_answer if index % 2 == 0 else {
            key: ("conforme" if value == "ecart" else "ecart")
            for key, value in expected_answer.items()
        }
        payload = answer_payload(current, supplied, 1250 + index)
        actual = call(runtime, "comparison-step", **payload)
        expected = source.repondre("comparer-documents", source_start["session_id"],
                                   source_item["id"], supplied, payload["elapsed_ms"])
        assert actual["feedback"] == expected
        no_answer_leak(actual["comparison"] or {})
        if index + 1 < len(source_start["items"]):
            call(runtime, "next")

    call(runtime, "finish", session_id=started["session_id"])
    source.terminer("comparer-documents", source_start["session_id"])
    key = "comparer-documents"
    assert runtime.store.lire_maitrise(key) == source.stockage.lire_maitrise(key)
    assert runtime.store.lire_temps_reference(key) == source.stockage.lire_temps_reference(key)
    actual_cards = runtime.store.lire_cartes(key)
    source_cards = source.stockage.lire_cartes(key)
    assert set(actual_cards) == set(source_cards)
    for item_id, card in actual_cards.items():
        source_card = source_cards[item_id]
        assert (card.echeance, card.stabilite, card.difficulte) == (
            source_card.echeance, source_card.stabilite, source_card.difficulte)


@pytest.mark.parametrize("answer", [
    {"jour": "ecart"},
    {"jour": "ecart", "debut": "conforme", "extra": "ecart"},
    {"jour": "oui", "debut": "conforme"},
])
def test_invalid_answers_and_identity_revision_or_elapsed_are_rejected(tmp_path, answer):
    runtime = ComparisonTestRuntime(str(tmp_path))
    started = call(runtime, "start", activity="comparer-documents")
    before = view(runtime)
    payload = answer_payload(before, answer)
    with pytest.raises(ValueError):
        call(runtime, "comparison-step", **payload)
    for changed in (
        {**answer_payload(before, {"jour": "ecart", "debut": "conforme"}), "item_id": "wrong"},
        {**answer_payload(before, {"jour": "ecart", "debut": "conforme"}), "session_id": "wrong"},
        {**answer_payload(before, {"jour": "ecart", "debut": "conforme"}), "revision": True},
        {**answer_payload(before, {"jour": "ecart", "debut": "conforme"}), "revision": 1},
    ):
        with pytest.raises(ValueError):
            call(runtime, "comparison-step", **changed)
    for elapsed in (True, float("nan"), float("inf"), -1, 86400001):
        bad = answer_payload(before, {"jour": "ecart", "debut": "conforme"}, elapsed)
        with pytest.raises(ValueError):
            call(runtime, "comparison-step", **bad)
    assert view(runtime) == before
    assert not runtime._session().essais
    assert not runtime._session().reponses
    assert runtime._session().runner._reponses == []
    assert runtime.ui["session"]["session_id"] == started["session_id"]


def test_duplicate_receipt_ignores_time_and_rejects_alternate_answer(tmp_path):
    runtime = ComparisonTestRuntime(str(tmp_path))
    call(runtime, "start", activity="comparer-documents")
    before = view(runtime)
    answer = runtime._session().items_par_id[before["item"]["id"]]["reponse"]["valeur"]
    payload = answer_payload(before, answer, 1000)
    first = call(runtime, "comparison-step", **payload)
    retry = call(runtime, "comparison-step", **{**payload, "elapsed_ms": 45000})
    assert retry == first
    assert len(runtime._session().runner._reponses) == 1
    assert len(runtime._session().temps_reference) == 1
    alternate = {key: ("ecart" if value == "conforme" else "conforme")
                 for key, value in answer.items()}
    with pytest.raises(ValueError):
        call(runtime, "comparison-step", **{**payload, "answer": alternate})
    assert len(runtime._session().runner._reponses) == 1


def test_pause_restore_resume_excludes_pause_duration_and_next_is_independent(tmp_path):
    runtime = ComparisonTestRuntime(str(tmp_path))
    started = call(runtime, "start", activity="comparer-documents")
    first = view(runtime)
    paused_view = call(runtime, "comparison-step", session_id=first["session_id"],
                       item_id=first["item"]["id"], revision=0, operation="pause", elapsed_ms=700)
    assert paused_view["comparison"]["paused"]
    assert "documents" not in paused_view["comparison"]
    restored = ComparisonTestRuntime(str(tmp_path))
    restored_view = view(restored)
    assert restored_view["comparison"]["paused"]
    resumed = call(restored, "comparison-step", session_id=started["session_id"],
                   item_id=first["item"]["id"], revision=1, operation="resume", elapsed_ms=86400000)
    assert not resumed["comparison"]["paused"]
    answer = restored._session().items_par_id[first["item"]["id"]]["reponse"]["valeur"]
    completed = call(restored, "comparison-step", **answer_payload(resumed, answer, 300))
    assert completed["feedback"]
    assert restored._session().temps_reference == [1000.0]
    next_view = call(restored, "next")
    assert next_view["position"] == first["position"] + 1
    assert next_view["comparison"]["revision"] == 0
    assert not next_view["comparison"]["paused"]
    assert restored.ui["comparison"][str(restored.ui["cursor"])] != restored.ui["comparison"]["0"]


def test_interruption_does_not_create_attempt_and_witness_activity_is_unchanged(tmp_path):
    runtime = ComparisonTestRuntime(str(tmp_path / "compare"))
    call(runtime, "start", activity="comparer-documents")
    before = view(runtime)
    restored = ComparisonTestRuntime(str(tmp_path / "compare"))
    interrupted = view(restored)
    assert interrupted["comparison"]["paused"]
    assert interrupted["comparison"]["revision"] == before["comparison"]["revision"] + 1
    assert not restored._session().runner._reponses
    assert not restored._session().reponses

    witness = ApplicationRuntime(str(tmp_path / "witness"))
    started = call(witness, "start", activity="calcul-mental")
    current = call(witness, "view")
    assert current["item"]
    assert current["activity"] == "calcul-mental"
    assert started["items"][0]["id"] == current["item"]["id"]
