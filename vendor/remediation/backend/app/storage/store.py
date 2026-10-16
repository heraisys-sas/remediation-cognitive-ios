"""Persistance JSON de l'entraînement — données non médicales (ADR-002).

Fichiers sous `backend/data/entrainement/<theme>/` (hors dépôt : le
.gitignore du projet exclut `data/`) :
- `cartes-fsrs.json`     : état FSRS par item (`CarteFSRS.to_dict` /
  `from_dict` de engine.srs.fsrs, utilisé tel quel) ;
- `maitrise.json`         : palier courant + historique chronologique
  des couples (palier, taux de réussite) — critère 90 % × 3 séances ;
- `compteur-seances.json` : compteur de séances de la fenêtre courante —
  jour, ou semaine (lundi) pour l'évaluation — remis à zéro au changement
  de fenêtre.

Les répertoires sont créés à la volée à l'accès (fichiers de verrou compris) ; les lectures sur
fichiers absents retournent des valeurs par défaut (thème vierge :
palier 1, aucun historique, aucune carte, 0 séance).

Les séances actives restent en mémoire ; les observations de protocole sont
écrites séparément dès une réponse ou un checkpoint (ADR-040/041).

Concurrence (issues #1, P0-A2) : chaque accès est protégé par deux
verrous imbriqués — un verrou processus (`threading.RLock`, protège les
threads d'un même interpréteur) et un verrou inter-processus sur un
fichier compagnon `<nom>.lock` (fcntl POSIX / msvcrt Windows).
- Les **écritures** sont atomiques (fichier temporaire + `os.replace`) ;
- Les **lectures** prennent elles aussi le verrou inter-processus, afin
  qu'aucune lecture ne s'intercale au milieu d'une écriture ;
- Les cycles **lire-modifier-écrire** doivent passer par une opération
  atomique (`_modifier_json`, `incrementer_compteur`) qui garde le verrou
  pendant toute la séquence — un `lire` puis `ecrire` séparés ne sont PAS
  atomiques et peuvent perdre une mise à jour.

Le verrou fichier n'est jamais imbriqué : toute la logique publique prend
le verrou une seule fois, puis appelle les helpers `*_sans_verrou`.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from engine.srs.fsrs import CarteFSRS


RACINE_PROJET = Path(__file__).resolve().parents[3]
"""Racine du dépôt ; le stockage accepte déjà une racine explicite."""

_MOTIF_THEME = re.compile(r"^[a-z0-9-]+$")

# Verrou processus : protège les opérations read-modify-write (P0-A2).
_verrou = threading.RLock()


@contextmanager
def _verrou_fichier(chemin: Path):
    """Verrou inter-processus sur `chemin` (fcntl POSIX / msvcrt Windows).

    Ne PAS imbriquer : le verrou est pris sur un fichier compagnon
    `<nom>.lock` ; une seconde acquisition dans la même séquence
    bloquerait (fcntl) ou échouerait. Les appelants prennent donc le
    verrou une seule fois, puis utilisent les helpers `*_sans_verrou`.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    avec = chemin.with_suffix(chemin.suffix + ".lock")
    with open(avec, "a+b") as poignee:
        try:
            import fcntl

            fcntl.flock(poignee.fileno(), fcntl.LOCK_EX)
            relacher = lambda: fcntl.flock(poignee.fileno(), fcntl.LOCK_UN)  # noqa: E731
        except ImportError:  # Windows
            import msvcrt

            # Verrouiller un octet existant, toujours au même emplacement.
            if poignee.seek(0, os.SEEK_END) == 0:
                poignee.write(b"\0"); poignee.flush()
            poignee.seek(0)
            msvcrt.locking(poignee.fileno(), msvcrt.LK_LOCK, 1)
            relacher = lambda: msvcrt.locking(poignee.fileno(), msvcrt.LK_UNLCK, 1)  # noqa: E731
        try:
            yield
        finally:
            relacher()


