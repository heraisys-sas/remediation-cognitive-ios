import copy

import pytest

from mobile.immediate_runtime import ImmediateRuntime


class Runtime(ImmediateRuntime):
    def __init__(self):
        self.ui = {}


def step(runtime, view, operation, **values):
    return runtime._immediate_step({"session_id": view["session_id"], "item_id": view["item_id"],
                                   "revision": view["immediate"]["revision"], "operation": operation,
                                   "elapsed_ms": 100, **values})


def answer_for(runtime):
    state = runtime.ui["immediate"]
    trial = state["trials"][-1]
    kind, stimulus = state["kind"], trial["stimulus"]
    if kind == "code":
        return "".join(stimulus["chiffres"])
    if kind == "chemin":
        return stimulus["trajet"]
    if kind == "objets":
        return stimulus["modele"]
    changed = stimulus["avant"] != stimulus["apres"]
    return {"decision": "different" if changed else "identique", "localisation": [],
            "localisation_absente": changed}


@pytest.mark.parametrize("kind", ["code", "chemin", "changement", "objets"])
def test_each_path_completes_four_fixed_trials_without_fsrs(kind):
    runtime = Runtime()
    view = runtime._immediate_start({"parcours": kind})
    assert view["activity"] == "memoires-immediates"
    changed = runtime.ui["immediate"]["changed"]
    assert sum(changed) == 2
    assert len(set(changed)) == 2

    for index in range(4):
        if kind == "chemin" and index:
            assert view["immediate"]["phase"] == "exposition"
            assert "instruction" not in view["immediate"]
            assert view["immediate"]["remaining_ms"] == runtime._immediate_exposure(runtime.ui["immediate"])
        else:
            assert view["immediate"]["phase"] == "pret"
            view = step(runtime, view, "show")
        assert view["immediate"]["phase"] == "exposition"
        view = step(runtime, view, "exposure-ended")
        assert view["immediate"]["phase"] == "masque"
        assert "stimulus" not in view["immediate"]
        view = step(runtime, view, "mask-ended")
        response = answer_for(runtime)
        view = step(runtime, view, "answer", response=response, observations={})
        assert view["immediate"]["phase"] == "feedback"
        if index < 3:
            view = step(runtime, view, "continue")
    view = step(runtime, view, "continue")
    assert view["finished"] is True
    assert view["summary"]["blocks"] == 4
    assert not any("fsrs" in key.lower() for key in runtime.ui["immediate"])


def test_auditory_code_exposes_only_one_digit_and_not_in_answer_view():
    runtime = Runtime()
    view = runtime._immediate_start({"parcours": "code", "parametres": {"modalite": "auditive"}})
    view = step(runtime, view, "show")
    assert "audio_digit" in view["immediate"]
    assert "stimulus" not in view["immediate"]
    assert "chiffres" not in str(view)
    digits = [view["immediate"]["audio_digit"]]
    while view["immediate"]["phase"] == "exposition":
        view = step(runtime, view, "audio-next")
        if "audio_digit" in view["immediate"]:
            digits.append(view["immediate"]["audio_digit"])
        assert "chiffres" not in str(view)
    assert len(digits) == runtime.ui["immediate"]["params"]["longueur"]
    assert view["immediate"]["phase"] == "masque"


def test_response_cannot_change_first_answer_and_help_is_a_separate_attempt():
    runtime = Runtime()
    view = runtime._immediate_start({"parcours": "code"})
    for op in ("show", "exposure-ended", "mask-ended"):
        view = step(runtime, view, op)
    trial = runtime.ui["immediate"]["trials"][-1]
    first = "".join(trial["stimulus"]["chiffres"])
    view = step(runtime, view, "answer", response=first, observations={})
    with pytest.raises(ValueError):
        step(runtime, view, "answer", response="0000", observations={})
    view = step(runtime, view, "help")
    assert view["immediate"]["phase"] == "pret"
    view = step(runtime, view, "show")
    view = step(runtime, view, "exposure-ended")
    view = step(runtime, view, "mask-ended")
    view = step(runtime, view, "answer", response=first, observations={}, assisted=True)
    assert trial["first"]["response"] == first
    assert trial["help"]["answer"]["response"] == first


