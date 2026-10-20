"""Raccord NaturalLanguage natif ; formule, seuil et garde-fous restent ceux de l'amont."""
from backend.app.domain import capacites


def install():
    try:
        import _rc_semantics as native
    except ImportError:
        return
    if not native.available():
        return
    class NativeEmbedding:
        def vectorForString_(self, text):
            return native.vector(text)
    capacites._EMBEDDINGS = NativeEmbedding()
    capacites._FOURNISSEUR = "nle_embedding"
