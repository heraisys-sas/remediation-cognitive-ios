"""Présentation visuelle séquencée ; rappel corrigé par le service mémoire amont."""
import copy
from mobile.input_hints import answer_inputmode

MEMORY_ACTIVITIES = {
    "pqrst-rappel": ("methodes", "pqrst-rappel", "Répondre de mémoire après lecture"),
    "quotidien": ("quotidien", None, "Situations du quotidien"),
    **{f"series-{mode}-{scope}": (theme,scope,f"Séries {label} — {title}")
       for mode,theme,label in (("lues","rappel-series","lues"),("entendues","series-entendues","entendues"))
       for scope,title in (("immediat","rappel immédiat"),("differe","rappel après attente"),("premiere-serie","première série"))},
    "chiffres-endroit": ("memoire", "chiffres-endroit", "Chiffres dans l’ordre"),
    "chiffres-envers": ("memoire", "chiffres-envers", "Chiffres en ordre inverse"),
    "mots": ("memoire", "mots", "Mots — ordre et ordre inverse"),
    "associations": ("memoire", "associations", "Associations mot–nombre"),
    "position": ("memoire", "position", "Position dans une séquence"),
}


def presentation(item):
    """Même alternance élément/blanc que presentation.js à la référence amont."""
    display = item["contenu"].get("affichage")
    if not display: return []
    timeline = []
    if display["mode"] in ("liste","texte"):
        timeline=[{"phase":"liste","content":display["elements"],"duration_ms":display["duree_totale_ms"]}]
    else:
        groups=display["series"] if display["mode"]=="series" else [display["elements"]]
        if display["mode"] not in ("sequence","series"):raise ValueError("Présentation inconnue")
        auditory=display.get("modalite")=="auditive"
        for group_index,group in enumerate(groups):
            for index,element in enumerate(group):
                event={"phase":"audio" if auditory else "element","duration_ms":0 if auditory else display["duree_par_item_ms"],
                       "position":index+1,"total":len(group),"group":group_index+1,"groups":len(groups)}
                if auditory:event["audio_path"]=display["audio"][element].removeprefix("/ui/")
                else:event["content"]=element
                timeline.append(event)
                pause=(display.get("pause_serie_ms",1500) if index==len(group)-1 and group_index<len(groups)-1
                       else display.get("pause_item_ms",2000))
                if index<len(group)-1 or group_index<len(groups)-1 or display.get("pause_item_ms"):
                    timeline.append({"phase":"blanc","duration_ms":pause})
    if item["contenu"].get("delai_s"):
        timeline.append({"phase":"attente","duration_ms":item["contenu"]["delai_s"]*1000})
    return timeline


