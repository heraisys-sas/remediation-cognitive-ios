"""Le raccord natif conserve la formule et le seuil de l'amont."""
import math
import sys
from types import SimpleNamespace

from mobile import application_runtime  # installe le chemin du moteur embarqué
from mobile import semantic_adapter
from backend.app.domain import capacites


def test_native_vectors_use_original_cosine_and_threshold(monkeypatch):
    monkeypatch.setattr(capacites, "_EMBEDDINGS", None)
    monkeypatch.setattr(capacites, "_FOURNISSEUR", None)
    def vector(text):
        score = {"attendue": 1.0, "acceptee": .78, "refusee": .7798}[text]
        return [score, math.sqrt(1 - score * score)]
    monkeypatch.setitem(sys.modules, "_rc_semantics", SimpleNamespace(available=lambda: True, vector=vector))
    semantic_adapter.install()
    assert capacites.fournisseur_similarite() == "nle_embedding"
    assert capacites.SEUIL_SIMILARITE == .78
    assert capacites.proche("acceptee", ["attendue"])
    assert not capacites.proche("refusee", ["attendue"])


def test_unavailable_native_model_keeps_existing_fallback(monkeypatch):
    monkeypatch.setattr(capacites, "_EMBEDDINGS", False)
    monkeypatch.setattr(capacites, "_FOURNISSEUR", "lexical")
    monkeypatch.setitem(sys.modules, "_rc_semantics", SimpleNamespace(available=lambda: False))
    semantic_adapter.install()
    assert capacites.fournisseur_similarite() == "lexical"
    assert capacites.similarite("même phrase", "même phrase") == 1
