"""Contrôles natifs du pilote, sans HTTP ni réseau et sur données temporaires."""

import json
from pathlib import Path
import sys
from contextlib import ExitStack
from tempfile import TemporaryDirectory

from mobile.application_runtime import ApplicationRuntime


def run():
    def call(runtime, action, **values):
        return json.loads(runtime.call(json.dumps({"action": action, **values})))

    passed = 0
    with TemporaryDirectory(prefix="remediation-pilot-") as directory, ExitStack() as resources:
        def restored_runtime():
            instance = ApplicationRuntime(str(Path(directory).resolve()))
            resources.callback(instance.store.connection.close)
            return instance

        runtime = restored_runtime()
        session = call(runtime, "start")
        assert session["items"] and all("reponse" not in i for i in session["items"])
        passed += 1
        answers = {item["id"]: item["reponse"]["valeur"]
                   for item in runtime.manager.contenu.items("calcul-mental")}
        first = session["items"][0]
        feedback = call(runtime, "answer", session_id=session["session_id"],
                        item_id=first["id"], answer="inconnu", elapsed_ms=1500)
        assert feedback["correcte"] is False and feedback["reprise"] is True
        passed += 1
        runtime = restored_runtime()
        assert call(runtime, "view")["feedback"] == feedback
        assert call(runtime, "start")["session_id"] == session["session_id"]
        passed += 1
        view = call(runtime, "next")
        while view.get("item"):
            item = view["item"]
            if view["reprise"]:
                assert view["reprise_attendue"] == answers[item["id"]]
            call(runtime, "answer", session_id=session["session_id"],
                 item_id=item["id"], answer=str(answers[item["id"]]), elapsed_ms=1500)
            view = call(runtime, "next")
        summary = call(runtime, "finish", session_id=session["session_id"])
        assert summary["resume"]["correctes"] == len(session["items"]) - 1
        progress = call(runtime, "progress")
        assert progress["historique"] and runtime.store.lire_cartes("calcul-mental")
        passed += 1
        relaunched = restored_runtime()
        assert call(relaunched, "finish", session_id=session["session_id"]) == summary
        assert call(relaunched, "progress") == progress
        passed += 1
        lexical = call(relaunched, "start", activity="acces-lexical")
        item = lexical["items"][0]
        identity = {"session_id": lexical["session_id"], "item_id": item["id"]}
        call(relaunched, "hint", **identity)
        restored = restored_runtime()
        view = call(restored, "view")
        assert view["activity"] == "acces-lexical" and view["hints_used"] == 1
        passed += 1
        result = call(restored, "reveal", **identity, elapsed_ms=1500)
        assert result["assistee"] is True and result["attendue"] is not None
        summary = call(restored, "finish", session_id=lexical["session_id"])
        assert summary["resume"]["assistees"] == 1 and summary["resume"]["sans_aide"] == 0
        assert restored.store.lire_cartes("evocation--acces-lexical")
        assert call(restored, "progress") == progress
        passed += 1
    return json.dumps({"platform": sys.platform, "passed": passed, "http_server": False})
