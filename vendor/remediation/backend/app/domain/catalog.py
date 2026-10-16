"""Identités, parcours et propriétés structurantes des thèmes jouables."""
from pathlib import Path

_BASE_ENTRAINEMENT = Path("content/entrainement")

# Parcours homogènes exposés à l'intérieur d'une même carte. Chaque parcours
# possède son propre état de maîtrise ; ``sources`` remappe les anciens paliers
# composites vers une progression locale 1..N, sans réécrire le contenu livré.
_PARCOURS_PAR_THEME: dict[str, list[dict]] = {
    "memoire": [
        {"id": "chiffres-endroit", "nom": "Chiffres dans l’ordre",
         "description": "Empans de 3 à 6 chiffres ; départ automatique à 5 chiffres",
         "sources": [1, 2, 3, 4], "types": ["empan"], "enonce_contient": "dans l'ordre",
         "palier_depart": 3},
        {"id": "chiffres-envers", "nom": "Chiffres en ordre inverse",
         "description": "Manipuler mentalement 3 à 6 chiffres, sans passer par les empans endroit",
         "sources": [4, 5, 6, 7], "types": ["empan"], "enonce_contient": "à l'envers",
         "palier_depart": 1},
        {"id": "mots", "nom": "Mots — ordre et ordre inverse",
         "description": "Empans de mots concrets ; départ automatique à 4 mots",
         "sources": [9, 10, 11, 12], "types": ["empan-mots"], "palier_depart": 2},
        {"id": "associations", "nom": "Associations mot–nombre",
         "description": "Mémoriser puis retrouver une association ; départ automatique à 3 paires",
         "sources": [3, 6, 8], "types": ["paires-associatives"], "palier_depart": 2},
        {"id": "position", "nom": "Position dans une séquence",
         "description": "Retrouver l’élément situé 2, 3 puis 4 positions avant la fin",
         "sources": [5, 7, 8], "types": ["n-back"]},
    ],
    "rappel-series": [
        {"id": "immediat", "nom": "Rappel immédiat",
         "description": "Une à trois séries ; départ automatique à deux séries de trois mots",
         "sources": [1, 2, 3], "palier_depart": 2},
        {"id": "differe", "nom": "Rappel différé",
         "description": "Toutes les séries après une attente de 20 secondes", "sources": [4],
         "portee": "toutes-series"},
        {"id": "premiere-serie", "nom": "Sélectionner la première série",
         "description": "Après le délai, rappeler seulement la première série", "sources": [4],
         "portee": "premiere-serie"},
    ],
    "series-entendues": [
        {"id": "immediat", "nom": "Rappel immédiat",
         "description": "Une à trois séries entendues ; départ automatique à deux séries",
         "sources": [1, 2, 3], "palier_depart": 2},
        {"id": "differe", "nom": "Rappel différé",
         "description": "Toutes les séries entendues après 20 secondes", "sources": [4],
         "portee": "toutes-series"},
        {"id": "premiere-serie", "nom": "Sélectionner la première série",
         "description": "Après le délai, rappeler seulement la première série entendue", "sources": [4],
         "portee": "premiere-serie"},
    ],
    "methodes": [
        {"id": "pqrst-guide", "nom": "PQRST guidé pas à pas", "sources": [6]},
        {"id": "pqrst-rappel", "nom": "PQRST — répondre de mémoire", "sources": [1]},
        {"id": "choisir-plan", "nom": "Choisir un plan", "sources": [2]},
        {"id": "auto-instruction", "nom": "Se guider avant d’agir", "sources": [3]},
        {"id": "verifier-plan", "nom": "Vérifier un plan", "sources": [4]},
        {"id": "chercher-information", "nom": "Chercher dans un document", "sources": [5]},
    ],
    "garder-cap": [
        {"id": "reprendre", "nom": "Reprendre après une interruption", "sources": [1]},
        {"id": "adapter", "nom": "Adapter un plan", "sources": [2]},
        {"id": "verifier", "nom": "Vérifier avant de terminer", "sources": [3]},
    ],
    "evocation": [
        {"id": "acces-lexical", "nom": "Retrouver le mot",
         "description": "Mots adultes, indices gradués ; réponse orale ou clavier, QCM de soutien au palier 1",
         "sources": list(range(8, 20)), "palier_depart": 2,
         "max_items_paliers": {1: 10, 2: 10, 3: 10, 4: 8, 5: 8, 6: 6, 7: 6, 8: 6, 9: 6, 10: 6, 11: 6, 12: 6},
         "libelles_paliers": {1: "QCM de soutien", 2: "Point de départ · objets familiers · voix ou clavier",
            3: "Mots précis · voix ou clavier", 4: "Notions en contexte · voix ou clavier",
            5: "Verbes utiles · voix ou clavier", 6: "Mots en situation · voix ou clavier",
            7: "Culture générale · voix ou clavier", 8: "Concepts culturels · voix ou clavier",
            9: "Langue soutenue · voix ou clavier", 10: "Verbes de précision · voix ou clavier",
            11: "Interprétation et raisonnement · voix ou clavier", 12: "Nuances soutenues · voix ou clavier"}},
        {"id": "memoire-source", "nom": "Retrouver le contexte",
         "description": "Distinguer l’information de l’endroit où elle a été apprise", "sources": [4],
         "types": ["rappel-source"]},
        {"id": "strategie-semantique", "nom": "Stratégie sémantique (SFA)", "sources": [6]},
        {"id": "strategie-phonologique", "nom": "Stratégie phonologique (PCA)", "sources": [7]},
    ],
}