def test_interrupted_help_keeps_first_response_and_reopens_as_separate_attempt():
    runtime = Runtime()
    view = runtime._immediate_start({"parcours": "code"})
    for operation in ("show", "exposure-ended", "mask-ended"):
        view = step(runtime, view, operation)
    trial = runtime.ui["immediate"]["trials"][-1]
    first = "".join(trial["stimulus"]["chiffres"])
    view = step(runtime, view, "answer", response=first, observations={})
    view = step(runtime, view, "help")
    assert len(runtime.ui["immediate"]["trials"]) == 1
    view = runtime._immediate_interrupt(phase="pret", reason="background")
    assert view["immediate"]["phase"] == "feedback"
    assert view["immediate"]["can_help"] is True
    assert view["immediate"]["help_interrupted"] is True
    assert trial["first"]["response"] == first
    assert trial["help"]["answer"] is None
    assert len(runtime.ui["immediate"]["trials"]) == 1


def test_interruption_replaces_trial_and_duplicate_command_is_idempotent():
    runtime = Runtime()
    view = runtime._immediate_start({"parcours": "chemin"})
    request = {"session_id": view["session_id"], "item_id": view["item_id"],
               "revision": view["immediate"]["revision"], "operation": "interrupt",
               "elapsed_ms": 90, "phase": "pret", "observations": {}}
    first = runtime._immediate_step(request)
    duplicate = runtime._immediate_step(copy.deepcopy(request))
    assert first == duplicate
    assert first["item_id"] != request["item_id"]
    assert runtime.ui["immediate"]["trials"][0]["interruption"]["phase"] == "pret"


def test_example_is_separate_and_does_not_add_to_history_or_trial_count():
    runtime = Runtime()
    view = runtime._immediate_start({"parcours": "changement", "parametres": {"condition": "couleur"}})
    first_trial_id = view["item_id"]
    view = step(runtime, view, "example")
    assert view["immediate"]["phase"] == "exemple"
    assert view["immediate"]["example_stage"] == "exposition"
    assert view["item_id"] != first_trial_id
    assert len(runtime.ui["immediate"]["trials"]) == 1
    view = step(runtime, view, "example-end")
    assert view["immediate"]["example_stage"] == "demonstration"
    view = step(runtime, view, "example-close")
    assert view["item_id"] == first_trial_id
    assert view["immediate"]["phase"] == "pret"
    assert len(runtime.ui["immediate"]["trials"]) == 1


def test_finishing_before_any_response_reports_zero_completed_blocks():
    runtime = Runtime()
    view = runtime._immediate_start({"parcours": "objets"})
    view = runtime._immediate_finish({"session_id": view["session_id"]})
    assert view["summary"]["blocks"] == 0
    assert view["summary"]["history"][0]["premiere"] is None


def test_invalid_fields_and_start_during_other_session_are_rejected():
    runtime = Runtime()
    with pytest.raises(ValueError):
        runtime._immediate_start({"parcours": "code", "unexpected": True})
    with pytest.raises(ValueError):
        runtime._immediate_start({"parcours": "unknown"})
    runtime.ui["session"] = {"active": True}
    runtime._session = lambda: type("Session", (), {"terminee": False})()
    with pytest.raises(ValueError):
        runtime._immediate_start({"parcours": "code"})


def test_three_blocks_per_day_limit_counts_opened_blocks():
    runtime = Runtime()
    for _ in range(3):
        view = runtime._immediate_start({"parcours": "code"})
        runtime._immediate_finish({"session_id": view["session_id"]})
    with pytest.raises(ValueError, match="Trois blocs"):
        runtime._immediate_start({"parcours": "code"})


def test_history_and_daily_count_survive_starting_another_block():
    runtime = Runtime()
    first = runtime._immediate_start({"parcours": "code"})
    runtime._immediate_finish({"session_id": first["session_id"]})
    second = runtime._immediate_start({"parcours": "objets"})
    assert runtime.ui["immediate_daily"]["count"] == 2
    assert len(runtime.ui["immediate_history"]) == 1
    assert runtime.ui["immediate_history"][0]["session_id"] == first["session_id"]
    runtime._immediate_finish({"session_id": second["session_id"]})
    assert len(runtime.ui["immediate_history"]) == 2
