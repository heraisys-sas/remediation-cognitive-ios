"""Adaptateur iOS des parcours attentionnels fonctionnels importés."""

import copy


ATTENTION_ACTIVITIES = {
    "reperer-essentiel": ("reperer-essentiel", None, "Repérer l’essentiel"),
    "cap-reprendre": ("garder-cap", "reprendre", "Garder le cap — reprendre après une interruption"),
}

ATTENTION_PROTOCOL_VERSION = 1
_MAX_ELAPSED_MS = 86_400_000
_REQUEST_FIELDS = {"action", "session_id", "item_id", "revision", "operation", "elapsed_ms", "value"}


class AttentionRuntime:
    """Mixin séquencé ; les réponses attendues restent dans le service source."""

    @staticmethod
    def _attention_stub(item):
        # Le texte de l’énoncé peut désigner un dossier confidentiel au rappel.
        # Un libellé neutre évite aussi qu’une lecture vocale contourne le masque.
        label = "Repérer l’essentiel" if item["type"] == "reperer-essentiel" else "Reprendre le fil"
        return {"id": item["id"], "type": item["type"],
                "contenu": {"enonce": label}}

    def _attention_item(self):
        session = self._session()
        return session.items_par_id[self.ui["queue"][self.ui["cursor"]]]

    def _attention_state(self):
        item = self._attention_item()
        cursor = str(self.ui["cursor"])
        states = self.ui.setdefault("attention", {})
        state = states.get(cursor)
        if state is None:
            if item["type"] == "reperer-essentiel":
                state = {"phase": "messages", "index": 0, "answers": {}}
            elif item["type"] == "reprise-interrompue":
                state = {"phase": "control", "index": 0, "points": {},
                         "interruption": None, "reprise": None,
                         "interruption_done": False}
            else:
                raise ValueError("Type de parcours attentionnel incompatible")
            state.update({"version": ATTENTION_PROTOCOL_VERSION, "revision": 0,
                          "paused": False, "elapsed_ms": 0, "interruptions": 0,
                          "last_request": None})
            states[cursor] = state
        if state.get("version") != ATTENTION_PROTOCOL_VERSION:
            raise ValueError("Version du protocole attentionnel incompatible")
        return state

    def _attention_interrupt(self):
        """Met en pause automatiquement et conserve le point de reprise durable."""
        if (self.ui.get("activity") not in ATTENTION_ACTIVITIES
                or self.ui.get("cursor", 0) >= len(self.ui.get("queue", []))
                or self.ui.get("feedback")):
            return
        state = self._attention_state()
        if not state["paused"]:
            state["paused"] = True
            state["revision"] += 1
            state["interruptions"] += 1

    @staticmethod
    def _attention_identity(request):
        return {key: value for key, value in request.items() if key != "elapsed_ms"}

    def _attention_step(self, request):
        if not isinstance(request, dict) or set(request) - _REQUEST_FIELDS:
            raise ValueError("Données d’étape attentionnelle inconnues")
        if request.get("action") not in (None, "attention-step"):
            raise ValueError("Action attentionnelle incompatible")
        if self.ui.get("activity") not in ATTENTION_ACTIVITIES:
            raise ValueError("Parcours attentionnel indisponible")
        session = self._session()
        if session.terminee or self.ui.get("cursor", 0) >= len(self.ui.get("queue", [])):
            raise ValueError("Aucun parcours attentionnel actif")
        item = self._attention_item()
        state = self._attention_state()
        current = self._view()
        if (current.get("finished") or current.get("session_id") != request.get("session_id")
                or current.get("item", {}).get("id") != request.get("item_id")):
            raise ValueError("Étape attentionnelle périmée")
        previous = state.get("last_request")
        if previous and self._attention_identity(previous) == self._attention_identity(request):
            return self._view()
        if (type(request.get("revision")) is not int
                or request["revision"] != state["revision"]
                or self.ui.get("feedback")):
            raise ValueError("Étape attentionnelle périmée")
        elapsed = request.get("elapsed_ms", 0)
        if (type(elapsed) not in (int, float) or not 0 <= elapsed <= _MAX_ELAPSED_MS
                or state["elapsed_ms"] + elapsed > _MAX_ELAPSED_MS):
            raise ValueError("Durée invalide")
        operation = request.get("operation")
        if type(operation) is not str or operation not in {"select", "submit", "pause", "resume"}:
            raise ValueError("Commande attentionnelle inconnue")
        if operation == "select":
            if "value" not in request:
                raise ValueError("Choix requis")
        elif "value" in request:
            raise ValueError("Données incompatibles avec la commande")
        if state["paused"] and operation != "resume":
            raise ValueError("Reprendre l’exercice avant de continuer")

        if operation == "pause":
            state["elapsed_ms"] += elapsed
            state["paused"] = True
            state["interruptions"] += 1
        elif operation == "resume":
            if not state["paused"]:
                raise ValueError("Le parcours attentionnel n’est pas en pause")
            state["paused"] = False
        elif operation == "select":
            state["elapsed_ms"] += elapsed
            self._attention_select(item, state, request["value"])
        elif operation == "submit":
            if state["phase"] != "submit":
                raise ValueError("Termine les choix avant de valider")
            answer = self._attention_answer(item, state)
            result = self.manager.repondre(session.theme, session.session_id, item["id"],
                                           answer, state["elapsed_ms"] + elapsed)
            self._record_feedback(item["id"], result)
            state["phase"] = "feedback"
            state["elapsed_ms"] += elapsed

        state["revision"] += 1
        state["last_request"] = copy.deepcopy(request)
        return self._view()

    @staticmethod
    def _attention_select(item, state, value):
        content = item["contenu"]
        phase = state["phase"]
        if item["type"] == "reperer-essentiel":
            if phase != "messages" or type(value) is not str or value not in ("oui", "non"):
                raise ValueError("Choisis oui ou non pour le message affiché")
            messages = content["messages"]
            index = state["index"]
            if index >= len(messages):
                raise ValueError("Tous les messages ont déjà reçu une réponse")
            state["answers"][messages[index]["id"]] = value
            state["index"] += 1
            if state["index"] == len(messages):
                state["phase"] = "submit"
            return

        if phase == "control":
            index = state["index"]
            points = content["points"]
            if index >= len(points):
                raise ValueError("Tous les points ont déjà été contrôlés")
            point = points[index]
            if type(value) is not str or value not in point["options"]:
                raise ValueError("Choix de contrôle invalide")
            state["points"][point["id"]] = "valide" if value == point["options"][0] else "reprendre"
            state["index"] += 1
            if (not state["interruption_done"]
                    and state["index"] == content["interruption_apres"]):
                state["phase"] = "interruption"
            elif state["index"] == len(points):
                state["phase"] = "submit"
        elif phase == "interruption":
            options = content["interruption"]["options"]
            if type(value) is not str or value not in options:
                raise ValueError("Réponds au message de détour")
            state["interruption"] = value
            state["interruption_done"] = True
            state["phase"] = "resume-choice"
        elif phase == "resume-choice":
            point_ids = {point["id"] for point in content["points"]}
            if type(value) is not str or value not in point_ids:
                raise ValueError("Choisis le point où reprendre")
            state["reprise"] = value
            state["phase"] = "control"
        else:
            raise ValueError("Choix incompatible avec l’étape attentionnelle")

    @staticmethod
    def _attention_answer(item, state):
        if item["type"] == "reperer-essentiel":
            message_ids = {message["id"] for message in item["contenu"]["messages"]}
            if set(state["answers"]) != message_ids:
                raise ValueError("Chaque message doit recevoir un choix")
            return copy.deepcopy(state["answers"])
        point_ids = {point["id"] for point in item["contenu"]["points"]}
        if (set(state["points"]) != point_ids or not state["interruption_done"]
                or state["interruption"] is None or state["reprise"] not in point_ids):
            raise ValueError("Le contrôle, le détour et le point de reprise sont requis")
        return {"points": copy.deepcopy(state["points"]), "reprise": state["reprise"],
                "interruption": state["interruption"]}

    def _attention_view(self, metadata):
        """Construit la vue hôte complète avec uniquement l’étape visible."""
        session_data = self.ui["session"]
        session = self._session()
        if session.terminee:
            return {"started": True, "finished": True, "summary": session.resume_cloture,
                    **metadata}
        cursor = self.ui["cursor"]
        queue = self.ui["queue"]
        if cursor >= len(queue):
            item = None
            screen = None
        else:
            item = self._attention_item()
            state = self._attention_state()
            screen = {"phase": state["phase"], "revision": state["revision"],
                      "paused": state["paused"], "interruptions": state["interruptions"],
                      "elapsed_ms": state["elapsed_ms"], "index": state["index"]}
            if not state["paused"] and not self.ui.get("feedback"):
                content = item["contenu"]
                if item["type"] == "reperer-essentiel":
                    screen["objective"] = content["objectif"]
                    screen["criterion"] = content["critere"]
                    screen["instruction"] = content.get("consigne", "")
                    screen["total"] = len(content["messages"])
                    if state["phase"] == "messages":
                        message = content["messages"][state["index"]]
                        screen["message"] = {"id": message["id"], "text": message["texte"]}
                        screen["answer_count"] = len(state["answers"])
                    elif state["phase"] == "submit":
                        screen["instruction"] = "Tes choix sont conservés. Vérifie-les avant la correction finale."
                        screen["answers"] = [
                            {"message": message["texte"], "value": state["answers"][message["id"]]}
                            for message in content["messages"]
                        ]
                elif state["phase"] == "control":
                    point = content["points"][state["index"]]
                    screen.update({"total": len(content["points"]),
                                   "position": state["index"] + 1,
                                   "title": content["enonce"], "goal": content["but"],
                                   "point": {"id": point["id"], "label": point["label"],
                                             "state": point["etat"],
                                             "options": list(point["options"])}})
                elif state["phase"] == "interruption":
                    interruption = content["interruption"]
                    screen.update({"instruction": "Réponds à ce bref message avant de revenir au contrôle.",
                                   "prompt": interruption["enonce"],
                                   "options": list(interruption["options"])})
                elif state["phase"] == "resume-choice":
                    screen.update({"instruction": "Le dossier est momentanément masqué. Quel point dois-tu traiter maintenant ?",
                                   "points": [{"id": point["id"], "label": point["label"]}
                                              for point in content["points"]]})
                elif state["phase"] == "submit":
                    screen.update({"total": len(content["points"]), "title": content["enonce"],
                                   "goal": content["but"], "points": copy.deepcopy(state["points"]),
                                   "instruction": "Le contrôle est terminé. Tu peux valider.",
                                   "interruption_answered": state["interruption_done"],
                                   "resume_point": state["reprise"],
                                   "resume_label": next(point["label"] for point in content["points"]
                                                        if point["id"] == state["reprise"]),
                                   "point_summaries": [{"id": point["id"], "label": point["label"]}
                                                       for point in content["points"]]})
            if state["paused"] or self.ui.get("feedback"):
                screen = {key: screen[key] for key in
                          ("phase", "revision", "paused", "interruptions", "elapsed_ms", "index")}
            item = self._attention_stub(item)
        return {"started": True, "session_id": session_data["session_id"],
                **metadata, "item": item, "item_id": item["id"] if item else None,
                "finished": False, "attention": screen, "position": cursor + 1,
                "total": len(queue), "choice_revision": self.ui.get("choice_revision", 0),
                "hints_used": 0, "retry_feedback": None, "feedback": self.ui.get("feedback"),
                "arret_propose": self.ui.get("stop_proposal", False),
                "reprise": cursor >= len(session_data["items"]),
                "reprise_attendue": None}
