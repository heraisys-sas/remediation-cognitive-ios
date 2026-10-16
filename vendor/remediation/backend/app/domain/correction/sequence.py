from __future__ import annotations
import re
from .normalization import (
    _clef_texte,
)
from .text import (
    _clef_reponse,
)

ETAPES_JUGEES_SEQUENCE = (1, 4, 5)
VERSION_PQRST = "pqrst-sequence-v1"
ETAPES_PQRST = ["P", "Q", "R", "S", "retour-S", "T1", "T2"]
PHASES_PQRST = {"pret", "P", "P-retour", "Q", "Q-retour", "R", "4",
                "retour-S", "5.0", "5.1", "relecture", "fin"}


def normaliser_observation_pqrst(item: dict, reponse: dict, partielle: bool = True) -> dict:
    """Valide une trace client bornée ; ne note ni une réponse ni un checkpoint."""
    def exiger(condition):
        if not condition:
            raise ValueError("Observation PQRST invalide")

    exiger(item.get("type") == "pqrst-mise-en-oeuvre" and isinstance(reponse, dict))
    exiger(set(reponse) <= {"1", "2", "4", "5", "_pqrst"})
    meta = reponse.get("_pqrst")
    attendues = {"version", "etapes_realisees", "statuts", "tentatives", "relectures",
                 "interruptions", "modele_avant_test", "phase", "reprise_apres_correction"}
    exiger(isinstance(meta, dict) and set(meta) == attendues)
    exiger(meta["version"] == VERSION_PQRST and isinstance(meta["phase"], str)
           and meta["phase"] in PHASES_PQRST)
    faites = meta["etapes_realisees"]
    exiger(isinstance(faites, list) and len(faites) <= len(ETAPES_PQRST)
           and faites == ETAPES_PQRST[:len(faites)])
    exiger(isinstance(meta["modele_avant_test"], bool)
           and meta["modele_avant_test"] == ("retour-S" in faites))
    exiger(isinstance(meta["reprise_apres_correction"], bool))
    if not partielle:
        exiger(faites == ETAPES_PQRST and meta["phase"] == "fin")

    etapes = {e["etape"]: e for e in item["contenu"]["etapes"]}
    cles = {"1": "P", "2": "Q", "4": "S", "5.0": "T1", "5.1": "T2"}
    statuts, tentatives = meta["statuts"], meta["tentatives"]
    exiger(isinstance(statuts, dict) and set(statuts) == {k for k, e in cles.items() if e in faites})
    exiger(isinstance(tentatives, dict) and set(tentatives) == (set(statuts) & {"4", "5.0", "5.1"}))
    tests = reponse.get("5", [])
    exiger(isinstance(tests, list) and len(tests) == sum(k.startswith("5.") for k in statuts))
    exiger(set(reponse) - {"5", "_pqrst"} == (set(statuts) & {"1", "2", "4"}))

    def valeur(cle, brut):
        exiger(brut is None or (isinstance(brut, str) and len(brut) <= 2000 and bool(brut.strip())))
        if brut is not None:
            brut = brut.strip()
            if cle == "1":
                exiger(brut in etapes[1]["options"])
            elif cle.startswith("5."):
                exiger(brut in etapes[5]["questions"][int(cle[-1])]["options"])
        return brut

    premieres = {}
    for cle in statuts:
        brute = tests[int(cle[-1])] if cle.startswith("5.") else reponse[cle]
        premieres[cle] = valeur(cle, brute)
        exiger(statuts[cle] == ("absence_declaree" if premieres[cle] is None else "reponse"))
    relectures, interruptions = meta["relectures"], meta["interruptions"]
    exiger(isinstance(relectures, list) and len(relectures) <= 3
           and all(isinstance(c, str) and c in tentatives for c in relectures)
           and len(set(relectures)) == len(relectures))
    exiger(isinstance(interruptions, dict) and set(interruptions) <= PHASES_PQRST)
    exiger(all(type(n) is int and 1 <= n <= 10000 for n in interruptions.values()))
    normalisees = {}
    for cle, essais in tentatives.items():
        exiger(isinstance(essais, list) and 1 <= len(essais) <= (2 if cle in relectures else 1))
        if not partielle:
            exiger(len(essais) == (2 if cle in relectures else 1))
        normalisees[cle] = []
        for i, essai in enumerate(essais):
            exiger(isinstance(essai, dict) and set(essai) == {"reponse", "condition", "modalite"})
            condition = essai["condition"]
            exiger(isinstance(condition, str) and condition in
                   {"sans_relecture", "apres_relecture", "reprise_interrompue"})
            exiger(essai["modalite"] == ("clavier" if cle == "4" else "choix"))
            if i:
                exiger(condition != "sans_relecture")
            if condition == "reprise_interrompue":
                exiger(bool(interruptions.get(cle)))
            if condition == "apres_relecture":
                exiger(cle in relectures or (cle == "5.1" and "5.0" in relectures))
            donnee = valeur(cle, essai["reponse"])
            if i == 0:
                exiger(donnee == premieres[cle])
            normalisees[cle].append({"reponse": donnee, "condition": condition,
                                    "modalite": essai["modalite"]})
    return {"version": VERSION_PQRST, "statut": "partielle" if partielle else "complete",
            "phase": meta["phase"], "etapes_realisees": list(faites),
            "reprise_apres_correction": meta["reprise_apres_correction"],
            "modele_avant_test": meta["modele_avant_test"], "statuts": dict(statuts),
            "parcours": premieres.get("1"), "question": premieres.get("2"),
            "tentatives": normalisees, "relectures": list(relectures),
            "interruptions": dict(interruptions)}