class StockageJSON:
    """Accès fichiers JSON par thème ; racine injectable (tests).

    Périmètre strictement « entraînement » : aucune donnée de bilan ne
    transite ici (séparation ADR-002).
    """

    def __init__(self, racine: Path | None = None) -> None:
        self.racine = (
            Path(racine)
            if racine is not None
            else RACINE_PROJET / "backend" / "data" / "entrainement"
        )

    # -- primitives sans verrou (appelées sous verrou) -------------------

    @contextmanager
    def transaction_theme(self, theme: str):
        """Sérialise une opération de séance complète sur un thème.

        Ce verrou distinct des fichiers de données couvre également les parcours
        du thème. Les méthodes de lecture/écriture restent utilisables à l'intérieur.
        Ne pas imbriquer deux transactions de thème.
        """
        with _verrou:
            with _verrou_fichier(self._dossier_theme(theme) / "transaction"):
                yield

    def _dossier_theme(self, theme: str) -> Path:
        """Dossier du thème, avec garde contre toute injection de chemin."""
        if not _MOTIF_THEME.match(theme or ""):
            raise ValueError(f"theme invalide : {theme!r}")
        return self.racine / theme

    def _lire_json_sans_verrou(self, chemin: Path) -> dict | None:
        """Lit un fichier JSON ; None s'il n'existe pas encore."""
        try:
            return json.loads(chemin.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def _ecrire_json_sans_verrou(self, chemin: Path, contenu: dict) -> None:
        """Écriture atomique (temporaire + rename) ; crée le répertoire."""
        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
        temporaire.write_text(
            json.dumps(contenu, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        os.replace(temporaire, chemin)

    # -- primitives verrouillées -----------------------------------------

    def _lire_json(self, chemin: Path) -> dict | None:
        """Lecture protégée : verrou processus + inter-processus (P0-A2)."""
        with _verrou:
            with _verrou_fichier(chemin):
                return self._lire_json_sans_verrou(chemin)

    def _ecrire_json(self, chemin: Path, contenu: dict) -> None:
        """Écriture atomique protégée : verrou processus + fichier (P0-A2)."""
        with _verrou:
            with _verrou_fichier(chemin):
                self._ecrire_json_sans_verrou(chemin, contenu)

    def _modifier_json(
        self,
        chemin: Path,
        transformation: Callable[[dict], dict],
        defaut: dict,
    ) -> dict:
        """Cycle lire-modifier-écrire **atomique** (P0-A2).

        Le verrou est tenu pendant toute la séquence : aucune écriture
        concurrente ne peut s'intercaler entre la lecture et l'écriture,
        donc aucune mise à jour n'est perdue. Retourne le contenu écrit.
        """
        with _verrou:
            with _verrou_fichier(chemin):
                contenu = self._lire_json_sans_verrou(chemin)
                if contenu is None:
                    contenu = dict(defaut)
                nouveau = transformation(contenu)
                self._ecrire_json_sans_verrou(chemin, nouveau)
                return nouveau

    # -- cartes FSRS -----------------------------------------------------

    def lire_cartes(self, theme: str) -> dict[str, CarteFSRS]:
        """Cartes FSRS persistées du thème (dictionnaire vide si thème vierge)."""
        donnees = self._lire_json(self._dossier_theme(theme) / "cartes-fsrs.json") or {}
        cartes: dict[str, CarteFSRS] = {}
        for item_id, etat in (donnees.get("cartes") or {}).items():
            cartes[item_id] = CarteFSRS.from_dict(etat)
        return cartes

    def ecrire_cartes(self, theme: str, cartes: dict[str, CarteFSRS]) -> None:
        """Persiste le deck complet du thème (sérialisation engine, non modifiée)."""
        contenu = {
            "cartes": {
                item_id: carte.to_dict()
                for item_id, carte in sorted(cartes.items())
            }
        }
        self._ecrire_json(self._dossier_theme(theme) / "cartes-fsrs.json", contenu)

    # -- maîtrise par palier ---------------------------------------------

    def lire_maitrise(self, theme: str) -> dict:
        """État de maîtrise : palier courant + historique [(palier, taux), …]."""
        donnees = self._lire_json(self._dossier_theme(theme) / "maitrise.json") or {}
        palier_courant = int(donnees.get("palier_courant") or 1)
        historique = [
            (int(palier), float(taux))
            for palier, taux in (donnees.get("historique") or [])
        ]
        etat = {"palier_courant": palier_courant, "historique": historique}
        if "historique_etapes" in donnees:
            etat["historique_etapes"] = [(int(p), float(t)) for p, t in donnees["historique_etapes"]]
        return etat

    def maitrise_existe(self, theme: str) -> bool:
        """True si une progression a déjà été persistée pour ce thème/parcours."""
        return (self._dossier_theme(theme) / "maitrise.json").is_file()

    def ecrire_maitrise(
        self,
        theme: str,
        palier_courant: int,
        historique: list[tuple[int, float]],
        historique_etapes: list[tuple[int, float]] | None = None,
    ) -> None:
        """Persiste le palier courant et l'historique chronologique."""
        contenu = {
            "palier_courant": int(palier_courant),
            "historique": [[palier, taux] for palier, taux in historique],
        }
        if historique_etapes is not None:
            contenu["historique_etapes"] = [[p, t] for p, t in historique_etapes]
        self._ecrire_json(self._dossier_theme(theme) / "maitrise.json", contenu)

    # -- compteur de séances (fenêtre courante) --------------------------

    def lire_compteur(self, theme: str, debut: date) -> int:
        """Séances démarrées dans la fenêtre ouverte à `debut` (0 sinon)."""
        donnees = (
            self._lire_json(self._dossier_theme(theme) / "compteur-seances.json")
            or {}
        )
        if donnees.get("date") != debut.isoformat():
            return 0
        return int(donnees.get("nb_sessions") or 0)

    def ecrire_compteur(self, theme: str, debut: date, nb_sessions: int) -> None:
        """Persiste le compteur de la fenêtre (le début stocké pilote la remise à zéro)."""
        contenu = {
            "date": debut.isoformat(),
            "nb_sessions": int(nb_sessions),
        }
        self._ecrire_json(self._dossier_theme(theme) / "compteur-seances.json", contenu)

    def incrementer_compteur(self, theme: str, debut: date, delta: int = 1) -> int:
        """Incrémente le compteur de séances de façon **atomique** (P0-A2).

        Remet à zéro si la fenêtre (`debut`) a changé, puis ajoute `delta`.
        Retourne le nouveau total. Conçu pour être appelé en concurrence
        (threads ou processus) sans perte de mise à jour.
        """
        chemin = self._dossier_theme(theme) / "compteur-seances.json"
        cle = debut.isoformat()

        def _maj(contenu: dict) -> dict:
            if contenu.get("date") != cle:
                contenu = {"date": cle, "nb_sessions": 0}
            contenu["nb_sessions"] = int(contenu.get("nb_sessions") or 0) + int(delta)
            return contenu

        nouveau = self._modifier_json(chemin, _maj, {"date": cle, "nb_sessions": 0})
        return int(nouveau["nb_sessions"])

    # -- baseline RT (temps de référence) --------------------------------

    def lire_temps_reference(self, theme: str) -> list[float]:
        """Derniers temps de réaction corrects (ms), vide si thème vierge."""
        donnees = (
            self._lire_json(self._dossier_theme(theme) / "temps-reference.json")
            or {}
        )
        return [float(t) for t in (donnees.get("temps") or [])]

    def ecrire_temps_reference(self, theme: str, temps: list[float]) -> None:
        """Persiste les ≤ 100 derniers temps corrects (médiane ⇒ baseline RT)."""
        contenu = {"temps": [float(t) for t in temps[-100:]]}
        self._ecrire_json(
            self._dossier_theme(theme) / "temps-reference.json", contenu
        )

    def _chemin_observations(self, session_id: str) -> Path:
        identifiant = str(uuid.UUID(session_id))
        if identifiant != session_id:
            raise ValueError("identifiant de séance invalide")
        return self.racine / "observations" / f"{identifiant}.json"

    def lire_observations(self, session_id: str) -> dict:
        return self._lire_json(self._chemin_observations(session_id)) or {}

    def modifier_observations(self, session_id: str, transformation: Callable[[dict], dict]) -> dict:
        return self._modifier_json(self._chemin_observations(session_id), transformation,
                                   {"session_id": session_id, "contextes": {"decouverte": [], "rappel": []}, "pqrst": {}})
