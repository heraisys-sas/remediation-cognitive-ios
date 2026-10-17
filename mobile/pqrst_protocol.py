"""Séquencement mobile PQRST ; correction et observation restent au service amont."""
import copy
import re

from backend.app.domain.messages import PQRST_INTERFACE as WORDS

RESPONSE_PHASES = {"P": "1", "Q": "2", "4": "4", "5.0": "5.0", "5.1": "5.1"}
REALIZED = {"1": "P", "2": "Q", "4": "S", "5.0": "T1", "5.1": "T2"}
FOLLOWING = {"P": "P-retour", "Q": "Q-retour", "4": "retour-S", "5.0": "5.1", "5.1": "fin"}


def create(reprise=False):
    return {"revision": 0, "phase": "pret", "paused": False, "target": None, "elapsed_ms": 0,
            "answer": {"5": [], "_pqrst": {"version": "pqrst-sequence-v1", "phase": "pret",
                "etapes_realisees": [], "statuts": {}, "tentatives": {}, "relectures": [],
                "interruptions": {}, "modele_avant_test": False, "reprise_apres_correction": reprise}}}


def pause(state):
    if state["paused"] or state["phase"] in ("pret", "fin"):
        return
    phase = state["target"] if state["phase"] == "relecture" else state["phase"]
    counts = state["answer"]["_pqrst"]["interruptions"]
    counts[phase] = min(10000, counts.get(phase, 0) + 1)
    state["paused"] = True


def transition(state, operation, value=None):
    phase = state["phase"]
    answer = state["answer"]
    meta = answer["_pqrst"]
    if operation == "pause":
        pause(state)
    elif operation == "resume":
        if not state["paused"]:
            raise ValueError("Le parcours n’est pas en pause")
        state["paused"] = False
    elif state["paused"]:
        raise ValueError("Reprendre le parcours avant de continuer")
    elif phase in RESPONSE_PHASES and operation in ("respond", "reread"):
        key = RESPONSE_PHASES[phase]
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 2000):
            raise ValueError("Réponse PQRST invalide")
        value = value.strip() if value is not None else None
        if operation == "reread" and (key not in ("4", "5.0", "5.1") or key in meta["relectures"]):
            raise ValueError("Relecture indisponible à cette étape")
        if key not in meta["statuts"]:
            meta["statuts"][key] = "absence_declaree" if value is None else "reponse"
            if key.startswith("5."):
                answer["5"].append(value)
            else:
                answer[key] = value
        if key in ("4", "5.0", "5.1"):
            condition = ("reprise_interrompue" if meta["interruptions"].get(key) else
                         "apres_relecture" if key in meta["relectures"] or
                         (key.startswith("5.") and "5.0" in meta["relectures"]) else "sans_relecture")
            meta["tentatives"].setdefault(key, []).append({"reponse": value, "condition": condition,
                                                         "modalite": "clavier" if key == "4" else "choix"})
        if REALIZED[key] not in meta["etapes_realisees"]:
            meta["etapes_realisees"].append(REALIZED[key])
        if operation == "reread":
            meta["relectures"].append(key)
            state["target"] = phase
            state["phase"] = "relecture"
        else:
            state["phase"] = FOLLOWING[phase]
    elif operation == "continue" and phase in ("pret", "P-retour", "Q-retour", "R", "retour-S", "relecture"):
        if phase == "R":
            meta["etapes_realisees"].append("R")
        if phase == "retour-S":
            meta["etapes_realisees"].append("retour-S")
            meta["modele_avant_test"] = True
        state["phase"] = {"pret": "P", "P-retour": "Q", "Q-retour": "R", "R": "4",
                          "retour-S": "5.0", "relecture": state["target"]}[phase]
    else:
        raise ValueError("Action incompatible avec l’étape PQRST")
    meta["phase"] = state["phase"]
    state["revision"] += 1


def screen(state, item):
    """Ne livre que les supports autorisés à l'étape active, jamais le texte caché."""
    content = item["contenu"]
    steps = {e["etape"]: e for e in content["etapes"]}
    phase = state["phase"]
    result = {"revision": state["revision"], "phase": phase, "paused": state["paused"],
              "paragraphs": [], "actions": [], "options": None, "input_label": None, "can_reread": False}
    def text(key, **values):
        return WORDS[key].format(**values)
    def paragraph(value):
        if value:
            result["paragraphs"].append(value)
    def action(operation, label):
        result["actions"].append({"operation": operation, "label": text(label)})
    if state["paused"]:
        paragraph(text("pause_titre")); paragraph(text("pause_detail"))
        return result
    if phase == "pret":
        paragraph(text("pret")); action("continue", "commencer")
    elif phase == "P":
        paragraph(text("P")); paragraph(content.get("titre_texte"))
        paragraph(re.match(r"^[^.!?]*[.!?]", content["texte"])[0] if re.match(r"^[^.!?]*[.!?]", content["texte"]) else "")
        paragraph(steps[1]["enonce"])
        result["options"] = steps[1]["options"]
    elif phase == "P-retour":
        paragraph(text("sujet_attendu", sujet=steps[1]["bonne"])); action("continue", "continuer")
    elif phase == "Q":
        paragraph(text("Q")); result["input_label"] = text("question")
    elif phase == "Q-retour":
        paragraph(text("question_modele", modele=steps[2]["modele"])); action("continue", "vers_lecture")
    elif phase in ("R", "relecture"):
        paragraph(text("R" if phase == "R" else "relecture"))
        if phase == "R":
            paragraph(state["answer"].get("2"))
        paragraph(content["texte"])
        action("continue", "vers_reformulation" if phase == "R" else "fin_relecture")
    elif phase == "4":
        paragraph(text("S")); result["input_label"] = text("reformulation")
    elif phase == "retour-S":
        paragraph(text("retour-S")); paragraph(text("retour_s"))
        last = state["answer"]["_pqrst"]["tentatives"]["4"][-1]["reponse"]
        paragraph(text("production", reponse=last) if last is not None else text("absence"))
        paragraph(text("modele", modele=steps[4]["modele"])); action("continue", "vers_test")
    elif phase in ("5.0", "5.1"):
        number = int(phase[-1])
        paragraph(text("T", numero=number + 1, total=2)); paragraph(text("test_condition"))
        paragraph(steps[5]["questions"][number]["enonce"])
        result["options"] = steps[5]["questions"][number]["options"]
    elif phase == "fin":
        paragraph(text("fin")); action("submit", "envoyer")
    if phase in RESPONSE_PHASES:
        result["response_label"] = text("valider")
        result["absence_label"] = text("sans_question" if phase == "Q" else "sans_reponse")
        meta = state["answer"]["_pqrst"]
        result["can_reread"] = phase in ("4", "5.0", "5.1") and phase not in meta["relectures"]
        if result["can_reread"]:
            result["reread_label"] = text("relire")
            result["reread_absence_label"] = text("absence_relire")
        if phase in meta["relectures"] or (phase == "5.1" and "5.0" in meta["relectures"]):
            paragraph(text("aidee"))
    return copy.deepcopy(result)