def _mots_sequence(valeur) -> set[str]:
    """Jetons d'une réponse libre, découpés sur tout ce qui n'est pas alphanumérique.

    L'apostrophe et le trait d'union séparent : « d'identité » donne `identite`, sinon une
    idée-clé écrite sans apostrophe ne serait jamais retrouvée (dictée, réponse tapée vite).
    """
    return {jeton for jeton in re.split(r"[^0-9a-z]+", _clef_texte(valeur)) if jeton}

def _liste_mots_sequence(valeur) -> list[str]:
    return [jeton for jeton in re.split(r"[^0-9a-z]+", _clef_texte(valeur)) if jeton]

def _positions_expression(expression: str, jetons: list[str]) -> list[int]:
    attendus = _liste_mots_sequence(expression)
    if not attendus:
        return []
    largeur = len(attendus)
    return [
        debut for debut in range(len(jetons) - largeur + 1)
        if jetons[debut:debut + largeur] == attendus
    ]

def _evaluer_critere_sequence(critere: dict, jetons: list[str]) -> str:
    """Classe une idée de reformulation : retrouvée, contredite ou non reconnue.

    Les expressions et contradictions sont déclarées par item. Une négation située
    juste avant une expression reconnue (``pas au bureau``, ``sans identité``) prime
    également sur la simple présence du mot-clé. Le correcteur reste volontairement
    borné : il ne prétend pas comprendre toute phrase libre.
    """
    for contradiction in critere.get("contradictions") or []:
        if _positions_expression(str(contradiction), jetons):
            return "contredite"

    groupes = critere.get("groupes") or [critere.get("expressions") or []]
    groupes_retrouves = 0
    for groupe in groupes:
        groupe_retrouve = False
        for expression in groupe:
            for debut in _positions_expression(str(expression), jetons):
                contexte = jetons[max(0, debut - 4):debut]
                if any(mot in contexte for mot in ("pas", "sans", "jamais", "aucun", "aucune")):
                    return "contredite"
                groupe_retrouve = True
                break
            if groupe_retrouve:
                break
        groupes_retrouves += int(groupe_retrouve)
    return "retrouvee" if groupes and groupes_retrouves == len(groupes) else "non_reconnue"

def _idee_retrouvee(idee: str, jetons: set[str], minimum: int = 4) -> bool:
    """Une idée-clé est retrouvée si un jeton la porte — égal ou préfixe.

    Le préfixe évite d'exiger la forme exacte : « remboursement » doit valoir l'idée
    « rembourse », « identité » valoir « identite ».
    """
    clef = _clef_texte(idee)
    if not clef:
        return False
    if clef in jetons or f"{clef}s" in jetons:
        return True
    if len(clef) < minimum:
        return False
    return any(jeton.startswith(clef) for jeton in jetons)

