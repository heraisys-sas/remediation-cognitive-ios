from __future__ import annotations
import re
from .normalization import (
    _clef_texte,
)

def _mots(texte) -> list[str]:
    return [
        _clef_texte(mot)
        for mot in re.split(r"[^0-9A-Za-z\u00C0-\u024F']+", str(texte or ""))
        if mot.strip()
    ]

def _corriger_mots_ordonnes(reponse, attendue) -> bool:
    """Empan de mots : la SÉQUENCE compte (mots dans l'ordre attendu).

    La tolérance porte sur la saisie (accents, casse, ponctuation), pas sur
    l'ordre : retrouver les mots dans le désordre n'est pas la même tâche.
    """
    return _mots(reponse) == _mots(attendue)

def corriger_rappel_libre(item: dict, reponse) -> tuple[bool, dict]:
    """Corrige un rappel libre et distingue omissions, confusions et intrusions.

    Une confusion est un mot réellement présenté mais hors de la portée demandée
    (par exemple un mot de la deuxième série quand seule la première est ciblée).
    Une intrusion n'a été présentée dans aucune série. Ces erreurs restent créditées
    séparément des mots retrouvés, mais empêchent une maîtrise complète de l'item.
    """
    reponse_item = item.get("reponse") or {}
    cibles = reponse_item.get("valeur") or []
    if not isinstance(cibles, list) or not cibles:
        return False, {"retrouves": [], "omis": [], "confusions_series": [], "intrusions": []}
    seuil = float(reponse_item.get("seuil") or 1.0)
    jetons = set(_mots(reponse))

    def correspond(mot: str, jeton: str) -> bool:
        clef = _clef_texte(mot)
        return jeton == clef or jeton == f"{clef}s"

    trouves = [mot for mot in cibles if any(correspond(mot, jeton) for jeton in jetons)]
    omis = [mot for mot in cibles if mot not in trouves]
    series = (((item.get("contenu") or {}).get("affichage") or {}).get("series") or [])
    presentes = [mot for serie in series if isinstance(serie, list) for mot in serie]
    hors_portee = [mot for mot in presentes if mot not in cibles]
    confusions = [mot for mot in hors_portee if any(correspond(mot, jeton) for jeton in jetons)]
    reconnus = [*cibles, *hors_portee]
    intrusions = sorted(
        jeton for jeton in jetons
        if not any(correspond(mot, jeton) for mot in reconnus)
    )
    proportion = len(trouves) / len(cibles)
    detail = {
        "retrouves": trouves,
        "omis": omis,
        "confusions_series": confusions,
        "intrusions": intrusions,
        "proportion": proportion,
        "seuil": seuil,
    }
    return proportion >= seuil and not confusions and not intrusions, detail

def _corriger_rappel_libre(item: dict, reponse) -> bool:
    return corriger_rappel_libre(item, reponse)[0]
