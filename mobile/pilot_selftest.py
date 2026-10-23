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
        def restored_runtime(storage_directory=None):
            instance = ApplicationRuntime(str(Path(storage_directory or directory).resolve()))
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
        pqrst = call(restored, "start", activity="pqrst-guide")
        item = restored._session().items_par_id[pqrst["items"][0]["id"]]
        steps = {e["etape"]: e for e in item["contenu"]["etapes"]}

        def advance(instance, operation, value=None):
            view = call(instance, "view")
            return call(instance, "pqrst-step", session_id=view["session_id"], item_id=view["item"]["id"],
                        revision=view["protocol"]["revision"], operation=operation, value=value, elapsed_ms=100)

        assert call(restored, "view")["protocol"]["phase"] == "P"
        advance(restored, "respond", steps[1]["bonne"])
        advance(restored, "continue")
        advance(restored, "respond", "Que retenir ?")
        advance(restored, "continue")
        advance(restored, "continue")
        pqrst_restored = restored_runtime()
        view = call(pqrst_restored, "view")
        assert view["protocol"]["paused"] and view["protocol"]["phase"] == "4"
        assert not pqrst_restored.store.lire_cartes("methodes--pqrst-guide")
        assert item["contenu"]["texte"] not in json.dumps(view, ensure_ascii=False)
        passed += 1
        advance(pqrst_restored, "resume")
        advance(pqrst_restored, "reread", "Le colis.")
        advance(pqrst_restored, "continue")
        advance(pqrst_restored, "respond", steps[4]["modele"])
        advance(pqrst_restored, "continue")
        for question in steps[5]["questions"]:
            advance(pqrst_restored, "respond", question["bonne"])
        view = advance(pqrst_restored, "submit")
        attempts = view["feedback"]["sequence"]["observation"]["tentatives"]["4"]
        assert attempts[0]["reponse"] == "Le colis." and not attempts[0]["correction"]["correcte"]
        assert attempts[1]["correction"]["correcte"]
        summary = call(pqrst_restored, "finish", session_id=pqrst["session_id"])
        assert summary["resume"]["correctes"] == 0
        assert pqrst_restored.store.lire_cartes("methodes--pqrst-guide")
        assert pqrst_restored.store.lire_temps_reference("methodes--pqrst-guide") == []
        passed += 1
        contexts = call(pqrst_restored, "start", activity="memoire-source")
        def context_step(instance, operation, value=None):
            view = call(instance, "view")
            return call(instance, "contextes-step", session_id=view["session_id"], item_id=view["item"]["id"],
                        revision=view["contextes"]["revision"], operation=operation, value=value, elapsed_ms=100)
        context_step(pqrst_restored, "show")
        context_step(pqrst_restored, "loaded")
        context_step(pqrst_restored, "pause")
        context_restored = restored_runtime()
        view = call(context_restored, "view")
        assert view["contextes"]["paused"] and "image" not in view["contextes"]
        context_step(context_restored, "resume")
        context_step(context_restored, "hide")
        passed += 1
        for passe in ("decouverte", "rappel"):
            for index in range(len(contexts["items"])):
                if passe == "decouverte" and index > 0:
                    context_step(context_restored, "show")
                    context_step(context_restored, "loaded")
                    context_step(context_restored, "hide")
                view = call(context_restored, "view")
                assert "image" not in view["contextes"]
                item = context_restored._session().items_par_id[view["item"]["id"]]
                context_step(context_restored, "answer", item["reponse"]["valeur"])
                view = context_step(context_restored, "next")
            if passe == "decouverte":
                assert not context_restored.store.lire_cartes("evocation--memoire-source")
        assert view["finished"] and view["summary"]["resume"]["correctes"] == len(contexts["items"])
        assert context_restored.store.lire_cartes("evocation--memoire-source")
        following = call(context_restored, "start", activity="memoire-source")
        assert len(following["items"]) == 10
        assert {item["id"] for item in following["items"]}.isdisjoint(item["id"] for item in contexts["items"])
        call(context_restored, "finish", session_id=following["session_id"])
        passed += 1
        for activity in ("choisir-plan", "auto-instruction", "verifier-plan", "chercher-information"):
            strategy_directory = Path(directory) / activity
            context_restored = restored_runtime(strategy_directory)
            strategy = call(context_restored, "start", activity=activity)
            item = context_restored._session().items_par_id[strategy["items"][0]["id"]]
            correct = item["reponse"]["valeur"]
            wrong = next(option for option in item["contenu"]["options"] if option != correct)
            def choose(instance, value):
                view = call(instance, "view")
                return call(instance, "choice-answer", session_id=view["session_id"], item_id=view["item"]["id"],
                            revision=view["choice_revision"], answer=value, elapsed_ms=100)
            view = choose(context_restored, wrong)
            if activity != "chercher-information":
                assert view["retry_feedback"] and view["feedback"] is None
                context_restored = restored_runtime(strategy_directory)
                view = choose(context_restored, correct)
                assert view["feedback"]["correcte"]
                assert context_restored._session().temps_reference == [200.0]
            else:
                assert view["feedback"] and not view["feedback"]["correcte"]
            call(context_restored, "finish", session_id=strategy["session_id"])
            assert context_restored.store.lire_cartes("methodes--" + activity)
            passed += 1
        for activity in ("chiffres-endroit", "chiffres-envers", "mots", "associations", "position"):
            memory_directory = Path(directory) / ("memory-" + activity)
            memory_runtime = restored_runtime(memory_directory)
            memory_session = call(memory_runtime, "start", activity=activity)
            assert "affichage" not in json.dumps(memory_session)
            def memory_step(instance, operation, answer=None, elapsed=0):
                view = call(instance, "view")
                return call(instance, "memory-step", session_id=view["session_id"], item_id=view["item"]["id"],
                            revision=view["memory"]["revision"], operation=operation, answer=answer, elapsed_ms=elapsed)
            view = memory_step(memory_runtime, "show")
            memory_step(memory_runtime, "pause", elapsed=100)
            memory_runtime = restored_runtime(memory_directory)
            assert call(memory_runtime, "view")["memory"]["paused"]
            view = memory_step(memory_runtime, "resume")
            while view["memory"]["phase"] != "question":
                view = memory_step(memory_runtime, "advance", elapsed=view["memory"]["remaining_ms"])
            assert "content" not in view["memory"] and "affichage" not in json.dumps(view)
            item = memory_runtime._session().items_par_id[view["item"]["id"]]
            view = memory_step(memory_runtime, "answer", str(item["reponse"]["valeur"]), elapsed=1000)
            assert view["feedback"]["correcte"]
            call(memory_runtime, "finish", session_id=memory_session["session_id"])
            assert memory_runtime.store.lire_cartes("memoire--" + activity)
            passed += 1
    # Même corpus source sur ordinateur et dans le Python embarqué iOS.
    from backend.app.domain.contenu import ChargeurContenu
    from backend.app.domain.correction import corriger, _sens_proche
    root = Path(__file__).resolve().parents[1]
    corpus_path = root / "correction-0ed9207.json"
    if not corpus_path.exists():
        corpus_path = root / "tests/fixtures/correction-0ed9207.json"
    corpus = json.loads(corpus_path.read_text())
    content = ChargeurContenu()
    cases = [*corpus["cases"], *corpus["synthetic"]]
    assert len(cases) == 70
    for case in cases:
        if "item" in case:
            item = content.item(case["theme"], case["item"])
            assert item["reponse"]["valeur"] == case["expected"]
            actual = corriger(case["theme"], item, case["response"])
        else:
            actual = _sens_proche(case["response"], [case["expected"]])
        assert actual == case["accepted"], case["id"]
    return json.dumps({"platform": sys.platform, "passed": passed, "http_server": False,
                       "correction_cases": len(cases)})
