"""Non-régression des garde-fous, sans exiger les empreintes Apple en CI."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.domain import capacites
from backend.app.domain.contenu import ChargeurContenu
from backend.app.domain.correction import _sens_proche, corriger


ROOT = Path(__file__).resolve().parent


@pytest.mark.parametrize("response", [
    "pas chez la gardienne", "pas, chez la gardienne", "chez la gardienne mais pas chez elle",
    "non : chez la gardienne", "jamais chez la gardienne",
])
def test_containment_never_bypasses_negation(response):
    item = ChargeurContenu().item("quotidien", "qo-1-message-06")
    with patch.object(capacites, "proche", return_value=True):
        assert not corriger("quotidien", item, response)


@pytest.mark.parametrize("response", [
    "Marie appelle Paul pour confirmer le rendez-vous",
    "Marie appelle Paul pour confirmer le rendez-vous !",
])
def test_word_permutation_cannot_prove_same_roles(response):
    with patch.object(capacites, "proche", return_value=True) as approximate:
        assert not _sens_proche(response, ["Paul appelle Marie pour confirmer le rendez-vous"])
        approximate.assert_not_called()


def test_source_corpus_parity():
    corpus = json.loads((ROOT / "fixtures/correction-0ed9207.json").read_text())
    content = ChargeurContenu()
    with patch.object(capacites, "similarite", side_effect=capacites._similarite_lexicale):
        for case in [*corpus["cases"], *corpus["synthetic"]]:
            if "item" in case:
                item = content.item(case["theme"], case["item"])
                assert item["reponse"]["valeur"] == case["expected"]
                actual = corriger(case["theme"], item, case["response"])
            else:
                actual = _sens_proche(case["response"], [case["expected"]])
            assert actual == case["accepted"], case["id"]


def test_all_message_items_ignore_similarity():
    with patch.object(capacites, "proche", side_effect=AssertionError("Aucun score pour un fait")):
        for item in ChargeurContenu().items("quotidien"):
            if item["type"] == "prise-message":
                assert corriger("quotidien", item, item["reponse"]["valeur"])
                assert not corriger("quotidien", item, "autre réponse")
        cave = ChargeurContenu().item("quotidien", "qo-1-message-04")
        assert corriger("quotidien", cave, "la cave")
        assert not corriger("quotidien", cave, "la porte du garage")


def test_explicit_variants_and_legacy_target_guard():
    item = {"id": "nouveau", "type": "prise-message", "reponse": {
        "valeur": "chez la gardienne", "variantes": ["à la loge"]}}
    assert corriger("quotidien", item, "à la loge")
    assert not corriger("quotidien", item, "chez la voisine")
    item = {"id": "qo-1-message-04", "type": "prise-message", "reponse": {"valeur": "le jardin"}}
    assert not corriger("quotidien", item, "la cave")


def test_message_target_can_explicitly_include_negation():
    item = {"type": "prise-message", "reponse": {"valeur": "sans sucre"}}
    assert corriger("quotidien", item, "sans sucre")
    assert not corriger("quotidien", item, "avec sucre")

