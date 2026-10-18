"""Deux passes Contextes ; effets métier et premières réponses confiés au service amont."""
import copy


class ContextesRuntime:
    @staticmethod
    def _contextes_stub(item):
        return {"id": item["id"], "type": "rappel-source", "contenu": {"enonce": "Retrouver le contexte"}}

    def _contextes_start(self):
        if not self.ui["session"]["items"]:
            session = self._session()
            self.manager.terminer(session.theme, session.session_id)
        self.ui["contextes"] = {"pass": "decouverte", "phase": "pret", "revision": 0,
                                "paused": False, "exposure_ms": 0, "elapsed_ms": 0}

    def _contextes_item(self):
        return self.ui["session"]["items"][self.ui["cursor"]]

    def _contextes_facts(self):
        return {"passe": self.ui["contextes"]["pass"], "ordre": self.ui["cursor"] + 1}

    def _contextes_record(self, **facts):
        session = self._session()
        self.manager._enregistrer_contexte(session, {"item_id": self._contextes_item()["id"],
                                                    **self._contextes_facts(), **facts})

    def _contextes_interrupt(self):
        state = self.ui["contextes"]
        if not self.ui["session"]["items"]:
            return
        if not state["paused"]:
            state["paused"] = True
            state["revision"] += 1
            # Ne pas inventer une durée d'exposition perdue à l'arrêt du processus.
            self._contextes_record()

    def _contextes_step(self, request):
        session = self._session()
        if self.ui.get("activity") != "memoire-source" or session.terminee:
            raise ValueError("Aucun parcours Contextes actif")
        item = self._contextes_item()
        state = self.ui["contextes"]
        if request.get("session_id") != session.session_id or request.get("item_id") != item["id"]:
            raise ValueError("Étape Contextes périmée")
        identity = lambda data: {k: v for k, v in data.items() if k != "elapsed_ms"}
        if state.get("last_request") and identity(state["last_request"]) == identity(request):
            return self._view()
        if type(request.get("revision")) is not int or request["revision"] != state["revision"]:
            raise ValueError("Étape Contextes périmée")
        elapsed = request.get("elapsed_ms")
        if type(elapsed) not in (int, float) or not 0 <= elapsed <= 86400000:
            raise ValueError("Durée invalide")
        operation = request.get("operation")
        if state["paused"] and operation != "resume":
            raise ValueError("Reprendre le parcours avant de continuer")
        if operation == "pause":
            self._contextes_accumulate(elapsed)
            state["paused"] = True
        elif operation == "resume" and state["paused"]:
            state["paused"] = False
        elif operation == "show" and state["phase"] == "pret":
            state["image_failed"] = False
            state["phase"] = "photo"
            self._contextes_record(presentee=True, presentee_ms=self._contextes_now())
        elif operation == "loaded" and state["phase"] == "photo":
            state["phase"] = "exposition"
            self._contextes_record(exposition_ms=self._contextes_now())
        elif operation == "image-error" and state["phase"] in ("photo", "exposition", "feedback"):
            self._contextes_record(incident_photo=True)
            state["image_failed"] = True
            if state["phase"] != "feedback":
                self._contextes_accumulate(elapsed)
                state["phase"] = "pret"
        elif operation == "hide" and state["phase"] == "exposition":
            self._contextes_accumulate(elapsed)
            state["phase"] = "question"
            state["elapsed_ms"] = 0
        elif operation == "answer" and state["phase"] == "question":
            value = request.get("value")
            if not isinstance(value, str) or value not in item["contenu"]["options"]:
                raise ValueError("Choisir une réponse proposée")
            state["elapsed_ms"] += elapsed
            result = self.manager.repondre(session.theme, session.session_id, item["id"], value,
                state["elapsed_ms"], memorisation=state["pass"] == "decouverte",
                observation_contextes=self._contextes_facts())
            self.ui["feedback"] = result
            if result.get("motif_arret") == "duree":
                self.ui["stop_proposal"] = True
            state["phase"] = "feedback"
        elif operation == "reveal-loaded" and state["phase"] == "feedback" and state["pass"] == "rappel" and not self.ui["feedback"]["correcte"]:
            self._contextes_record(photo_apres_erreur=True, photo_revelee_ms=self._contextes_now())
            state["reveal_recorded"] = True
        elif operation == "next" and state["phase"] == "feedback":
            self.ui["cursor"] += 1
            self.ui["feedback"] = None
            if self.ui["cursor"] == len(self.ui["session"]["items"]):
                if state["pass"] == "decouverte":
                    state["pass"] = "rappel"
                    self.ui["cursor"] = 0
                else:
                    self.manager.terminer(session.theme, session.session_id)
            state.update(phase="pret" if state["pass"] == "decouverte" else "question",
                         elapsed_ms=0, exposure_ms=0, image_failed=False, reveal_recorded=False)
        else:
            raise ValueError("Commande incompatible avec l'étape Contextes")
        state["revision"] += 1
        state["last_request"] = copy.deepcopy(request)
        return self._view()

    def _contextes_now(self):
        return int(self.manager.horloge().timestamp() * 1000)

    def _contextes_accumulate(self, elapsed):
        state = self.ui["contextes"]
        if state["phase"] == "exposition":
            state["exposure_ms"] += elapsed
        elif state["phase"] == "question":
            state["elapsed_ms"] += elapsed

    def _contextes_view(self, metadata):
        state = self.ui["contextes"]
        item = self._contextes_item()
        contenu = item["contenu"]
        screen = {key: state[key] for key in ("pass", "phase", "revision", "paused")}
        screen["image_failed"] = state.get("image_failed", False)
        if not state["paused"]:
            if state["phase"] == "pret":
                screen["instruction"] = contenu["consigne"]
            elif state["phase"] in ("photo", "exposition"):
                screen["image"] = contenu["affichage"]["image"]
                screen["remaining_ms"] = max(0, contenu["affichage"]["duree_totale_ms"] - state["exposure_ms"])
            else:
                screen["question"] = contenu["enonce"]
                screen["options"] = contenu["options"] if state["phase"] == "question" else []
                if state["phase"] == "feedback" and state["pass"] == "rappel" and not self.ui["feedback"]["correcte"] and not state.get("image_failed"):
                    screen["reveal_recorded"] = state.get("reveal_recorded", False)
                    screen["image"] = contenu["affichage"]["image"]
        return {"started": True, "session_id": self._session().session_id, **metadata,
                "item": self._contextes_stub(item), "contextes": screen, "protocol": None,
                "position": self.ui["cursor"] + 1, "total": len(self.ui["session"]["items"]),
                "feedback": self.ui["feedback"], "arret_propose": self.ui.get("stop_proposal", False)}
