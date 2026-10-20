"""Réponses à choix : préserver le second essai amont et les renvois du pont."""
import copy

CHOICE_ACTIVITIES = {
    "cap-adapter": ("garder-cap", "adapter", "Adapter un plan"),
    "cap-verifier": ("garder-cap", "verifier", "Vérifier avant de terminer"),
    "choisir-plan": ("methodes", "choisir-plan", "Choisir un plan"),
    "auto-instruction": ("methodes", "auto-instruction", "Se guider avant d’agir"),
    "verifier-plan": ("methodes", "verifier-plan", "Vérifier un plan"),
    "chercher-information": ("methodes", "chercher-information", "Chercher dans un document"),
}


class ChoiceRuntime:
    def _choice_answer(self, request):
        if self.ui.get("activity") not in CHOICE_ACTIVITIES:
            raise ValueError("Parcours à choix indisponible")
        identity = lambda data: {key: value for key, value in data.items() if key != "elapsed_ms"}
        previous = self.ui.get("choice_receipt")
        if previous and identity(previous) == identity(request):
            return self._view()
        current = self._current_item(request)
        revision = self.ui.get("choice_revision", 0)
        if (type(request.get("revision")) is not int or request["revision"] != revision
                or self.ui.get("feedback")):
            raise ValueError("Choix périmé")
        value = request.get("answer")
        if not isinstance(value, str) or value not in current["item"]["contenu"]["options"]:
            raise ValueError("Choisir une réponse proposée")
        elapsed = request.get("elapsed_ms")
        if type(elapsed) not in (int, float) or not 0 <= elapsed <= 86400000:
            raise ValueError("Durée invalide")
        session = self._session()
        elapsed += self.ui.get("choice_elapsed_ms", 0)
        result = self.manager.repondre(session.theme, session.session_id, current["item"]["id"], value, elapsed)
        self.ui["choice_revision"] = revision + 1
        self.ui["choice_receipt"] = copy.deepcopy(request)
        if result.get("essai_supplementaire"):
            self.ui["choice_elapsed_ms"] = elapsed
            self.ui["retry_feedback"] = result["feedback"]
        else:
            self.ui.pop("retry_feedback", None)
            self.ui.pop("choice_elapsed_ms", None)
            self._record_feedback(current["item"]["id"], result)
        return self._view()
