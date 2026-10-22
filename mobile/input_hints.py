"""Indications de clavier locales ; aucune valeur attendue transmise à l’écran."""
from numbers import Real
from backend.app.domain.correction.numeric import _en_nombre


def answer_inputmode(item):
    kind = item.get("type")
    if kind in {"empan", "paires-associatives"}:
        return "numeric"
    value = (item.get("reponse") or {}).get("valeur")
    # Ces réponses sont des nombres ou quantités ; les horaires, dates, mots
    # et sorties de code textuelles conservent leur clavier complet.
    if kind not in {"production", "prediction-sortie", "estimation-temps", "prise-message", "n-back"}:
        return "text"
    number = _en_nombre(value)
    if number is None or number < 0:
        # Le clavier decimal iOS ne fournit pas de signe moins.
        return "text"
    if isinstance(value, Real) and not isinstance(value, bool):
        return "decimal"
    return "numeric" if str(value).strip().isdigit() or kind in {"prise-message", "n-back"} else "decimal"
