"""Entrée JSON locale ; conserve le service métier amont, sans serveur HTTP."""

import json
from dataclasses import fields
from datetime import datetime
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/remediation"))

from backend.app.api.entrainement.service import GestionnaireSessions, SessionEnCours, ItemMoteur  # noqa: E402
from engine.session.runner import SessionRunner  # noqa: E402
from mobile.transactional_store import TransactionalStore  # noqa: E402


class ApplicationRuntime:
    """Instance sérialisée par l'appelant natif ; données dans le conteneur de l'app."""

    def __init__(self, storage_directory: str):
        path = Path(storage_directory)
        if not path.is_absolute():
            raise ValueError("Le stockage doit être un chemin absolu du conteneur iOS")
        self.store = TransactionalStore(path)
        self.manager = GestionnaireSessions(stockage=self.store)
        self.checkpoint = path / "native-checkpoint.json"
        self.ui = {}
        self.lock = threading.RLock()
        self.source_version = json.loads((ROOT / "UPSTREAM.json").read_text())["commit"]

    def _restore(self):
        self.manager = GestionnaireSessions(stockage=self.store)
        saved = self.store._lire_json(self.checkpoint)
        self.ui = saved.get("ui", {}) if saved else {}
        if not saved:
            return
        if saved["schema"] != 1 or saved.get("source_version") != self.source_version:
            raise ValueError("Version de sauvegarde incompatible ; données conservées")
        for data in saved["sessions"]:
            values = data["session"]
            available = self.manager.contenu.items(values["theme"], values["parcours"])
            by_id = {item["id"]: item for item in available}
            selected = {key: by_id[key] for key in data["selected"]}
            runner = SessionRunner([ItemMoteur(item) for item in selected.values()],
                                   **data["runner_config"])
            for key, value in data["runner_state"].items():
                setattr(runner, key, datetime.fromisoformat(value) if key == "_depart" else value)
            values["depart"] = datetime.fromisoformat(values["depart"])
            for key in ("protocoles_pqrst", "reprises", "assistees"):
                values[key] = set(values[key])
            session = SessionEnCours(**values, runner=runner, items_par_id=selected,
                                     items_disponibles=available)
            self.manager._sessions[session.session_id] = session

    def _save(self):
        sessions = []
        for session in self.manager._sessions.values():
            values = {}
            for field in fields(session):
                if field.name in ("runner", "items_par_id", "items_disponibles"):
                    continue
                value = getattr(session, field.name)
                values[field.name] = value.isoformat() if isinstance(value, datetime) else sorted(value) if isinstance(value, set) else value
            runner = session.runner
            sessions.append({"session": values, "selected": list(session.items_par_id),
                "runner_config": {key: getattr(runner, key) for key in ("max_items", "duree_max_s", "baseline_rt_ms")},
                "runner_state": {key: getattr(runner, key).isoformat() if key == "_depart" else getattr(runner, key)
                                 for key in ("_index", "_reponses", "_terminee", "_depart")}})
        self.store._ecrire_json(self.checkpoint, {"schema": 1, "source_version": self.source_version,
                                                "sessions": sessions, "ui": self.ui})

    def call(self, request_json: str) -> str:
        request = json.loads(request_json)
        with self.lock, self.store.transaction_theme("pilot"):
            # Reconstruction depuis l'état durable : un échec ne laisse aucun état
            # mémoire en avance sur la transaction annulée.
            self._restore()
            result = self._execute(request)
            self._save()
            return json.dumps(result, ensure_ascii=False, allow_nan=False)

    def _execute(self, request):
        action = request.get("action")
        # Le premier pilote ne propose que le calcul. Pas de dictée/IA implicite.
        if action == "start":
            active = next((s for s in self.manager._sessions.values() if not s.terminee), None)
            if active:
                result = self.ui["session"]
            else:
                self.manager._sessions.clear()
                result = self.manager.demarrer("calcul-mental")
                self.ui = {"session": result, "queue": [i["id"] for i in result["items"]],
                           "cursor": 0, "feedback": None}
        elif action == "view":
            result = self._view()
        elif action == "next":
            if self.ui.get("feedback") is not None:
                self.ui["cursor"] += 1
                self.ui["feedback"] = None
            result = self._view()
        elif action == "answer":
            answer = request.get("answer")
            elapsed = request.get("elapsed_ms")
            if not isinstance(answer, (str, int, float)) or isinstance(answer, bool):
                raise ValueError("Réponse invalide")
            if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not 0 <= elapsed <= 86400000:
                raise ValueError("Durée invalide")
            # Un renvoi du même appel natif après perte de son retour ne crée pas
            # un essai supplémentaire. Le bouton Continuer libère l'item suivant.
            previous = self.ui.get("feedback")
            if previous and self.ui.get("last_item") == request["item_id"]:
                return previous
            current = self._view()
            if (current.get("finished") or not current.get("item") or
                    current["session_id"] != request["session_id"] or
                    current["item"]["id"] != request["item_id"]):
                raise ValueError("Réponse hors de l'étape présentée")
            result = self.manager.repondre(
                "calcul-mental", str(request["session_id"]), str(request["item_id"]),
                answer, elapsed,
            )
            self.ui["last_item"] = request["item_id"]
            self.ui["feedback"] = result
            if result.get("reprise"):
                self.ui["queue"].append(str(request["item_id"]))
        elif action == "finish":
            result = self.manager.terminer("calcul-mental", str(request["session_id"]))
        elif action == "progress":
            result = self.manager.stockage.lire_maitrise("calcul-mental")
        else:
            raise ValueError("Action native non prise en charge")
        return result

    def _view(self):
        if "session" not in self.ui:
            return {"started": False}
        session = self.ui["session"]
        current = self.manager._sessions[session["session_id"]]
        if current.terminee:
            return {"started": True, "finished": True, "summary": current.resume_cloture}
        cursor = self.ui["cursor"]
        queue = self.ui["queue"]
        by_id = {item["id"]: item for item in session["items"]}
        return {"started": True, "session_id": session["session_id"],
                "item": by_id[queue[cursor]] if cursor < len(queue) else None,
                "position": cursor + 1, "total": len(queue),
                "feedback": self.ui["feedback"],
                "reprise": cursor >= len(session["items"])}
