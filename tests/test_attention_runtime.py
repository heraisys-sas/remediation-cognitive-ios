"""Parité de séquencement avec functional.js et corrections amont réelles."""

import json

import pytest

from mobile import application_runtime
from mobile.attention_runtime import ATTENTION_ACTIVITIES, AttentionRuntime


application_runtime.ACTIVITIES.update(ATTENTION_ACTIVITIES)


class Runtime(application_runtime.ApplicationRuntime, AttentionRuntime):
    """ApplicationRuntime réel avec le seul routage d’attention ajouté au test."""

    def _view(self):
        if self.ui.get("activity") in ATTENTION_ACTIVITIES and "session" in self.ui:
            activity = self.ui["activity"]
            return self._attention_view({"activity": activity,
                                         "title": ATTENTION_ACTIVITIES[activity][2]})
        return super()._view()

    def start(self, activity):
        with self.lock, self.store.transaction_theme("pilot"):
            self._restore()
            result = self._execute({"action": "start", "activity": activity})
            self._save()
        return result

    def step(self, request):
        with self.lock, self.store.transaction_theme("pilot"):
            self._restore()
            result = self._attention_step(request)
            self._save()
        return result

    def interrupt(self):
        with self.lock, self.store.transaction_theme("pilot"):
            self._restore()
            self._attention_interrupt()
            self._save()


@pytest.fixture
def runtime(tmp_path):
    return Runtime(str(tmp_path / "sandbox"))


def current_item(runtime):
    return runtime._attention_item()


def command(runtime, operation, value=None, elapsed=1200, revision=None):
    view = runtime._view()
    payload = {"action": "attention-step", "session_id": view["session_id"],
               "item_id": view["item"]["id"],
               "revision": view["attention"]["revision"] if revision is None else revision,
               "operation": operation, "elapsed_ms": elapsed}
    if value is not None:
        payload["value"] = value
    return runtime.step(payload)


def test_reperer_keeps_objective_and_successive_choices_until_final_correction(runtime):
    runtime.start("reperer-essentiel")
    item = current_item(runtime)
    screen = runtime._view()["attention"]
    assert screen["objective"] == item["contenu"]["objectif"]
    assert screen["criterion"] == item["contenu"]["critere"]
    assert screen["message"]["text"] == item["contenu"]["messages"][0]["texte"]
    assert "reponse" not in str(runtime._view())

    for index, message in enumerate(item["contenu"]["messages"]):
        command(runtime, "select", item["reponse"]["valeur"][message["id"]])
        view = runtime._view()
        if index + 1 < len(item["contenu"]["messages"]):
            assert view["attention"]["phase"] == "messages"
            assert view["attention"]["message"]["id"] == item["contenu"]["messages"][index + 1]["id"]
        else:
            assert view["attention"]["phase"] == "submit"
            assert [row["value"] for row in view["attention"]["answers"]] == [
                item["reponse"]["valeur"][entry["id"]] for entry in item["contenu"]["messages"]]

    feedback = command(runtime, "submit")
    assert feedback["feedback"]["correcte"] is True
    assert "detail_fonctionnel" in feedback["feedback"]
    assert runtime._session().reponses[item["id"]] is True


def test_reperer_requires_each_strict_choice_and_does_not_score_a_partial_set(runtime):
    runtime.start("reperer-essentiel")
    item = current_item(runtime)
    with pytest.raises(ValueError, match="oui ou non"):
        command(runtime, "select", True)
    with pytest.raises(ValueError, match="choix"):
        command(runtime, "submit")
    assert item["id"] not in runtime._session().reponses
    command(runtime, "select", "non")
    assert runtime._attention_state()["answers"][item["contenu"]["messages"][0]["id"]] == "non"
    assert item["id"] not in runtime._session().reponses


def test_cap_requires_four_controls_detour_and_resume_without_exposing_hidden_dossier(runtime):
    runtime.start("cap-reprendre")
    item = current_item(runtime)
    content = item["contenu"]
    assert len(content["points"]) == 4

    expected = item["reponse"]["valeur"]
    for index, point in enumerate(content["points"][:content["interruption_apres"]]):
        choice = point["options"][0] if expected["points"][point["id"]] == "valide" else point["options"][1]
        view = command(runtime, "select", choice)
    assert view["attention"]["phase"] == "interruption"
    assert "but" not in str(view["attention"])
    assert content["interruption"]["enonce"] == view["attention"]["prompt"]

    view = command(runtime, "select", content["interruption"]["options"][0])
    assert view["attention"]["phase"] == "resume-choice"
    hidden = json.dumps(view, ensure_ascii=False)
    assert content["but"] not in hidden
    assert all(point["etat"] not in hidden for point in content["points"])
    assert "stimulus" not in hidden and "audio" not in hidden

    view = command(runtime, "select", expected["reprise"])
    assert view["attention"]["phase"] == "control"
    for point in content["points"][content["interruption_apres"]:]:
        choice = point["options"][0] if expected["points"][point["id"]] == "valide" else point["options"][1]
        view = command(runtime, "select", choice)
    assert view["attention"]["phase"] == "submit"
    assert view["attention"]["interruption_answered"] is True
    assert view["attention"]["resume_label"] == next(
        point["label"] for point in content["points"] if point["id"] == expected["reprise"])
    feedback = command(runtime, "submit")
    detail = feedback["feedback"]["detail_fonctionnel"]
    assert feedback["feedback"]["correcte"] is True
    assert detail["interruption_non_notee"] is True
    assert len(detail["lignes"]) == 5


def test_pause_restore_elapsed_bounds_revision_and_idempotent_receipt(runtime):
    runtime.start("reperer-essentiel")
    item = current_item(runtime)
    message = item["contenu"]["messages"][0]
    request = {"action": "attention-step", "session_id": runtime._view()["session_id"],
               "item_id": item["id"], "revision": 0, "operation": "select",
               "value": "oui", "elapsed_ms": 1000}
    first = runtime.step(request)
    assert runtime.step(request) == first
    runtime.interrupt()
    paused = runtime._view()["attention"]
    assert paused["paused"] is True and paused["index"] == 1
    with pytest.raises(ValueError, match="Reprendre"):
        command(runtime, "select", "non")
    command(runtime, "resume")
    assert runtime._view()["attention"]["message"]["id"] == item["contenu"]["messages"][1]["id"]
    with pytest.raises(ValueError, match="périmée"):
        command(runtime, "select", "non", revision=0)
    with pytest.raises(ValueError, match="Durée"):
        command(runtime, "select", "non", elapsed=True)
    assert message["id"] in runtime._attention_state()["answers"]