from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class ThemeSpec:
    id: str
    source_dir: str
    source_pattern: str = "palier-*.json"
    category: str = "entrainement"
    start_level: int = 1
    extra: bool = False
    french: bool = True
    dictation: bool = True
    session_parameters: dict = field(default_factory=dict)


CATALOGUE = {
    'calcul-mental': ThemeSpec('calcul-mental', 'calcul-mental/paliers', start_level=5, session_parameters={'limite_sessions': 6, 'inclure_non_dus': True}),
    'anglais': ThemeSpec('anglais', 'anglais', source_pattern='verbes-irreguliers.json', extra=True, french=False),
    'python': ThemeSpec('python', 'python/commandes', source_pattern='builtins.json', extra=True, french=False, dictation=False),
    'memoire': ThemeSpec('memoire', 'memoire/paliers', category='cible'),
    'rappel-series': ThemeSpec('rappel-series', 'rappel-series/paliers', category='cible', session_parameters={'max_items': 4}),
    'series-entendues': ThemeSpec('series-entendues', 'series-entendues/paliers', category='cible', session_parameters={'max_items': 4}),
    'actualiser-consigne': ThemeSpec('actualiser-consigne', 'actualiser-consigne/paliers', session_parameters={'max_items': 4}),
    'comparer-documents': ThemeSpec('comparer-documents', 'comparer-documents/paliers', session_parameters={'max_items': 4}),
    'reperer-essentiel': ThemeSpec('reperer-essentiel', 'reperer-essentiel/paliers', session_parameters={'max_items': 4}),
    'quotidien': ThemeSpec('quotidien', 'quotidien/paliers'),
    'deduction': ThemeSpec('deduction', 'deduction/paliers', session_parameters={'max_items': 6}),
    'methodes': ThemeSpec('methodes', 'methodes/paliers'),
    'garder-cap': ThemeSpec('garder-cap', 'garder-cap/paliers', session_parameters={'max_items': 4}),
    'evocation': ThemeSpec('evocation', 'evocation/paliers'),
}
THEMES = tuple(CATALOGUE)
_SOURCES_PAR_THEME = {cle: (spec.source_dir, spec.source_pattern) for cle, spec in CATALOGUE.items()}
_CATEGORIE_PAR_THEME = {cle: spec.category for cle, spec in CATALOGUE.items()}
_PALIER_DEPART_PAR_THEME = {cle: spec.start_level for cle, spec in CATALOGUE.items()}
PARAMETRES_THEME = {cle: spec.session_parameters for cle, spec in CATALOGUE.items()}


def proprietes_interface(theme: str) -> dict:
    spec = CATALOGUE[theme]
    return {"extra": spec.extra, "francais": spec.french, "dictee": spec.dictation}