class MemoryRuntime:
    @staticmethod
    def _memory_stub(item):
        # Le pont ne livre ni séquence complète ni question avant leur étape.
        return {"id": item["id"], "type": item["type"], "contenu": {"enonce": "Mémorisation visuelle"}}

    def _memory_state(self):
        cursor = self.ui["cursor"]
        reprise = cursor >= len(self.ui["session"]["items"])
        return self.ui.setdefault("memory", {}).setdefault(str(cursor), {
            "phase": "question" if reprise or not self._memory_item()["contenu"].get("affichage") else "pret", "index": 0, "revision": 0,
            "paused": False, "remaining_ms": 0, "answer_elapsed_ms": 0,
            "interruptions": 0, "skipped": False,
        })

    def _memory_item(self):
        return self._session().items_par_id[self.ui["queue"][self.ui["cursor"]]]

    def _memory_interrupt(self):
        if self.ui["cursor"] >= len(self.ui["queue"]):
            return
        state = self._memory_state()
        if not state["paused"]:
            state["paused"] = True
            if state["phase"]=="audio":state.update(phase="pret",index=0,remaining_ms=0,audio_failed=True)
            state["interruptions"] += 1
            state["revision"] += 1
            # Le segment depuis le dernier appel validé est inconnu après arrêt.

    def _memory_accumulate(self, state, elapsed):
        if state["phase"] in ("element", "blanc", "liste", "attente"):
            state["remaining_ms"] = max(0, state["remaining_ms"] - elapsed)
        elif state["phase"] == "question":
            state["answer_elapsed_ms"] += elapsed

    def _memory_present(self, state, timeline, index):
        state["index"] = index
        if index >= len(timeline):
            state["phase"] = "question"
            state["remaining_ms"] = 0
        else:
            state["phase"] = timeline[index]["phase"]
            state["remaining_ms"] = timeline[index]["duration_ms"]

    def _memory_step(self, request):
        if self.ui.get("activity") not in MEMORY_ACTIVITIES:
            raise ValueError("Parcours mémoire indisponible")
        current = self._current_item(request)
        state = self._memory_state()
        identity = lambda value: {key: value for key, value in value.items() if key != "elapsed_ms"}
        if state.get("receipt") and identity(state["receipt"]) == identity(request):
            return self._view()
        if (type(request.get("revision")) is not int or request["revision"] != state["revision"]
                or self.ui.get("feedback")):
            raise ValueError("Étape mémoire périmée")
        elapsed = request.get("elapsed_ms")
        if type(elapsed) not in (int, float) or not 0 <= elapsed <= 86400000:
            raise ValueError("Durée invalide")
        operation = request.get("operation")
        if state["paused"] and operation != "resume":
            raise ValueError("Reprendre la présentation avant de continuer")
        item = self._memory_item()
        if operation == "pause":
            self._memory_accumulate(state, elapsed)
            state["paused"] = True
            state["interruptions"] += 1
        elif operation == "resume" and state["paused"]:
            state["paused"] = False
        elif operation == "show" and state["phase"] == "pret":
            state["audio_failed"]=False
            self._memory_present(state, presentation(item), 0)
        elif operation == "audio-error" and state["phase"]=="audio":
            state.update(phase="pret",index=0,remaining_ms=0,audio_failed=True,interruptions=state["interruptions"]+1)
        elif operation == "advance" and state["phase"]=="audio":
            self._memory_present(state,presentation(item),state["index"]+1)
        elif operation == "advance" and state["phase"] in ("element", "blanc", "liste", "attente"):
            self._memory_accumulate(state, elapsed)
            if not state["remaining_ms"]:
                self._memory_present(state, presentation(item), state["index"] + 1)
        elif operation == "skip" and state["phase"] in ("element", "blanc", "liste", "attente"):
            # Le bouton Passer existe aussi sur le client amont.
            state.update(phase="question", remaining_ms=0, skipped=True)
        elif operation == "answer" and state["phase"] == "question":
            value = request.get("answer")
            if not isinstance(value, str) or not value.strip() or len(value) > 2000:
                raise ValueError("Réponse mémoire invalide")
            options=item["contenu"].get("options")
            if options and value not in options:raise ValueError("Choisir une réponse proposée")
            self._memory_accumulate(state, elapsed)
            session = self._session()
            result = self.manager.repondre(session.theme, session.session_id, item["id"], value,
                                          state["answer_elapsed_ms"])
            self._record_feedback(item["id"], result)
        else:
            raise ValueError("Commande incompatible avec l’étape mémoire")
        state["revision"] += 1
        state["receipt"] = copy.deepcopy(request)
        return self._view()

    def _memory_view(self, metadata):
        cursor = self.ui["cursor"]
        queue = self.ui["queue"]
        common = {"started": True, "session_id": self._session().session_id, **metadata,
                  "position": cursor + 1, "total": len(queue), "feedback": self.ui["feedback"],
                  "arret_propose": self.ui.get("stop_proposal", False),
                  "reprise": cursor >= len(self.ui["session"]["items"]), "protocol": None}
        if cursor >= len(queue):
            return {**common, "item": None, "memory": None}
        item = self._memory_item()
        state = self._memory_state()
        screen = {key: state[key] for key in ("phase", "revision", "paused", "remaining_ms", "interruptions", "skipped")}
        if not state["paused"] and not self.ui["feedback"]:
            if state["phase"] == "pret":
                screen["instruction"] = item["contenu"]["consigne"]
                screen["audio_failed"]=state.get("audio_failed",False)
            elif state["phase"] in ("element", "liste", "blanc", "audio", "attente"):
                event = presentation(item)[state["index"]]
                screen.update({key: event[key] for key in ("content", "position", "total", "group", "groups", "audio_path") if key in event})
            elif state["phase"] == "question":
                screen["question"] = item["contenu"]["enonce"]
                screen["options"]=item["contenu"].get("options")
                screen["inputmode"] = answer_inputmode(item)
        support = self.ui.get("reprise_support", {}).get(item["id"]) if common["reprise"] else None
        return {**common, "item": self._memory_stub(item), "memory": screen, "reprise_attendue": support}