def corriger_sequence(item: dict, reponse) -> tuple[bool, dict]:
    """Juge une séquence « PQRST mis en œuvre » (ADR-015) : (réussi, détail par étape).

    - **étape 1 — Parcours** : le sujet du texte (choix) ;
    - **étape 2 — Question** : **non notée** ; on vérifie seulement qu'une question a été
      écrite, et le **modèle** est renvoyé — c'est la production qui travaille, pas sa note ;
    - **étape 4 — Reformulation** : idées-clés retrouvées, seuil déclaré par l'item
      (4 sur 5) ; les idées manquées sont renvoyées pour le retour ;
    - **étape 5 — Test** : les deux questions de mémoire, réussies ensemble.

    La lecture (étape 3) ne se juge pas : elle est guidée par la question écrite.
    """
    contenu = item.get("contenu") or {}
    etapes = {etape.get("etape"): etape for etape in contenu.get("etapes") or []}
    donnees = reponse if isinstance(reponse, dict) else {}
    observation = normaliser_observation_pqrst(item, donnees, partielle=False) if "_pqrst" in donnees else None

    def fournie(numero: int):
        return donnees.get(str(numero), donnees.get(numero))

    detail: dict[str, dict] = {}
    verdicts: list[bool] = []

    # 1 — Parcours
    parcours = etapes.get(1) or {}
    reussi_1 = _clef_reponse(fournie(1)) == _clef_reponse(parcours.get("bonne"))
    detail["1"] = {"correcte": reussi_1, "attendue": parcours.get("bonne")}
    verdicts.append(reussi_1)

    # 2 — Question écrite (non notée : une production vide est simplement signalée)
    question = etapes.get(2) or {}
    texte_question = str(fournie(2) or "").strip()
    detail["2"] = {
        "correcte": bool(texte_question),
        "modele": question.get("modele"),
        "non_notee": True,
    }

    # 4 — Reformulation : critères sémantiques bornés, avec contradictions explicites.
    reformulation = etapes.get(4) or {}
    criteres = reformulation.get("criteres") or []
    seuil = float((item.get("reponse") or {}).get("seuil") or reformulation.get("seuil") or 1.0)
    jetons = _liste_mots_sequence(fournie(4))
    evaluations = [(_evaluer_critere_sequence(critere, jetons), critere) for critere in criteres]
    trouvees = [critere["label"] for etat, critere in evaluations if etat == "retrouvee"]
    contredites = [critere["label"] for etat, critere in evaluations if etat == "contredite"]
    manquantes = [critere["label"] for etat, critere in evaluations if etat == "non_reconnue"]
    reussi_4 = (
        bool(criteres)
        and not contredites
        and (len(trouvees) / len(criteres)) >= seuil
    )
    detail["4"] = {
        "correcte": reussi_4,
        "trouvees": trouvees,
        "contredites": contredites,
        "manquantes": manquantes,
        "seuil": seuil,
        "modele": reformulation.get("modele"),
        "correction_bornee": True,
    }
    verdicts.append(reussi_4)

    # 5 — Test : les deux questions de mémoire
    test = etapes.get(5) or {}
    questions = test.get("questions") or []
    reponses_test = fournie(5)
    if not isinstance(reponses_test, list):
        reponses_test = [reponses_test]
    verdicts_questions = []
    for rang, question_test in enumerate(questions):
        donnee = reponses_test[rang] if rang < len(reponses_test) else None
        verdicts_questions.append(
            _clef_reponse(donnee) == _clef_reponse(question_test.get("bonne"))
        )
    reussi_5 = bool(verdicts_questions) and all(verdicts_questions)
    detail["5"] = {
        "correcte": reussi_5,
        "questions": [q.get("bonne") for q in questions],
        "reussies": verdicts_questions,
    }
    verdicts.append(reussi_5)

    if observation is not None:
        for cle, essais in observation["tentatives"].items():
            for rang, essai in enumerate(essais):
                if cle == "4":
                    evaluation = detail["4"] if rang == 0 else corriger_sequence(
                        item, {**{k: v for k, v in donnees.items() if k != "_pqrst"},
                               "4": essai["reponse"]})[1]["4"]
                    statut = ("absence_declaree" if essai["reponse"] is None else
                              "contradiction" if evaluation["contredites"] else
                              "a_verifier" if evaluation["manquantes"] else "compatible")
                    essai["correction"] = {k: evaluation[k] for k in
                                          ("correcte", "trouvees", "contredites", "manquantes", "seuil")}
                    essai["correction"]["etat"] = statut
                else:
                    correcte = _clef_reponse(essai["reponse"]) == _clef_reponse(questions[int(cle[-1])]["bonne"])
                    essai["correction"] = {"correcte": correcte, "etat":
                        "absence_declaree" if essai["reponse"] is None else "exacte" if correcte else "incorrecte"}
        detail["observation"] = observation
    return all(verdicts), detail
