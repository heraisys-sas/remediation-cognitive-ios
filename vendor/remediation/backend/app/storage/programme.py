"""État local du programme d'entraînement — périmètre entraînement (non médical).

Un seul élément est conservé : la **date de début** du programme, posée à la
première consultation. Le jour courant en découle ; aucun suivi de performance,
aucune donnée de santé n'est stockée ici.

Fichier : ``backend/data/programme/programme.json`` (hors dépôt — ``.gitignore``
exclut ``data/``).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date
from pathlib import Path

RACINE_PROJET = Path(__file__).resolve().parents[3]
"""Racine du dépôt remediation-cognitive (résolution indépendante du CWD)."""


class StockageProgramme:
    """Date de début du programme ; racine injectable (tests)."""

    def __init__(self, racine: Path | None = None) -> None:
        self.racine = (
            Path(racine)
            if racine is not None
            else RACINE_PROJET / "backend" / "data" / "programme"
        )
        self._chemin = self.racine / "programme.json"
        self._verrou = threading.Lock()

    def lire_date_debut(self) -> date | None:
        """Date de début enregistrée, ou None si le programme n'a jamais été ouvert."""
        try:
            donnees = json.loads(self._chemin.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        valeur = donnees.get("date_debut") if isinstance(donnees, dict) else None
        try:
            return date.fromisoformat(valeur) if valeur else None
        except ValueError:
            return None

    def definir_date_debut(self, quand: date) -> date:
        """Pose la date de début si elle n'existe pas encore (idempotent).

        Relire le programme ne décale donc jamais le calendrier : seule la
        première consultation compte. Retourne la date effectivement retenue.
        """
        with self._verrou:
            existante = self.lire_date_debut()
            if existante is not None:
                return existante
            self.racine.mkdir(parents=True, exist_ok=True)
            temporaire = self._chemin.with_suffix(".json.tmp")
            temporaire.write_text(
                json.dumps({"date_debut": quand.isoformat()}, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            os.replace(temporaire, self._chemin)
            return quand
