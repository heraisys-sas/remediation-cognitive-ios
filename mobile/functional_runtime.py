"""Parcours d’attention fonctionnelle, corrigés par le service amont inchangé."""
import copy


FUNCTIONAL_ACTIVITIES = {
    "actualiser-consigne": ("actualiser-consigne", None, "Actualiser une consigne"),
}

_MAX_ELAPSED_MS = 86_400_000


class FunctionalRuntime:
    """Adaptateur UI versionné ; aucune réponse attendue ne quitte le service."""

    @staticmethod
    def _functional_stub(item):
        return {"id": item["id"], "type": item["type"],
                "contenu": {"enonce": item["contenu"].get("enonce", "Exercice fonctionnel")}}

    def _functional_item(self):
        return self._session().items_par_id[self.ui["queue"][self.ui["cursor"]]]

    def _functional_state(self):
        cursor = str(self.ui["cursor"])
        reprise = self.ui["cursor"] >= len(self.ui["session"]["items"])
        return self.ui.setdefault("functional", {}).setdefault(cursor, {
            "phase": "messages", "index": 0, "revision": 0, "paused": False,
            "elapsed_ms": 0, "interruption_count": 0, "reprise": reprise,
        })

    def _functional_interrupt(self):
        if (self.ui.get("activity") not in FUNCTIONAL_ACTIVITIES
                or self.ui.get("cursor", 0) >= len(self.ui.get("queue", []))):
            return
        state = self._functional_state()
        if not state["paused"]:
            state["paused"] = True
            state["revision"] += 1
            state["interruption_count"] += 1

    def _functional_step(self, request):
        activity = self.ui.get("activity")
        if activity not in FUNCTIONAL_ACTIVITIES:
            raise ValueError("Parcours fonctionnel indisponible")
        item = self._functional_item()
        current = self._view()
        if (current.get("finished") or current.get("session_id") != request.get("session_id")
                or current.get("item", {}).get("id") != request.get("item_id")):
            raise ValueError("Étape fonctionnelle périmée")
        state = self._functional_state()

        def identity(value):
            return {key: item for key, item in value.items() if key != "elapsed_ms"}

        if state.get("receipt") and identity(state["receipt"]) == identity(request):
            return self._view()
        if type(request.get("revision")) is not int or request["revision"] != state["revision"] or self.ui.get("feedback"):
            raise ValueError("Étape fonctionnelle périmée")
        elapsed = request.get("elapsed_ms")
        if type(elapsed) not in (int, float) or not 0 <= elapsed <= _MAX_ELAPSED_MS:
            raise ValueError("Durée invalide")
        operation = request.get("operation")
        if state["paused"] and operation != "resume":
            raise ValueError("Reprendre l’exercice avant de continuer")

        content = item["contenu"]
        if operation == "pause":
            state["elapsed_ms"] += elapsed
            state["paused"] = True
            state["interruption_count"] += 1
        elif operation == "resume" and state["paused"]:
            state["paused"] = False
        elif operation == "next" and state["phase"] == "messages":
            state["elapsed_ms"] += elapsed
            state["index"] += 1
            if state["index"] >= len(content["etapes"]):
                state["phase"] = "form"
        elif operation == "submit" and state["phase"] == "form":
            answer = request.get("answer")
            fields = content["champs"]
            expected_keys = {field["id"] for field in fields}
            if not isinstance(answer, dict) or set(answer) != expected_keys:
                raise ValueError("Complète chaque champ avant de valider")
            if any(not isinstance(answer[key], str) or not answer[key].strip() or len(answer[key]) > 500
                   for key in expected_keys):
                raise ValueError("Complète chaque champ avant de valider")
            result = self.manager.repondre(self._session().theme, self._session().session_id,
                                           item["id"], answer, state["elapsed_ms"] + elapsed)
            self._record_feedback(item["id"], result)
        else:
            raise ValueError("Commande incompatible avec l’étape fonctionnelle")

        state["revision"] += 1
        state["receipt"] = copy.deepcopy(request)
        return self._view()

    def _functional_view(self, item):
        state = self._functional_state()
        screen = {key: state[key] for key in ("phase", "index", "revision", "paused", "interruption_count", "reprise")}
        content = item["contenu"]
        if state["paused"] or self.ui.get("feedback"):
            return screen
        activity = self.ui["activity"]
        if activity == "actualiser-consigne":
            if state["phase"] == "messages":
                step = content["etapes"][state["index"]]
                visible_step = {key: step[key] for key in ("titre", "evenement", "texte") if key in step}
                screen.update({"consigne": content.get("consigne", ""), "etape": visible_step,
                               "total": len(content["etapes"])})
            else:
                screen.update({"consigne": "Écris la consigne finale. Les éléments non modifiés restent valables.",
                               "fields": [{**field, "inputmode": "numeric" if field["id"] in {"quai", "nombre", "public"} else "text"}
                                          for field in content["champs"]]})
        return screen
