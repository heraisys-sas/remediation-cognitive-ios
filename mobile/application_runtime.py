"""Entrée JSON locale ; conserve le service métier amont, sans serveur HTTP."""

import json
import copy
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
from mobile.contextes_runtime import ContextesRuntime
from mobile import pqrst_protocol  # noqa: E402

ACTIVITIES = {
    "calcul-mental": ("calcul-mental", None, "Calcul mental"),
    "acces-lexical": ("evocation", "acces-lexical", "Retrouver le mot"),
    "memoire-source": ("evocation", "memoire-source", "Retrouver le contexte"),
    "pqrst-guide": ("methodes", "pqrst-guide", "PQRST guidé"),
}


class ApplicationRuntime(ContextesRuntime):
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
        self.first_call = True

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
            if self.first_call:
                self._mark_restored_interruption()
            result = self._execute(request)
            self._save()
            encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)
        self.first_call = False
        return encoded

    def _execute(self, request):
        action = request.get("action")
        if action == "start":
            activity = request.get("activity", "calcul-mental")
            if activity not in ACTIVITIES:
                raise ValueError("Parcours non disponible")
            active = next((s for s in self.manager._sessions.values() if not s.terminee), None)
            if active:
                result = self.ui["session"]
            else:
                self.manager._sessions.clear()
                theme, parcours, _ = ACTIVITIES[activity]
                result = self.manager.demarrer(theme, parcours=parcours)
                self.ui = {"session": result, "queue": [i["id"] for i in result["items"]],
                           "cursor": 0, "feedback": None, "reprise_support": {},
                           "activity": activity, "hints": {}}
                if activity == "memoire-source":
                    self._contextes_start()
        elif action == "contextes-step":
            return self._contextes_step(request)
        elif action == "view":
            result = self._view()
        elif action == "pqrst-step":
            result = self._pqrst_step(request)
        elif action == "next":
            if self.ui.get("activity") == "memoire-source":
                raise ValueError("Utiliser le parcours Contextes séquencé")
            if self.ui.get("feedback") is not None:
                self.ui["cursor"] += 1
                self.ui["feedback"] = None
            result = self._view()
        elif action == "dismiss-stop-proposal":
            self.ui["stop_proposal"] = False
            result = self._view()
        elif action == "hint":
            current = self._current_item(request)
            item = current["item"]
            if item.get("type") == "pqrst-mise-en-oeuvre":
                raise ValueError("Utiliser le parcours PQRST séquencé")
            hints = item["contenu"].get("indices", [])
            if item.get("type") != "rappel-indice" or not hints or current.get("feedback"):
                raise ValueError("Indice indisponible à cette étape")
            counts = self.ui.setdefault("hints", {})
            counts[item["id"]] = min(len(hints), counts.get(item["id"], 0) + 1)
            result = self._view()
        elif action in ("answer", "reveal"):
            if self.ui.get("activity") == "memoire-source":
                raise ValueError("Utiliser le parcours Contextes séquencé")
            answer = request.get("answer", "")
            elapsed = request.get("elapsed_ms")
            if not isinstance(answer, (str, int, float)) or isinstance(answer, bool):
                raise ValueError("Réponse invalide")
            if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not 0 <= elapsed <= 86400000:
                raise ValueError("Durée invalide")
            # Un renvoi du même appel natif après perte de son retour ne crée pas
            # un essai supplémentaire. Le bouton Continuer libère l'item suivant.
            previous = self.ui.get("feedback")
            if (previous and self.ui.get("last_item") == request.get("item_id")
                    and self.ui["session"]["session_id"] == request.get("session_id")):
                return previous
            current = self._current_item(request)
            item = current["item"]
            hints = item["contenu"].get("indices", [])
            if item.get("type") == "pqrst-mise-en-oeuvre":
                raise ValueError("Utiliser le parcours PQRST séquencé")
            hint_count = self.ui.get("hints", {}).get(item["id"], 0)
            if action == "reveal":
                if item.get("type") != "rappel-indice" or not hints:
                    raise ValueError("Affichage de réponse indisponible")
                hint_count = len(hints) + 1
                answer = ""
            result = self.manager.repondre(
                self._session().theme, str(request["session_id"]), str(request["item_id"]),
                answer, elapsed, indice_utilise=hint_count,
            )
            self._record_feedback(request["item_id"], result)
        elif action == "finish":
            result = self.manager.terminer(self._session().theme, str(request["session_id"]))
        elif action == "progress":
            activity = request.get("activity", "calcul-mental")
            if activity not in ACTIVITIES:
                raise ValueError("Parcours non disponible")
            theme, parcours, _ = ACTIVITIES[activity]
            result = self.manager.stockage.lire_maitrise(f"{theme}--{parcours}" if parcours else theme)
        else:
            raise ValueError("Action native non prise en charge")
        if action == "start" and self.ui.get("activity") == "memoire-source":
            result = {**result, "items": [self._contextes_stub(i) for i in result["items"]]}
        if action == "start" and self.ui.get("activity") == "pqrst-guide":
            result = {**result, "items": [self._protocol_item(i) for i in result["items"]]}
        return result

    def _record_feedback(self, item_id, result):
        self.ui["last_item"] = item_id
        self.ui["feedback"] = result
        if result.get("reprise"):
            self.ui["queue"].append(str(item_id))
            self.ui.setdefault("reprise_support", {})[str(item_id)] = result["attendue"]
        if result.get("arret_propose") and result.get("motif_arret") == "duree":
            self.ui["stop_proposal"] = True

    def _protocol_item(self, item):
        return {"id": item["id"], "type": item["type"], "contenu": {"enonce": "PQRST — un texte, cinq étapes"}}

    def _protocol(self):
        return self.ui.setdefault("protocols", {}).setdefault(
            str(self.ui["cursor"]), pqrst_protocol.create(self.ui["cursor"] >= len(self.ui["session"]["items"])))

    def _mark_restored_interruption(self):
        if "session" not in self.ui or self._session().terminee or self.ui.get("feedback"):
            return
        if self.ui.get("activity") == "memoire-source":
            self._contextes_interrupt()
            return
        protocol = self.ui.get("protocols", {}).get(str(self.ui["cursor"]))
        if protocol and not protocol["paused"] and protocol["phase"] not in ("pret", "fin"):
            pqrst_protocol.pause(protocol)
            protocol["revision"] += 1
            item_id = self.ui["queue"][self.ui["cursor"]]
            self.manager.observer(self._session().theme, self._session().session_id, item_id, protocol["answer"])

    def _pqrst_step(self, request):
        session = self._session()
        cursor = self.ui["cursor"]
        if (request.get("session_id") != session.session_id or cursor >= len(self.ui["queue"])
                or request.get("item_id") != self.ui["queue"][cursor]):
            raise ValueError("Étape PQRST périmée")
        item_id = self.ui["queue"][cursor]
        item = session.items_par_id[item_id]
        if item["type"] != "pqrst-mise-en-oeuvre":
            raise ValueError("Ce parcours n'est pas PQRST")
        protocol = self._protocol()
        # L'identité de l'action exclut l'horloge recalculée par le client après
        # perte du retour ; un renvoi ne doit ni avancer ni ajouter du temps.
        identity = lambda value: {k: v for k, v in value.items() if k != "elapsed_ms"}
        if protocol.get("last_request") and identity(protocol["last_request"]) == identity(request):
            return self._view()
        revision = request.get("revision")
        if (type(revision) is not int or revision != protocol["revision"]
                or session.terminee or self.ui.get("feedback")):
            raise ValueError("Étape PQRST périmée")
        elapsed = request.get("elapsed_ms")
        if type(elapsed) not in (int, float) or not 0 <= elapsed <= 86400000:
            raise ValueError("Durée invalide")
        protocol["elapsed_ms"] += elapsed
        operation = request.get("operation")
        if operation == "submit":
            if protocol["phase"] != "fin" or protocol["paused"]:
                raise ValueError("Terminer toutes les étapes avant la correction")
            result = self.manager.repondre(session.theme, session.session_id, item_id,
                                          protocol["answer"], protocol["elapsed_ms"])
            self._record_feedback(item_id, result)
            protocol["revision"] += 1
        else:
            pqrst_protocol.transition(protocol, operation, request.get("value"))
            self.manager.observer(session.theme, session.session_id, item_id, protocol["answer"])
        protocol["last_request"] = copy.deepcopy(request)
        return self._view()

    def _session(self):
        if "session" not in self.ui:
            raise ValueError("Aucune séance en cours")
        return self.manager._sessions[self.ui["session"]["session_id"]]

    def _current_item(self, request):
        current = self._view()
        if (current.get("finished") or not current.get("item") or
                current.get("session_id") != request.get("session_id") or
                current["item"]["id"] != request.get("item_id")):
            raise ValueError("Réponse hors de l'étape présentée")
        return current

    def _view(self):
        if "session" not in self.ui:
            return {"started": False}
        session = self.ui["session"]
        current = self.manager._sessions[session["session_id"]]
        activity = self.ui.get("activity", "calcul-mental")
        metadata = {"activity": activity, "title": ACTIVITIES[activity][2]}
        if current.terminee:
            return {"started": True, "finished": True, "summary": current.resume_cloture, **metadata}
        if activity == "memoire-source":
            return self._contextes_view(metadata)
        cursor = self.ui["cursor"]
        queue = self.ui["queue"]
        by_id = {item["id"]: item for item in session["items"]}
        item = by_id[queue[cursor]] if cursor < len(queue) else None
        protocol = None
        if item and item["type"] == "pqrst-mise-en-oeuvre":
            if not self.ui["feedback"]:
                protocol = pqrst_protocol.screen(self._protocol(), item)
            item = self._protocol_item(item)
        return {"started": True, "session_id": session["session_id"], **metadata,
                "hints_used": self.ui.get("hints", {}).get(queue[cursor], 0) if cursor < len(queue) else 0,
                "item": item, "protocol": protocol,
                "position": cursor + 1, "total": len(queue),
                "feedback": self.ui["feedback"],
                "arret_propose": self.ui.get("stop_proposal", False),
                "reprise_attendue": self.ui.get("reprise_support", {}).get(queue[cursor])
                    if cursor < len(queue) and cursor >= len(session["items"]) else None,
                "reprise": cursor >= len(session["items"])}
