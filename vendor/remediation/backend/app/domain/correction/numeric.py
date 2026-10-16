from __future__ import annotations
from numbers import Real
from .normalization import (
    _clef_texte,
)

TOLERANCE_NUMERIQUE = 1e-9

_UNITES_MOTS = {
    "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11,
    "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16,
}

_DIZAINES_MOTS = {
    "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50,
    "soixante": 60, "quatrevingt": 80, "quatrevingtdix": 90,
}

def _nombre_en_chiffres(texte) -> float | None:
    """Convertit un nombre écrit en lettres en valeur numérique.

    Gère les unités, les dizaines, les formes irrégulières (« soixante-dix »,
    « quatre-vingt-dix »), « cent » et « mille », avec traits d'union, espaces
    ou « et ». Retourne None si le texte n'est pas un nombre en lettres.
    """
    texte = _clef_texte(texte)
    if not texte:
        return None
    texte = texte.replace("-", " ")
    texte = texte.replace("quatre vingt dix", "quatrevingtdix")
    texte = texte.replace("quatre vingts", "quatrevingt").replace("quatre vingt", "quatrevingt")
    jetons = [j for j in texte.split() if j != "et"]
    if not jetons:
        return None
    total, courant, vu = 0.0, 0.0, False
    for jeton in jetons:
        if jeton in _UNITES_MOTS:
            courant += _UNITES_MOTS[jeton]
        elif jeton in _DIZAINES_MOTS:
            courant += _DIZAINES_MOTS[jeton]
        elif jeton == "cent":
            courant = (courant or 1) * 100
        elif jeton == "mille":
            total += (courant or 1) * 1000
            courant = 0.0
        else:
            return None
        vu = True
    return total + courant if vu else None

def _en_nombre(valeur) -> float | None:
    if isinstance(valeur, bool) or valeur is None:
        return None
    if isinstance(valeur, Real):
        return float(valeur)
    texte = str(valeur).strip()
    if not texte:
        return None
    texte = texte.strip(" .,!?;:")   # la dictée ajoute souvent un point final
    if not texte:
        return None
    try:
        return float(texte.replace(",", "."))
    except ValueError:
        return _nombre_en_chiffres(texte)

def _corriger_numerique(reponse, attendue) -> bool:
    """Compare numériquement : accepte un nombre, une chaîne numérique, ou des lettres.

    La virgule décimale française est tolérée (``"56,5"`` vaut 56.5) et une réponse
    dictée en toutes lettres est comprise (« six » vaut 6, « quarante-deux » vaut 42).
    Tout ce qui n'est pas interprétable numériquement est faux.
    """
    if attendue is None or isinstance(reponse, bool):
        return False
    valeur = _en_nombre(reponse)
    if valeur is None:
        return False
    cible = _en_nombre(attendue)
    if cible is None:
        return False
    return abs(valeur - cible) <= TOLERANCE_NUMERIQUE

def _corriger_estimation(item: dict, reponse) -> bool:
    """Estimation de durée : acceptée dans la fourchette déclarée par l'item.

    Une estimation n'est pas une mesure exacte : la réponse est correcte si elle
    tombe dans ``reponse.intervalle`` (bornes incluses).
    """
    reponse_item = item.get("reponse") or {}
    intervalle = reponse_item.get("intervalle")
    nombre = _en_nombre(reponse)
    if nombre is None:
        return False
    if isinstance(intervalle, list) and len(intervalle) == 2:
        return float(intervalle[0]) <= nombre <= float(intervalle[1])
    return _corriger_numerique(reponse, reponse_item.get("valeur"))
