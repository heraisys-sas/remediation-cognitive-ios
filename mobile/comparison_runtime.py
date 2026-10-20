"""Parcours sécurisé de comparaison de documents."""

import copy
import math


COMPARISON_ACTIVITIES = {
    "comparer-documents": ("comparer-documents", None, "Comparer des documents"),
}


class ComparisonRuntime:
    """Adaptateur de vue et de commande ; la correction reste au moteur."""

    def _comparison_state(self):
        cursor = self.ui["cursor"]
        if cursor >= len(self.ui["queue"]):
            raise ValueError("Aucun document à comparer")
        return self.ui.setdefault("comparison", {}).setdefault(str(cursor), {
            "phase": "question",
            "revision": 0,
            "paused": False,
            "answer_elapsed_ms": 0,
            "receipt": None,
        })

    def _comparison_interrupt(self):
        if self.ui.get("activity") != "comparer-documents" or "session" not in self.ui:
            return
        session = self._session()
        cursor = self.ui.get("cursor", 0)
        if (session.terminee or self.ui.get("feedback") is not None
                or cursor >= len(self.ui.get("queue", []))):
            return
        state = self._comparison_state()
        if not state["paused"]:
            state["paused"] = True
            state["revision"] += 1

    def _comparison_view(self, metadata):
        session = self._session()
        cursor = self.ui["cursor"]
        queue = self.ui["queue"]
        common = {
            "started": True,
            "session_id": session.session_id,
            "activity": metadata["activity"],
            "title": metadata["title"],
            "position": cursor + 1,
            "total": len(queue),
            "feedback": self.ui.get("feedback"),
            "arret_propose": self.ui.get("stop_proposal", False),
            "protocol": None,
        }
        if session.terminee:
            return {**common, "finished": True, "summary": session.resume_cloture,
                    "item": None, "comparison": None}
        if cursor >= len(queue):
            return {**common, "item": None, "comparison": None}

        item_id = queue[cursor]
        original = session.items_par_id[item_id]
        content = original.get("contenu", {})
        public_item = {
            "id": original["id"],
            "type": original["type"],
            "contenu": {key: copy.deepcopy(content[key])
                        for key in ("enonce", "consigne", "methode") if key in content},
        }
        state = self._comparison_state()
        comparison = {
            "phase": state["phase"],
            "revision": state["revision"],
            "paused": state["paused"],
        }
        if not state["paused"] and self.ui.get("feedback") is None:
            comparison["documents"] = copy.deepcopy(content.get("documents", []))
            comparison["champs"] = copy.deepcopy(content.get("champs", []))
        return {**common, "item": public_item, "comparison": comparison}

    def _comparison_step(self, request):
        if self.ui.get("activity") != "comparer-documents":
            raise ValueError("Parcours de comparaison indisponible")
        session = self._session()
        if session.terminee:
            raise ValueError("La séance est terminée")
        current = self._current_item(request)
        item_id = current["item"]["id"]
        item = session.items_par_id[item_id]
        if item.get("type") != "comparer-documents":
            raise ValueError("Cet item ne compare pas des documents")
        state = self._comparison_state()

        identity = lambda value: {key: val for key, val in value.items() if key != "elapsed_ms"}
        if state["receipt"] is not None and identity(state["receipt"]) == identity(request):
            return self._view()

        revision = request.get("revision")
        if (type(revision) is not int or revision != state["revision"]
                or self.ui.get("feedback") is not None):
            raise ValueError("Étape de comparaison périmée")
        elapsed = request.get("elapsed_ms")
        if type(elapsed) not in (int, float):
            raise ValueError("Durée invalide")
        try:
            finite_elapsed = math.isfinite(elapsed)
        except (OverflowError, TypeError, ValueError):
            finite_elapsed = False
        if not finite_elapsed or elapsed < 0 or elapsed > 86400000:
            raise ValueError("Durée invalide")

        operation = request.get("operation")
        if operation == "pause":
            if state["paused"]:
                raise ValueError("La comparaison est déjà en pause")
            state["answer_elapsed_ms"] += elapsed
            state["paused"] = True
        elif operation == "resume":
            if not state["paused"]:
                raise ValueError("La comparaison n’est pas en pause")
            state["paused"] = False
        elif operation == "answer":
            if state["paused"]:
                raise ValueError("Reprendre avant de valider")
            answer = request.get("answer")
            if type(answer) is not dict:
                raise ValueError("Réponse invalide")
            fields = item["contenu"].get("champs", [])
            allowed = {field["id"] for field in fields}
            if set(answer) != allowed or any(
                    type(value) is not str or value not in ("conforme", "ecart")
                    for value in answer.values()):
                raise ValueError("Réponse incomplète ou invalide")
            total_elapsed = state["answer_elapsed_ms"] + elapsed
            result = self.manager.repondre(
                session.theme, session.session_id, item_id, answer, total_elapsed)
            self._record_feedback(item_id, result)
        else:
            raise ValueError("Commande de comparaison invalide")

        state["revision"] += 1
        state["receipt"] = copy.deepcopy(request)
        return self._view()
