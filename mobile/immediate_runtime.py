"""Runtime autonome des blocs de mémoires immédiates, sans FSRS ni FastAPI."""
import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

_VENDOR = Path(__file__).resolve().parents[1] / "vendor/remediation"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from backend.app.api.memoires_immediates.protocoles import (
    VERSION, correction, observations, parameters, stimulus,
)

IMMEDIATE_NAMES = {
    "code": "Retenir un code", "chemin": "Refaire le chemin",
    "changement": "Qu’est-ce qui a changé ?", "objets": "Quel objet était où ?",
}
PHASES = {"pret", "exposition", "masque", "reponse", "feedback", "termine"}


def _now():
    return datetime.now(timezone.utc).isoformat()


class ImmediateRuntime:
    """Mixin de routage; toute écriture est incluse dans la transaction hôte."""

    def _immediate_active(self):
        state = self.ui.get("immediate")
        return bool(state and not state["finished"])

    def _immediate_start(self, request):
        if set(request) - {"action", "activity", "parcours", "parametres"}:
            raise ValueError("Paramètres de démarrage inconnus")
        if self._immediate_active():
            raise ValueError("Un bloc de mémoire immédiate est déjà actif")
        if self.ui.get("session") and not self._session().terminee:
            raise ValueError("Terminez ou interrompez l’autre séance avant de commencer")
        kind = request.get("parcours")
        if kind not in IMMEDIATE_NAMES:
            raise ValueError("Parcours de mémoire immédiate indisponible")
        params = parameters(kind, request.get("parametres", {}))
        today = datetime.now(timezone.utc).date().isoformat()
        opened = self.ui.setdefault("immediate_daily", {})
        if opened.get("date") != today:
            opened.update(date=today, count=0)
        if opened["count"] >= 3:
            raise ValueError("Trois blocs déjà commencés aujourd’hui")
        session_id = str(uuid4())
        changed = [True, True, False, False]
        # Source cryptographique non requise ici; mélange indépendant au bloc.
        import random
        random.SystemRandom().shuffle(changed)
        state = {"session_id": session_id, "kind": kind, "params": params,
                 "version": VERSION, "changed": changed, "created": _now(),
                 "finished": False, "index": 0, "trials": [], "revision": 0,
                 "last_request": None, "summary": None, "example": None}
        state["trials"].append(self._immediate_new_trial(state, 1))
        opened["count"] += 1
        self.ui["immediate"] = state
        return self._immediate_view()

    def _immediate_new_trial(self, state, index, replaces=None):
        identifier = str(uuid4())
        trial = {"id": identifier, "index": index,
                 "stimulus": stimulus(state["kind"], state["params"], identifier,
                                      state["changed"][index - 1]),
                 "phase": "pret", "first": None, "help": None,
                 "interruption": None, "elapsed_ms": 0, "answer_elapsed_ms": 0,
                 "remaining_ms": 0, "interruptions": 0, "started": None,
                 "audio_index": 0}
        if replaces:
            trial["replaces"] = replaces
        return trial

    def _immediate_current(self):
        state = self.ui.get("immediate")
        if not state or state["finished"]:
            raise ValueError("Aucun bloc de mémoire immédiate actif")
        if state.get("version") != VERSION:
            raise ValueError("Version du protocole de mémoire immédiate incompatible")
        return state, state["trials"][-1]

    def _immediate_interrupt(self, phase=None, reason="interruption"):
        """Masque un écran et lie la reprise au trial qui a été interrompu."""
        if not self._immediate_active():
            return self._immediate_view()
        state, trial = self._immediate_current()
        if state.get("example"):
            state["example"] = None
            state["revision"] += 1
            state["last_request"] = None
            return self._immediate_view()
        if trial["phase"] not in ("pret", "exposition", "masque", "reponse"):
            return self._immediate_view()
        if phase is not None and phase != trial["phase"]:
            raise ValueError("Phase d’interruption incohérente")
        facts = observations({"phase": trial["phase"], "raison": reason})
        interruption = {"phase": trial["phase"], "observations": facts, "date": _now()}
        if trial.get("help") and trial["help"].get("answer") is None:
            trial["help"]["interruption"] = interruption
            trial["phase"] = "feedback"
        else:
            trial["interruption"] = interruption
            trial["interruptions"] += 1
            state["trials"].append(self._immediate_new_trial(state, trial["index"], trial["id"]))
        state["revision"] += 1
        state["last_request"] = None
        return self._immediate_view()

    def _immediate_view(self):
        state = self.ui.get("immediate")
        if not state:
            return {"started": False, "finished": False}
        if state.get("version") != VERSION:
            raise ValueError("Version du protocole de mémoire immédiate incompatible")
        common = {"started": True, "session_id": state["session_id"],
                  "title": IMMEDIATE_NAMES[state["kind"]],
                  "activity": "memoires-immediates", "item_id": state["trials"][-1]["id"] if state["trials"] else None,
                  "item": {"id": state["trials"][-1]["id"], "type": "memoires-immediates",
                           "contenu": {"enonce": IMMEDIATE_NAMES[state["kind"]]}} if state["trials"] else None,
                  "finished": state["finished"], "position": min(state["index"] + 1, 4), "total": 4}
        if state["finished"]:
            return {**common, "item_id": None, "immediate": {"phase": "termine"}, "summary": copy.deepcopy(state["summary"])}
        trial = state["trials"][-1]
        example = state.get("example")
        phase = "exemple" if example and example["phase"] in ("exposition", "demonstration") else trial["phase"]
        interruptions = sum(item["interruptions"] for item in state["trials"] if item["index"] == trial["index"])
        screen = {"phase": phase, "revision": state["revision"],
                  "index": trial["index"], "total": 4, "interruptions": interruptions,
                  "help_interrupted": bool((trial.get("help") or {}).get("interruption")),
                  "assisted": bool(trial["help"]), "example": bool(example),
                  "kind": state["kind"], "params": copy.deepcopy(state["params"]),
                  "modalite": state["params"]["modalite"]}
        if example:
            screen["example_stage"] = example["phase"]
            if example["phase"] == "exposition":
                if state["kind"] == "code" and state["params"]["modalite"] == "auditive":
                    screen["audio_digit"] = example["stimulus"]["chiffres"][example["audio_index"]]
                    screen["audio_index"] = example["audio_index"]
                else:
                    screen["stimulus"] = copy.deepcopy(example["stimulus"])
            else:
                screen["stimulus"] = copy.deepcopy(example["stimulus"])
            return {**common, "item_id": f"example:{state['session_id']}",
                    "item": {"id": f"example:{state['session_id']}", "type": "example",
                             "contenu": {"enonce": "Exemple facultatif"}},
                    "immediate": screen}
        # Le stimulus n'est visible que pendant l'exposition et la réponse,
        # jamais dans les commandes de pause/interruption.
        if trial["phase"] == "exposition":
            if state["kind"] == "code" and state["params"]["modalite"] == "auditive":
                screen["audio_digit"] = trial["stimulus"]["chiffres"][trial["audio_index"]]
                screen["audio_index"] = trial["audio_index"]
            else:
                screen["stimulus"] = copy.deepcopy(trial["stimulus"])
            screen["remaining_ms"] = trial["remaining_ms"]
        elif trial["phase"] == "reponse":
            screen["question"] = self._immediate_question(state["kind"], state["params"])
            sample = trial["stimulus"]
            if state["kind"] == "chemin":
                screen["stimulus"] = {"positions": copy.deepcopy(sample["positions"])}
            elif state["kind"] == "objets":
                screen["stimulus"] = {key: copy.deepcopy(sample[key]) for key in ("positions", "objets", "reserve")}
            elif state["kind"] == "changement":
                screen["stimulus"] = {key: copy.deepcopy(sample[key]) for key in ("apres", "palette")}
        elif trial["phase"] == "masque":
            screen["remaining_ms"] = trial["remaining_ms"]
        elif trial["phase"] == "feedback":
            screen["correction"] = copy.deepcopy(trial.get("feedback"))
            screen["can_help"] = bool(trial.get("first") and (not trial.get("help") or trial["help"].get("answer") is None))
            screen["model"] = copy.deepcopy(trial["stimulus"])
            screen["first_response"] = copy.deepcopy(trial.get("first"))
            screen["help_response"] = copy.deepcopy((trial.get("help") or {}).get("answer"))
        elif trial["phase"] == "pret":
            screen["instruction"] = self._immediate_instruction(state["kind"], state["params"])
        return {**common, "immediate": screen}

    @staticmethod
    def _immediate_question(kind, params):
        return {"code": "Entrez les chiffres dans le même ordre.",
                "chemin": "Reprenez le chemin dans le même ordre.",
                "changement": "La composition est-elle identique ou différente ?",
                "objets": "Replacez les objets dans les emplacements."}[kind]

    @staticmethod
    def _immediate_instruction(kind, params):
        return {"code": "Retenez ce code ; chaque chiffre est présenté une fois.",
                "chemin": "Regardez les cases indiquées et retenez le chemin.",
                "changement": "Retenez les formes et leurs détails.",
                "objets": f"Retenez où se trouve chaque objet pendant {params['exposition_ms'] / 1000:g} secondes."}[kind]

    def _immediate_step(self, request):
        state = self.ui.get("immediate")
        if not state or state["finished"]:
            raise ValueError("Aucun bloc de mémoire immédiate actif")
        previous = state.get("last_request")
        def identity(value):
            return {k: v for k, v in value.items() if k != "elapsed_ms"}
        if previous and identity(previous) == identity(request):
            return self._immediate_view()
        state, trial = self._immediate_current()
        allowed_item_ids = {trial["id"]}
        if state.get("example"):
            allowed_item_ids.add(f"example:{state['session_id']}")
        if request.get("session_id") != state["session_id"] or request.get("item_id") not in allowed_item_ids:
            raise ValueError("Étape de mémoire immédiate périmée")
        if set(request) - {"action", "session_id", "item_id", "revision", "operation", "elapsed_ms",
                           "response", "observations", "assisted", "phase"}:
            raise ValueError("Données d’étape inconnues")
        if type(request.get("revision")) is not int or request["revision"] != state["revision"]:
            raise ValueError("Révision de mémoire immédiate périmée")
        elapsed = request.get("elapsed_ms", 0)
        if type(elapsed) not in (int, float) or not 0 <= elapsed <= 86400000:
            raise ValueError("Durée invalide")
        op = request.get("operation")
        allowed = {"show", "exposure-ended", "mask-ended", "audio-next", "answer", "help", "interrupt", "continue",
                   "example", "example-end", "example-close"}
        if op not in allowed:
            raise ValueError("Commande de mémoire immédiate inconnue")
        permitted_fields = {"show": set(), "exposure-ended": set(), "mask-ended": set(),
                            "audio-next": set(), "answer": {"response", "observations", "assisted"},
                            "help": set(), "interrupt": {"phase", "observations"}, "continue": set(),
                            "example": set(), "example-end": set(), "example-close": set()}
        if set(request) - {"action", "session_id", "item_id", "revision", "operation", "elapsed_ms"} - permitted_fields[op]:
            raise ValueError("Données incompatibles avec la commande")
        if op == "show" and trial["phase"] == "pret":
            trial.update(phase="exposition", started=_now(), remaining_ms=self._immediate_exposure(state))
        elif op == "example" and trial["phase"] == "pret" and trial["index"] == 1 and not trial.get("help") and not state.get("example"):
            example_stimulus = stimulus(state["kind"], state["params"], f"example:{state['session_id']}", True)
            state["example"] = {"phase": "exposition", "stimulus": example_stimulus, "audio_index": 0}
        elif op == "exposure-ended" and trial["phase"] == "exposition":
            if state["kind"] == "code" and state["params"]["modalite"] == "auditive":
                raise ValueError("Lecture audio inachevée")
            trial.update(phase="masque", remaining_ms=state["params"]["masque_ms"])
        elif op == "audio-next" and trial["phase"] == "exposition" and state["kind"] == "code" and state["params"]["modalite"] == "auditive":
            trial["audio_index"] += 1
            if trial["audio_index"] >= len(trial["stimulus"]["chiffres"]):
                trial.update(phase="masque", remaining_ms=state["params"]["masque_ms"])
        elif op == "audio-next" and state.get("example") and state["example"]["phase"] == "exposition" and state["kind"] == "code" and state["params"]["modalite"] == "auditive":
            example = state["example"]
            example["audio_index"] += 1
            if example["audio_index"] >= len(example["stimulus"]["chiffres"]):
                example["phase"] = "demonstration"
        elif op == "example-end" and state.get("example") and state["example"]["phase"] == "exposition":
            state["example"]["phase"] = "demonstration"
        elif op == "example-close" and state.get("example") and state["example"]["phase"] == "demonstration":
            state["example"] = None
        elif op == "mask-ended" and trial["phase"] == "masque":
            trial.update(phase="reponse", remaining_ms=0)
        elif op == "interrupt" and trial["phase"] in ("pret", "exposition", "masque", "reponse"):
            phase = request.get("phase")
            if phase != trial["phase"]:
                raise ValueError("Phase d’interruption incohérente")
            facts = observations(request.get("observations", {}))
            trial["elapsed_ms"] += elapsed
            interruption = {"phase": phase, "observations": facts, "date": _now(), "elapsed_ms": elapsed}
            if trial.get("help") and trial["help"].get("answer") is None:
                trial["help"]["interruption"] = interruption
                trial["phase"] = "feedback"
            else:
                trial["interruption"] = interruption
                trial["interruptions"] += 1
                state["trials"].append(self._immediate_new_trial(state, trial["index"], trial["id"]))
        elif op == "answer" and trial["phase"] == "reponse":
            response = request.get("response")
            facts = observations(request.get("observations", {}))
            result = correction(state["kind"], trial["stimulus"], response)
            record = {"response": copy.deepcopy(response), "correction": result, "observations": facts, "date": _now()}
            if request.get("assisted") is True:
                if not trial.get("help") or trial["help"].get("answer") is not None:
                    raise ValueError("Réponse aidée non ouverte")
                trial["help"].update(answer=record)
            elif request.get("assisted", False) is not False or trial.get("first"):
                raise ValueError("Première réponse déjà enregistrée")
            else:
                trial["first"] = record
            trial["feedback"] = result
            trial["phase"] = "feedback"
            trial["answer_elapsed_ms"] += elapsed
        elif op == "help" and trial["phase"] == "feedback" and trial.get("first") and (not trial.get("help") or trial["help"].get("answer") is None):
            if not trial.get("help"):
                trial["help"] = {"opened": _now(), "answer": None}
            else:
                trial["help"].update(opened=_now(), interruption=None)
            trial["phase"] = "pret"
        elif op == "continue" and trial["phase"] == "feedback":
            if trial["index"] < 4:
                state["index"] = trial["index"]
                next_trial = self._immediate_new_trial(state, trial["index"] + 1)
                # La consigne a déjà été lue au début du bloc chemin.
                # Les aides et reprises conservent leur démarrage explicite.
                if state["kind"] == "chemin":
                    next_trial.update(phase="exposition", started=_now(),
                                      remaining_ms=self._immediate_exposure(state))
                state["trials"].append(next_trial)
            else:
                state["finished"] = True
                state["summary"] = self._immediate_summary(state)
                self._immediate_archive(state)
        else:
            raise ValueError("Commande incompatible avec la phase courante")
        state["revision"] += 1
        state["last_request"] = copy.deepcopy(request)
        return self._immediate_view()

    @staticmethod
    def _immediate_exposure(state):
        params = state["params"]
        if state["kind"] in ("code", "chemin"):
            return params["longueur"] * params["signal_ms"] + max(0, params["longueur"] - 1) * params["intervalle_ms"]
        return params["exposition_ms"]

    @staticmethod
    def _immediate_summary(state):
        rows = {}
        for trial in state["trials"]:
            row = rows.setdefault(trial["index"], {"index": trial["index"], "premiere": None,
                                                    "aide": None, "interrupted": 0})
            if trial.get("first"):
                row["premiere"] = copy.deepcopy(trial["first"])
            if trial.get("help"):
                row["aide"] = copy.deepcopy(trial["help"])
            row["interrupted"] += trial["interruptions"]
        completed = sum(row["premiere"] is not None for row in rows.values())
        return {"blocks": completed, "parcours": state["kind"], "history": list(rows.values()),
                "version": state["version"]}

    def _immediate_archive(self, state):
        if state.get("archived"):
            return
        self.ui.setdefault("immediate_history", []).append({
            "session_id": state["session_id"], "parcours": state["kind"],
            "version": state["version"], "created": state["created"],
            "finished": _now(), "parametres": copy.deepcopy(state["params"]),
            "summary": copy.deepcopy(state["summary"]),
        })
        state["archived"] = True

    def _immediate_finish(self, request):
        if set(request) - {"action", "session_id"}:
            raise ValueError("Paramètres de clôture inconnus")
        state = self.ui.get("immediate")
        if not state or request.get("session_id") != state["session_id"]:
            raise ValueError("Bloc de mémoire immédiate inconnu")
        if not state["finished"]:
            state["finished"] = True
            state["example"] = None
            state["summary"] = self._immediate_summary(state)
            state["trials"][-1]["phase"] = "termine"
            state["revision"] += 1
            self._immediate_archive(state)
        return self._immediate_view()
