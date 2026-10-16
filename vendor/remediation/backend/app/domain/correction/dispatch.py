from __future__ import annotations
from .deduction import (
    _corriger_grille,
)
from .normalization import (
    _normaliser_texte,
)
from .numeric import (
    _corriger_estimation, _corriger_numerique,
)
from .recall import (
    _corriger_mots_ordonnes, _corriger_rappel_libre,
)
from .text import (
    _clef_reponse, _contient_reponse, _corriger_mot, _corriger_sans_espaces, _est_reponse_libre, _sens_proche,
)

def corriger(theme: str, item: dict, reponse) -> bool:
    if item.get("type") in {"actualiser-consigne", "comparer-documents", "reperer-essentiel",
                             "reprise-interrompue"}:
        from ..attention_fonctionnelle import corriger_detail
        return corriger_detail(item, reponse)[0]
    attendue = (item.get("reponse") or {}).get("valeur")
    if theme == "calcul-mental":
        return _corriger_numerique(reponse, attendue)
    if theme == "deduction":
        return _corriger_grille(item, reponse)
    if theme == "methodes":
        # PQRST, GMT, auto-instruction, plan à vérifier, repérage : proposition choisie.
        if _clef_reponse(reponse) == _clef_reponse(attendue):
            return True
        # Sur un choix multiple, le filet sémantique est écarté : les autres
        # propositions sont des leurres proches par construction.
        if (item.get("contenu") or {}).get("options"):
            return False
        # Réponse libre formulée autrement (formulée en phrase) : le poste sait
        # comparer le sens (« je consulte le docteur » pour « je vais chez le médecin »),
        # et une réponse courte peut être écrite dans une phrase (ADR-008).
        if _est_reponse_libre(attendue):
            return _sens_proche(reponse, [attendue])
        return _contient_reponse(reponse, attendue)
    if theme == "quotidien":
        if item.get("type") == "prise-message":
            if _clef_reponse(reponse) == _clef_reponse(attendue):
                return True
            # Formulation proche (« la cave » pour « la porte de la cave ») — mais
            # jamais à travers un jour, un moment ou un nombre (voir _sens_proche).
            return _sens_proche(reponse, [attendue]) or _contient_reponse(reponse, attendue)
        if item.get("type") == "estimation-temps":
            return _corriger_estimation(item, reponse)
        # etape-suivante et les familles à choix : la proposition choisie, en clair.
        return _clef_reponse(reponse) == _clef_reponse(attendue)
    if theme in ("rappel-series", "series-entendues"):
        return _corriger_rappel_libre(item, reponse)
    if theme == "evocation":
        # Accès lexical : mot retrouvé, avec variantes et petite tolérance de frappe.
        return _corriger_mot(reponse, item)
    if theme in ("anglais", "memoire"):
        if theme == "memoire":
            if item.get("type") == "empan-mots":
                return _corriger_mots_ordonnes(reponse, attendue)
            return _corriger_sans_espaces(reponse, attendue)
        return (
            _normaliser_texte(reponse).lower()
            == _normaliser_texte(attendue).lower()
        )
    # python — production et prediction-sortie : chaîne exacte trimmée
    # (cas sensitive ; la valeur attendue peut être str ou nombre).
    reponse_texte = "" if reponse is None else str(reponse)
    attendue_texte = "" if attendue is None else str(attendue)
    return reponse_texte.strip() == attendue_texte.strip()
