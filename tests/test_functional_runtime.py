import copy

import pytest

from mobile.functional_runtime import FunctionalRuntime


ITEM = {
    "id": "actualiser-consigne-v2-1-test", "type": "actualiser-consigne",
    "contenu": {
        "enonce": "Préparer une réunion", "consigne": "Lis les messages successifs.",
        "etat_initial": {"heure": "14 h", "lieu": "Atlas"},
        "etapes": [
            {"titre": "Consigne initiale", "evenement": "initial", "texte": "Horaire : 14 h. Salle : Atlas."},
            {"titre": "Mise à jour", "evenement": "mise_a_jour", "champ": "heure", "nouveau": "15 h",
             "texte": "Horaire : désormais 15 h. Conserve les autres éléments mémorisés."},
        ],
        "champs": [{"id": "heure", "label": "Horaire"}, {"id": "lieu", "label": "Salle"}],
    },
    "reponse": {"valeur": {"heure": "15 h", "lieu": "Atlas"}},
}


class Manager:
    def __init__(self):
        self.calls = []

    def repondre(self, theme, session_id, item_id, answer, elapsed):
        self.calls.append((theme, session_id, item_id, copy.deepcopy(answer), elapsed))
        return {"correcte": answer == ITEM["reponse"]["valeur"], "attendue": ITEM["reponse"]["valeur"],
                "feedback": "Réponse enregistrée"}


class Runtime(FunctionalRuntime):
    def __init__(self):
        self.ui = {"activity": "actualiser-consigne", "session": {"session_id": "s-1", "items": [{"id": ITEM["id"]}]},
                   "queue": [ITEM["id"]], "cursor": 0, "feedback": None}
        self.manager = Manager()
        self.item = ITEM

    def _session(self):
        return type("Session", (), {"theme": "actualiser-consigne", "session_id": "s-1",
                                     "items_par_id": {ITEM["id"]: ITEM}})()

    def _view(self):
        feedback = self.ui["feedback"]
        return {"session_id": "s-1", "item": self._functional_stub(ITEM), "feedback": feedback,
                "functional": self._functional_view(ITEM)}

    def _record_feedback(self, item_id, result):
        self.ui["last_item"] = item_id
        self.ui["feedback"] = result


def command(runtime, operation, revision=None, elapsed=1200, **extra):
    if revision is None:
        revision = runtime._functional_state()["revision"]
    return runtime._functional_step({"session_id": "s-1", "item_id": ITEM["id"], "revision": revision,
                                     "operation": operation, "elapsed_ms": elapsed, **extra})


def test_actualiser_delivers_only_current_message_and_stubs_answer():
    runtime = Runtime()
    view = runtime._view()
    assert view["item"]["contenu"] == {"enonce": "Préparer une réunion"}
    assert view["functional"]["etape"]["texte"] == ITEM["contenu"]["etapes"][0]["texte"]
    assert "nouveau" not in view["functional"]["etape"]
    assert "réponse" not in str(view)

    command(runtime, "next")
    view = runtime._view()
    assert view["functional"]["etape"]["texte"] == ITEM["contenu"]["etapes"][1]["texte"]
    assert "champs" not in str(view)
    command(runtime, "next")
    assert runtime._view()["functional"]["phase"] == "form"


@pytest.mark.parametrize("answer", [None, {}, {"heure": "15 h"}, {"heure": "15 h", "lieu": "Atlas", "x": "x"},
                                    {"heure": "15 h", "lieu": "  "}, {"heure": "15 h", "lieu": 3}])
def test_actualiser_requires_all_nonempty_fields(answer):
    runtime = Runtime()
    command(runtime, "next")
    command(runtime, "next")
    with pytest.raises(ValueError, match="Complète"):
        command(runtime, "submit", answer=answer)
    assert runtime.manager.calls == []


def test_actualiser_submits_complete_answer_with_accumulated_time_and_retry_is_idempotent():
    runtime = Runtime()
    command(runtime, "next", elapsed=2000)
    command(runtime, "next", elapsed=3000)
    request = {"session_id": "s-1", "item_id": ITEM["id"], "revision": 2, "operation": "submit",
               "elapsed_ms": 4000, "answer": {"heure": "15 h", "lieu": "Atlas"}}
    first = runtime._functional_step(request)
    again = runtime._functional_step(request)
    assert first == again
    assert runtime.manager.calls == [("actualiser-consigne", "s-1", ITEM["id"], request["answer"], 9000)]
    assert runtime.ui["feedback"]["correcte"] is True


def test_pause_resume_versions_state_and_preserves_current_message():
    runtime = Runtime()
    command(runtime, "next")
    runtime._functional_interrupt()
    screen = runtime._view()["functional"]
    assert screen["paused"] is True and screen["index"] == 1
    with pytest.raises(ValueError, match="Reprendre"):
        command(runtime, "next")
    command(runtime, "resume")
    assert runtime._view()["functional"]["paused"] is False
    assert runtime._view()["functional"]["etape"]["titre"] == "Mise à jour"
    with pytest.raises(ValueError, match="périmée"):
        command(runtime, "next", revision=0)


@pytest.mark.parametrize("elapsed", [-1, 86_400_001, True, "2"])
def test_actualiser_rejects_invalid_time(elapsed):
    runtime = Runtime()
    with pytest.raises(ValueError, match="Durée"):
        command(runtime, "next", elapsed=elapsed)
