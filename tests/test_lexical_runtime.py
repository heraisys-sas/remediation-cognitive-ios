"""Parité du parcours lexical et restauration des aides, sur données synthétiques."""
import json
from datetime import datetime, timezone

import pytest

from mobile.application_runtime import ApplicationRuntime
from backend.app.api.entrainement.service import GestionnaireSessions
from backend.app.storage.store import StockageJSON


def call(runtime, action, **values):
    return json.loads(runtime.call(json.dumps({"action": action, **values})))


def test_lexical_matches_source_feedback_and_progress(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc)
    original = GestionnaireSessions.__init__
    def fixed_clock(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.horloge = lambda: now
    monkeypatch.setattr(GestionnaireSessions, "__init__", fixed_clock)
    mobile = ApplicationRuntime(str(tmp_path / "mobile"))
    source = GestionnaireSessions(stockage=StockageJSON(tmp_path / "source"))
    actual = call(mobile, "start", activity="acces-lexical")
    expected = source.demarrer("evocation", parcours="acces-lexical")
    assert actual["items"] == expected["items"]
    assert len(actual["items"]) == 10
    assert all(i["type"] == "rappel-indice" and "reponse" not in i for i in actual["items"])
    answers = {i["id"]: i["reponse"]["valeur"] for i in source.contenu.items("evocation", "acces-lexical")}
    for number, item in enumerate(actual["items"]):
        identity = {"session_id": actual["session_id"], "item_id": item["id"]}
        count = number % 3  # sans aide, indice, puis affichage du mot
        if count == 1:
            call(mobile, "hint", **identity)
        action = "reveal" if count == 2 else "answer"
        answer = "" if action == "reveal" else str(answers[item["id"]]).upper()
        result = call(mobile, action, **identity, answer=answer, elapsed_ms=1500)
        reference = source.repondre("evocation", expected["session_id"], item["id"], answer, 1500,
                                   indice_utilise=len(item["contenu"]["indices"]) + 1 if count == 2 else count)
        assert result == reference
        call(mobile, "next")
    summary = call(mobile, "finish", session_id=actual["session_id"])
    reference = source.terminer("evocation", expected["session_id"])
    assert summary["resume"] == reference["resume"]
    key = "evocation--acces-lexical"
    assert mobile.store.lire_maitrise(key) == source.stockage.lire_maitrise(key)
    assert mobile.store.lire_temps_reference(key) == source.stockage.lire_temps_reference(key)
    for item_id, card in mobile.store.lire_cartes(key).items():
        other = source.stockage.lire_cartes(key)[item_id]
        assert (card.echeance, card.stabilite, card.difficulte) == (other.echeance, other.stabilite, other.difficulte)
    assert not mobile.store.lire_cartes("calcul-mental")
    assert call(ApplicationRuntime(str(tmp_path / "mobile")), "finish", session_id=actual["session_id"]) == summary


def test_hints_resume_and_reveal_cannot_become_unassisted(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, "start", activity="acces-lexical")
    item = session["items"][0]
    identity = {"session_id":session["session_id"], "item_id":item["id"]}
    for _ in range(5):
        call(runtime, "hint", **identity)
    restored = ApplicationRuntime(str(tmp_path))
    view = call(restored, "view")
    assert view["activity"] == "acces-lexical"
    assert view["hints_used"] == len(item["contenu"]["indices"])
    # Demander un autre parcours reprend la séance courante, sans l'effacer.
    assert call(restored, "start", activity="calcul-mental")["session_id"] == session["session_id"]
    shown = call(restored, "reveal", **identity, elapsed_ms=1500)
    assert shown["assistee"] is True
    assert not shown.get("reprise")
    again = ApplicationRuntime(str(tmp_path))
    assert call(again, "answer", **identity, answer=shown["attendue"], elapsed_ms=1500) == shown
    summary = call(again, "finish", session_id=session["session_id"])
    assert summary["resume"]["assistees"] == 1
    assert summary["resume"]["sans_aide"] == 0
    assert again.store.lire_temps_reference("evocation--acces-lexical") == []
    calculation = call(again, "start", activity="calcul-mental")
    assert calculation["parcours"] is None
    assert call(again, "view")["activity"] == "calcul-mental"


def test_lexical_rejects_stale_hint_and_unsupported_activity(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    with pytest.raises(ValueError):
        call(runtime, "start", activity="parcours-inexistant")
    session = call(runtime, "start", activity="acces-lexical")
    with pytest.raises(ValueError):
        call(runtime, "hint", session_id=session["session_id"], item_id="autre")
    assert call(runtime, "view")["hints_used"] == 0
