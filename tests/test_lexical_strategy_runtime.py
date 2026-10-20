"""Contrat du séquencement SFA/PCA, sans notation des notes intermédiaires."""
from types import SimpleNamespace

import pytest

from mobile.lexical_strategy_runtime import LEXICAL_STRATEGY_ACTIVITIES, LexicalStrategyRuntime


class FakeManager:
    def __init__(self):
        self.calls = []

    def repondre(self, *args):
        self.calls.append(args)
        return {"correcte": args[3] == "marteau", "attendue": "marteau", "feedback": "retour"}


class Runtime(LexicalStrategyRuntime):
    def __init__(self):
        self.item = {"id": "ev-6-analyse-01", "type": "analyse-mot", "contenu": {
            "consigne": "Décris le mot.", "definition": "Sert à enfoncer des clous.",
            "etapes": ["Catégorie ?", "Usage ?", "Lieu ?"], "enonce": "Quel est ce mot ?"}}
        self.ui = {"activity": "strategie-semantique", "cursor": 0,
                   "session": {"session_id": "session-1", "items": [self.item]},
                   "feedback": None, "queue": [self.item["id"]]}
        self.manager = FakeManager()
        self.manager.terminer = lambda *_args: None
        self._lexical_strategy_start()

    def _session(self):
        return SimpleNamespace(session_id="session-1", theme="evocation", terminee=False, items_par_id={self.item["id"]: self.item})

    def _record_feedback(self, item_id, result):
        self.ui["last_item"] = item_id
        self.ui["feedback"] = result

    def _view(self):
        return {"session_id": "session-1", "item": self._lexical_strategy_stub(self.item),
                "lexical_strategy": self._lexical_strategy_view(self.item),
                "feedback": self.ui.get("feedback")}

    def step(self, operation, revision, value="", elapsed_ms=100):
        return self._lexical_strategy_step({"session_id": "session-1", "item_id": self.item["id"],
            "revision": revision, "operation": operation, "value": value, "elapsed_ms": elapsed_ms})


def test_activity_contract_and_stub_hide_answer():
    assert LEXICAL_STRATEGY_ACTIVITIES["strategie-semantique"][:2] == (
        "evocation", "strategie-semantique")
    assert LEXICAL_STRATEGY_ACTIVITIES["strategie-phonologique"][:2] == (
        "evocation", "strategie-phonologique")
    runtime = Runtime()
    assert "reponse" not in runtime._lexical_strategy_stub(runtime.item)
    assert runtime._view()["lexical_strategy"]["definition"] == "Sert à enfoncer des clous."


def test_notes_are_retained_but_only_final_word_reaches_source_service():
    runtime = Runtime()
    for revision, note in enumerate(("un outil", "enfoncer", "atelier")):
        view = runtime.step("note", revision, note)
        assert runtime.manager.calls == []
        assert view["lexical_strategy"]["notes"] == ["un outil", "enfoncer", "atelier"][:revision + 1]
    view = runtime.step("answer", 3, " marteau ", 900)
    assert runtime.manager.calls == [("evocation", "session-1", "ev-6-analyse-01", "marteau", 1200)]
    assert view["feedback"]["attendue"] == "marteau"
    assert runtime.ui["feedback"]["correcte"] is True


def test_pause_resume_is_revisioned_and_preserves_notes():
    runtime = Runtime()
    runtime.step("note", 0, "un outil")
    paused = runtime.step("pause", 1, elapsed_ms=250)
    assert paused["lexical_strategy"]["paused"] is True
    assert paused["lexical_strategy"]["notes"] == ["un outil"]
    with pytest.raises(ValueError, match="Reprendre"):
        runtime.step("note", 2, "enfoncer")
    resumed = runtime.step("resume", 2, elapsed_ms=0)
    assert resumed["lexical_strategy"]["paused"] is False
    assert resumed["lexical_strategy"]["revision"] == 3
    assert resumed["lexical_strategy"]["note_index"] == 1


def test_duplicate_request_is_idempotent_and_stale_or_bad_time_is_rejected():
    runtime = Runtime()
    request = {"session_id": "session-1", "item_id": runtime.item["id"], "revision": 0,
               "operation": "note", "value": "outil", "elapsed_ms": 100}
    runtime._lexical_strategy_step(request)
    repeated = {**request, "elapsed_ms": 999}
    assert runtime._lexical_strategy_step(repeated)["lexical_strategy"]["notes"] == ["outil"]
    assert runtime.ui["lexical_strategy"]["elapsed_ms"] == 100
    with pytest.raises(ValueError, match="périmée"):
        runtime.step("note", 0, "stale")
    with pytest.raises(ValueError, match="Durée"):
        runtime.step("note", 1, "usage", elapsed_ms=-1)
    assert runtime.manager.calls == []


def test_source_retry_keeps_strategy_open_without_revealing_expected_word():
    runtime = Runtime()
    for revision, note in enumerate(("outil", "clous", "atelier")):
        runtime.step("note", revision, note)
    runtime.manager.repondre = lambda *args: (
        runtime.manager.calls.append(args) or {"correcte": False, "attendue": None,
            "essai_supplementaire": True, "feedback": "Essaie encore."})
    view = runtime.step("answer", 3, "tournevis", 600)
    assert view["feedback"] is None
    assert view["lexical_strategy"]["phase"] == "answer"
    assert view["lexical_strategy"]["retry_feedback"] == "Essaie encore."
    assert "attendue" not in view["lexical_strategy"]
    assert runtime.ui.get("feedback") is None
    assert runtime.manager.calls[-1][-1] == 900
