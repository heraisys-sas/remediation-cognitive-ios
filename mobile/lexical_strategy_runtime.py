"""Parcours SFA/PCA : notes non notées, puis correction du mot par le service amont."""
import copy


LEXICAL_STRATEGY_ACTIVITIES = {
    "strategie-semantique": ("evocation", "strategie-semantique", "Stratégie sémantique (SFA)"),
    "strategie-phonologique": ("evocation", "strategie-phonologique", "Stratégie phonologique (PCA)"),
}


class LexicalStrategyRuntime:
    """Mixin à intégrer à ApplicationRuntime pour séquencer les exercices analyse-mot."""

    @staticmethod
    def _lexical_strategy_stub(item):
        # Le stub est stable et ne transporte jamais la réponse attendue.
        return {"id": item["id"], "type": "analyse-mot",
                "contenu": {"enonce": "Retrouver le mot"}}

    def _lexical_strategy_start(self):
        if not self.ui["session"]["items"]:
            session = self._session()
            self.manager.terminer(session.theme, session.session_id)
        self.ui["lexical_strategy"] = {
            "phase": "notes", "note_index": 0, "notes": [], "elapsed_ms": 0,
            "revision": 0, "paused": False,
        }

    def _lexical_strategy_interrupt(self):
        state = self.ui.get("lexical_strategy")
        if (state and state.get("phase") != "feedback" and not state["paused"]
                and self.ui.get("session", {}).get("items")):
            state["paused"] = True
            state["revision"] += 1

    def _lexical_strategy_item(self):
        return self._session().items_par_id[self.ui["queue"][self.ui["cursor"]]]

    def _lexical_strategy_step(self, request):
        session = self._session()
        activity = self.ui.get("activity")
        if activity not in LEXICAL_STRATEGY_ACTIVITIES or session.terminee:
            raise ValueError("Aucun parcours de stratégie lexicale actif")
        item = self._lexical_strategy_item()
        state = self.ui.get("lexical_strategy")
        if not state or request.get("session_id") != session.session_id or request.get("item_id") != item["id"]:
            raise ValueError("Étape de stratégie lexicale périmée")

        def identity(data):
            return {key: value for key, value in data.items() if key != "elapsed_ms"}

        if state.get("last_request") and identity(state["last_request"]) == identity(request):
            return self._view()
        if type(request.get("revision")) is not int or request["revision"] != state["revision"]:
            raise ValueError("Étape de stratégie lexicale périmée")
        elapsed = request.get("elapsed_ms")
        if type(elapsed) not in (int, float) or not 0 <= elapsed <= 86400000:
            raise ValueError("Durée invalide")

        operation = request.get("operation")
        if state["paused"] and operation != "resume":
            raise ValueError("Reprendre le parcours avant de continuer")
        if operation == "pause" and not state["paused"]:
            state["elapsed_ms"] += elapsed
            state["paused"] = True
        elif operation == "resume" and state["paused"]:
            state["paused"] = False
        elif operation == "note" and not state["paused"] and state["phase"] == "notes":
            value = request.get("value")
            prompts = item.get("contenu", {}).get("etapes", [])
            if not isinstance(value, str) or len(value) > 2000:
                raise ValueError("Note invalide")
            if state["note_index"] >= len(prompts):
                raise ValueError("Toutes les notes sont déjà saisies")
            state["notes"].append(value.strip())
            state["note_index"] += 1
            state["elapsed_ms"] += elapsed
            if state["note_index"] == len(prompts):
                state["phase"] = "answer"
        elif operation == "answer" and not state["paused"] and state["phase"] == "answer":
            value = request.get("value")
            if not isinstance(value, str) or not value.strip() or len(value) > 500:
                raise ValueError("Saisir le mot retrouvé")
            total_elapsed = state["elapsed_ms"] + elapsed
            result = self.manager.repondre(session.theme, session.session_id, item["id"],
                                           value.strip(), total_elapsed)
            state["elapsed_ms"] = total_elapsed
            if result.get("essai_supplementaire"):
                # Le service source conserve la stratégie active après le premier
                # échec ; il n'enregistre pas encore de correction/progression.
                state["retry_feedback"] = result.get("feedback", "Essaie encore.")
            else:
                state.pop("retry_feedback", None)
                self._record_feedback(item["id"], result)
                state["phase"] = "feedback"
        else:
            raise ValueError("Commande incompatible avec l'étape de stratégie lexicale")

        state["revision"] += 1
        state["last_request"] = copy.deepcopy(request)
        return self._view()

    def _lexical_strategy_view(self, item):
        state = self.ui["lexical_strategy"]
        content = item.get("contenu", {})
        view = {"phase": state["phase"], "revision": state["revision"],
                "paused": state["paused"], "note_index": state["note_index"],
                "notes": list(state["notes"]), "total_notes": len(content.get("etapes", []))}
        if state.get("retry_feedback"):
            view["retry_feedback"] = state["retry_feedback"]
        if state["paused"]:
            return view
        if state["phase"] == "notes":
            prompts = content.get("etapes", [])
            view.update({"instruction": content.get("consigne", ""),
                         "definition": content.get("definition", ""),
                         "prompt": prompts[state["note_index"]]})
        elif state["phase"] == "answer":
            view.update({"question": content.get("enonce", "Quel est ce mot ?")})
        return view
