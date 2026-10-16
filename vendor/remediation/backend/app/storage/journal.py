"""Journal des missions hors écran — stockage séparé, personnel (ADR-002 / ADR-004).

Fichier : ``backend/data/journal/journal.json`` (hors dépôt — ``.gitignore``
exclut ``data/``). Périmètre volontairement isolé des données d'entraînement :
le journal contient des éléments de vie privée (ce qui s'est passé, avec qui,
comment cela a été vécu) et ne doit jamais être joint aux données de séance.

Le nombre d'entrées est borné (les plus anciennes sont écartées) : le journal
est un carnet de bord, pas une archive.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

RACINE_PROJET = Path(__file__).resolve().parents[3]
"""Racine du dépôt remediation-cognitive (résolution indépendante du CWD)."""

#: Nombre maximal d'entrées conservées (les plus anciennes sont écartées).
MAX_ENTREES = 500


class StockageJournal:
    """Accès au carnet de bord des missions ; racine injectable (tests)."""

    def __init__(self, racine: Path | None = None) -> None:
        self.racine = (
            Path(racine)
            if racine is not None
            else RACINE_PROJET / "backend" / "data" / "journal"
        )
        self._chemin = self.racine / "journal.json"
        # Sérialise lecture → ajout → écriture (le journal est lu et écrit
        # depuis le même processus, mais l'interface peut envoyer deux notes
        # rapprochées).
        self._verrou = threading.Lock()

    def lire_entrees(self) -> list[dict]:
        """Entrées du journal, dans l'ordre chronologique (liste vide si vierge)."""
        try:
            donnees = json.loads(self._chemin.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        entrees = donnees.get("entrees") if isinstance(donnees, dict) else None
        return entrees if isinstance(entrees, list) else []

    def ajouter(
        self,
        mission_id: str,
        texte: str,
        ressenti: str | None,
        horodatage: datetime,
    ) -> dict:
        """Ajoute une note et la retourne (bornage : les plus anciennes partent)."""
        entree = {
            "id": str(uuid.uuid4()),
            "mission_id": mission_id,
            "texte": texte.strip(),
            "ressenti": (ressenti or "").strip() or None,
            "date": horodatage.isoformat(),
        }
        with self._verrou:
            entrees = self.lire_entrees()
            entrees.append(entree)
            del entrees[:-MAX_ENTREES]
            self._ecrire(entrees)
        return entree

    def _ecrire(self, entrees: list[dict]) -> None:
        """Écriture atomique (temporaire + rename) ; crée le dossier à la volée."""
        self.racine.mkdir(parents=True, exist_ok=True)
        temporaire = self._chemin.with_suffix(".json.tmp")
        temporaire.write_text(
            json.dumps({"entrees": entrees}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        os.replace(temporaire, self._chemin)
