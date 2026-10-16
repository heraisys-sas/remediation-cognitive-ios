from __future__ import annotations
import unicodedata

def _normaliser_texte(valeur) -> str:
    if valeur is None:
        return ""
    return " ".join(str(valeur).split())

def _clef_texte(valeur) -> str:
    """Clé de comparaison souple : casse, accents, espaces et guillemets ignorés.

    Sert au thème ``evocation`` (mot retrouvé) : l'objectif est le rappel du mot,
    pas l'orthographe exacte ni la typographie — un mot juste écrit sans accent
    reste juste.
    """
    texte = unicodedata.normalize("NFD", str(valeur or "").casefold())
    sans_accents = "".join(c for c in texte if not unicodedata.combining(c))
    return " ".join(sans_accents.replace("«", " ").replace("»", " ").split())
