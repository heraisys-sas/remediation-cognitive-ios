"""Contrat métier amont : la découverte ne remplace jamais le rappel final."""

from mobile.application_runtime import ApplicationRuntime


def test_discovery_has_no_fsrs_or_mastery_effect(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    manager = runtime.manager
    session = manager.demarrer("evocation", parcours="memoire-source")
    key = "evocation--memoire-source"
    item = session["items"][0]
    expected = manager.contenu.item("evocation", item["id"])["reponse"]["valeur"]
    before = (runtime.store.lire_cartes(key), runtime.store.lire_maitrise(key),
              runtime.store.lire_temps_reference(key))
    result = manager.repondre("evocation", session["session_id"], item["id"],
                             expected, 1500, memorisation=True)
    assert result["memorisation"] is True
    manager.terminer("evocation", session["session_id"])
    assert (runtime.store.lire_cartes(key), runtime.store.lire_maitrise(key),
            runtime.store.lire_temps_reference(key)) == before


def test_only_final_recall_changes_progress_once(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    manager = runtime.manager
    session = manager.demarrer("evocation", parcours="memoire-source")
    key = "evocation--memoire-source"
    item = session["items"][0]
    expected = manager.contenu.item("evocation", item["id"])["reponse"]["valeur"]
    manager.repondre("evocation", session["session_id"], item["id"], "introuvable", 1500, memorisation=True)
    manager.repondre("evocation", session["session_id"], item["id"], expected, 1500)
    summary = manager.terminer("evocation", session["session_id"])
    assert summary["resume"]["correctes"] == 1
    assert item["id"] in runtime.store.lire_cartes(key)
    before = runtime.store.lire_maitrise(key)
    assert manager.terminer("evocation", session["session_id"]) == summary
    assert runtime.store.lire_maitrise(key) == before
