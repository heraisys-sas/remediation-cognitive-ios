"""Accès au contenu d'entraînement versionné sous content/ (données, pas code).

Le backend lit content/ tel quel : tout item est déjà conforme à
``content/schema-item.json``. Les chemins sont résolus depuis
l'emplacement de ce fichier, indépendamment du CWD.

Le catalogue métier mappe les identifiants de thème de l'API vers
les sources du dépôt ; les libellés visibles (nom/description) viennent
du vocabulaire centralisé (``domain.messages``), pas d'ici.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from . import messages
from .catalog import (
    _BASE_ENTRAINEMENT, _SOURCES_PAR_THEME, _PARCOURS_PAR_THEME,
    _CATEGORIE_PAR_THEME, _PALIER_DEPART_PAR_THEME, proprietes_interface,
)
RACINE_PROJET = Path(__file__).resolve().parents[3]
"""Racine du dépôt remediation-cognitive (résolution indépendante du CWD)."""

#: Fichier des missions d'interaction réelle (hors écran, périmètre « missions »).
_FICHIER_MISSIONS = Path("content/missions/missions.json")

#: Programme d'entraînement (cadrage du rythme et des paliers).
_FICHIER_PROGRAMME = Path("content/programmes/8-semaines.json")


class ChargeurContenu:
    """Charge et met en cache les items d'entraînement par thème.

    Le contenu est versionné et figé pendant l'exécution : une lecture
    unique par thème suffit (cache mémoire de l'instance).
    """

    def __init__(self) -> None:
        self._cache_items: dict[tuple[str, str | None], list[dict]] = {}
        self._cache_missions: list[dict] | None = None
        self._cache_programme: dict | None = None

    # -- programme d'entraînement ---------------------------------------------

    def programme(self) -> dict:
        if self._cache_programme is None:
            chemin = RACINE_PROJET / _FICHIER_PROGRAMME
            try:
                donnees = json.loads(chemin.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                donnees = {}
            self._cache_programme = donnees if isinstance(donnees, dict) else {}
        return self._cache_programme

    # -- missions hors écran --------------------------------------------------

    def missions(self) -> list[dict]:
        """Missions d'interaction réelle (hors écran).

        Hors moteur de séance : une mission n'a pas de réponse attendue —
        l'application fournit la préparation et le suivi, pas une note.
        """
        if self._cache_missions is None:
            chemin = RACINE_PROJET / _FICHIER_MISSIONS
            try:
                donnees = json.loads(chemin.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                donnees = {}
            missions = donnees.get("missions") if isinstance(donnees, dict) else None
            self._cache_missions = missions if isinstance(missions, list) else []
        return self._cache_missions

    # -- thèmes ------------------------------------------------------------

    def themes(self) -> list[dict]:
        """Métadonnées des thèmes exposés par l'API (contrat GET /themes).

        Chaque thème porte sa ``categorie`` : « entrainement » (remédiation) ou
        « cible » (exercices ciblés) — l’interface sépare les deux sections.
        """
        libelles = messages.VOCABULAIRES["entrainement"]["themes"]
        return [
            {
                "id": theme_id,
                "categorie": self.categorie(theme_id),
                "interface": proprietes_interface(theme_id),
                # Paliers disponibles : sert au sélecteur d'essai de l'interface
                # (« Palier : auto » suit la progression ; un palier forcé ne sert
                # que pour les essais, il ne fait jamais reculer la maîtrise).
                "paliers": self.paliers(theme_id),
                "palier_depart": self.palier_depart(theme_id, None),
                "parcours": self.parcours(theme_id),
                **libelles[theme_id],
            }
            for theme_id in _SOURCES_PAR_THEME
            if theme_id in libelles
        ]

    def categorie(self, theme: str) -> str:
        return _CATEGORIE_PAR_THEME.get(theme, "entrainement")

    def theme_existe(self, theme: str) -> bool:
        return theme in _SOURCES_PAR_THEME

    def parcours(self, theme: str) -> list[dict]:
        return [
            {cle: valeur for cle, valeur in definition.items()
             if cle not in {"sources", "types", "types_par_source", "portee", "enonce_contient"}}
            | {"paliers": list(range(1, len(definition["sources"]) + 1))}
            for definition in _PARCOURS_PAR_THEME.get(theme, [])
        ]

    def parcours_existe(self, theme: str, parcours: str | None) -> bool:
        return parcours is None or any(
            definition["id"] == parcours for definition in _PARCOURS_PAR_THEME.get(theme, [])
        )

    def max_items_parcours(self, theme: str, parcours: str | None, palier: int) -> int | None:
        definition = next((p for p in _PARCOURS_PAR_THEME.get(theme, []) if p["id"] == parcours), {})
        return definition.get("max_items_paliers", {}).get(palier)

    def palier_depart(self, theme: str, parcours: str | None) -> int:
        definition = next((p for p in _PARCOURS_PAR_THEME.get(theme, [])
                           if p["id"] == parcours), None)
        if definition is not None:
            return int(definition.get("palier_depart", 1))
        return int(_PALIER_DEPART_PAR_THEME.get(theme, 1))

    # -- items -------------------------------------------------------------

    def items(self, theme: str, parcours: str | None = None) -> list[dict]:
        cle = (theme, parcours)
        if cle not in self._cache_items:
            items = self._charger(theme)
            if parcours is not None:
                definition = next((p for p in _PARCOURS_PAR_THEME.get(theme, [])
                                   if p["id"] == parcours), None)
                if definition is None:
                    return []
                rangs = {source: rang for rang, source in enumerate(definition["sources"], 1)}
                types = set(definition.get("types") or [])
                portee = definition.get("portee")
                enonce_contient = definition.get("enonce_contient")
                filtres = []
                for item in items:
                    if item.get("palier") not in rangs:
                        continue
                    if types and item.get("type") not in types:
                        continue
                    types_source = definition.get("types_par_source", {}).get(item["palier"])
                    if types_source and item.get("type") not in types_source:
                        continue
                    if portee and (item.get("contenu") or {}).get("portee") != portee:
                        continue
                    if enonce_contient and enonce_contient not in str(
                        (item.get("contenu") or {}).get("enonce") or ""
                    ):
                        continue
                    copie = deepcopy(item)
                    copie["palier"] = rangs[item["palier"]]
                    filtres.append(copie)
                items = filtres
            self._cache_items[cle] = items
        return self._cache_items[cle]

    def item(self, theme: str, item_id: str, parcours: str | None = None) -> dict | None:
        for item in self.items(theme, parcours):
            if item["id"] == item_id:
                return item
        return None

    def paliers(self, theme: str, parcours: str | None = None) -> list[int]:
        return sorted({int(item["palier"]) for item in self.items(theme, parcours)})

    # -- interne -----------------------------------------------------------

    def _charger(self, theme: str) -> list[dict]:
        """Lit les fichiers de contenu du thème (ordre de glob trié = stable)."""
        if theme not in _SOURCES_PAR_THEME:
            return []
        sous_dossier, motif = _SOURCES_PAR_THEME[theme]
        dossier = RACINE_PROJET / _BASE_ENTRAINEMENT / sous_dossier
        items: list[dict] = []
        for fichier in sorted(dossier.glob(motif)):
            donnees = json.loads(fichier.read_text(encoding="utf-8"))
            if isinstance(donnees, list):
                items.extend(donnees)
        return items
