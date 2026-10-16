"""Parcours réel : les correcteurs et la persistance viennent de l'amont."""

import json
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mobile.application_runtime import ApplicationRuntime  # noqa: E402


def call(runtime, action, **kwargs):
    return json.loads(runtime.call(json.dumps(dict(action=action, **kwargs))))


def test_calculation_session_corrects_saves_and_reloads(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start")
    assert session["items"]
    assert all("reponse" not in item for item in session["items"])
    # Le test consulte la banque pour fournir les réponses ; jamais l'interface.
    answers = {item["id"]: item["reponse"]["valeur"]
               for item in runtime.manager.contenu.items("calcul-mental")}
    for item in session["items"]:
        result = call(runtime, "answer", session_id=session["session_id"],
                      item_id=item["id"], answer=str(answers[item["id"]]), elapsed_ms=1500)
        assert result["correcte"] is True
        call(runtime, "next")
    summary = call(runtime, "finish", session_id=session["session_id"])
    assert summary["resume"]["correctes"] == len(session["items"])
    assert call(runtime, "finish", session_id=session["session_id"]) == summary
    progress = call(runtime, "progress")
    assert progress["historique"]
    assert call(ApplicationRuntime(str(tmp_path)), "progress") == progress
    assert runtime.manager.stockage.lire_cartes("calcul-mental")


def test_wrong_answer_preserves_upstream_first_response(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start")
    item = session["items"][0]
    response = call(runtime, "answer", session_id=session["session_id"],
                    item_id=item["id"], answer="réponse inconnue", elapsed_ms=1800)
    assert response["correcte"] is False
    assert response["attendue"] is not None
    second = call(runtime, "answer", session_id=session["session_id"],
                  item_id=item["id"], answer=str(response["attendue"]), elapsed_ms=2000)
    assert second == response
    summary = call(runtime, "finish", session_id=session["session_id"])
    assert summary["resume"]["correctes"] == 0


def test_interruption_restores_validated_answer_and_no_duplicate_progress(tmp_path):
    first = ApplicationRuntime(str(tmp_path))
    session = call(first, "start")
    item = session["items"][0]
    result = call(first, "answer", session_id=session["session_id"],
                  item_id=item["id"], answer="inconnu", elapsed_ms=1500)
    restored = ApplicationRuntime(str(tmp_path))
    assert call(restored, "view")["feedback"] == result
    assert call(restored, "start")["session_id"] == session["session_id"]
    summary = call(restored, "finish", session_id=session["session_id"])
    progress = call(restored, "progress")
    relaunched = ApplicationRuntime(str(tmp_path))
    assert call(relaunched, "finish", session_id=session["session_id"]) == summary
    assert call(relaunched, "progress") == progress


def test_failed_checkpoint_rolls_back_fsrs_and_progress(tmp_path, monkeypatch):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start")
    item = session["items"][0]
    call(runtime, "answer", session_id=session["session_id"], item_id=item["id"],
         answer="inconnu", elapsed_ms=1500)
    write = runtime.store._ecrire_json

    def fail_checkpoint(path, value):
        if path == runtime.checkpoint:
            raise OSError("disque indisponible simulé")
        write(path, value)

    monkeypatch.setattr(runtime.store, "_ecrire_json", fail_checkpoint)
    with pytest.raises(OSError):
        call(runtime, "finish", session_id=session["session_id"])
    assert runtime.store.lire_cartes("calcul-mental") == {}
    assert runtime.store.lire_maitrise("calcul-mental")["historique"] == []
    monkeypatch.setattr(runtime.store, "_ecrire_json", write)
    call(runtime, "finish", session_id=session["session_id"])
    assert len(call(runtime, "progress")["historique"]) == 1


def test_errorless_reprise_preserves_support_and_first_result(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start")
    first = session["items"][0]
    answer = call(runtime, "answer", session_id=session["session_id"],
                  item_id=first["id"], answer="inconnu", elapsed_ms=1500)
    view = call(runtime, "next")
    answers = {i["id"]: i["reponse"]["valeur"] for i in runtime.manager.contenu.items("calcul-mental")}
    while not view["reprise"]:
        call(runtime, "answer", session_id=session["session_id"], item_id=view["item"]["id"],
             answer=str(answers[view["item"]["id"]]), elapsed_ms=1500)
        view = call(runtime, "next")
    runtime = ApplicationRuntime(str(tmp_path))
    view = call(runtime, "view")
    assert view["reprise_attendue"] == answer["attendue"]
    call(runtime, "answer", session_id=session["session_id"], item_id=first["id"],
         answer=str(view["reprise_attendue"]), elapsed_ms=1500)
    result = call(runtime, "finish", session_id=session["session_id"])
    assert result["resume"]["correctes"] == len(session["items"]) - 1


def test_duration_proposal_can_be_dismissed_without_finishing(tmp_path, monkeypatch):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start")
    import backend.app.api.entrainement.service as service
    future = datetime.now(timezone.utc) + timedelta(seconds=601)
    monkeypatch.setattr(service, "_horloge_utc", lambda: future)
    call(runtime, "answer", session_id=session["session_id"],
         item_id=session["items"][0]["id"], answer="inconnu", elapsed_ms=1500)
    assert call(runtime, "view")["arret_propose"] is True
    view = call(runtime, "dismiss-stop-proposal")
    assert view["arret_propose"] is False
    assert view.get("finished") is not True


def test_summary_keeps_upstream_fatigue_proposal(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start")
    for item in session["items"][:3]:
        call(runtime, "answer", session_id=session["session_id"],
             item_id=item["id"], answer="inconnu", elapsed_ms=5000)
        call(runtime, "next")
    call(runtime, "finish", session_id=session["session_id"])
    summary = call(runtime, "view")["summary"]
    assert summary["arret_propose"] is True
    assert summary["motif_arret"] == "fatigue"
