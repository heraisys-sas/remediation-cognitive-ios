"""Stimuli originaux v1 et correction descriptive, sans moteur adaptatif."""
import random
import re

VERSION = "memoires-immediates-v1"
POSITIONS = [{"id": str(i), "x": x, "y": y} for i, (x, y) in enumerate(((.15, .2), (.5, .12), (.82, .3), (.22, .72), (.58, .6), (.85, .82)))]
PALETTE = {"bleu": "#668fc0", "ocre": "#c39b54", "rose": "#b87892", "vert": "#6ca48e", "violet": "#9481b5", "orange": "#c48259"}
FORMES = ["cercle", "carre", "triangle", "losange", "etoile", "croix"]
OBJETS = [{"id": k, "nom": "clé" if k == "cle" else k} for k in ("cle", "tasse", "livre", "pomme")]


def parameters(parcours, provided):
    defaults = {"longueur": 4 if parcours == "code" else 3, "modalite": "visuelle", "condition": "forme", "exposition_ms": 6000 if parcours == "objets" else 5000, "signal_ms": 2000 if parcours == "code" else 1500, "intervalle_ms": 1000 if parcours == "code" else 500, "masque_ms": 1500 if parcours == "changement" else 1000 if parcours == "objets" else 0}
    if parcours not in ("code", "chemin", "changement", "objets") or not isinstance(provided, dict) or set(provided) - set(defaults):
        raise ValueError("Paramètres inconnus")
    defaults.update(provided)
    for key, low, high in (("longueur", 2, 6 if parcours in ("code", "chemin") else 4 if parcours == "objets" else 5), ("exposition_ms", 1000, 30000), ("signal_ms", 500, 10000), ("intervalle_ms", 0, 5000), ("masque_ms", 0, 10000)):
        value = defaults[key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError("Paramètre hors limites")
    if defaults["modalite"] not in ("visuelle", "auditive") or (parcours != "code" and defaults["modalite"] != "visuelle") or defaults["condition"] not in ("forme", "couleur", "association"):
        raise ValueError("Condition ou modalité inconnue")
    return defaults


def stimulus(parcours, params, seed, changed):
    rng = random.Random(f"{VERSION}:{parcours}:{seed}")
    n = params["longueur"]
    if parcours == "code":
        return {"chiffres": rng.sample(list("0123456789"), n)}
    if parcours == "chemin":
        return {"positions": POSITIONS, "trajet": rng.sample([p["id"] for p in POSITIONS], n)}
    if parcours == "objets":
        objects = OBJETS[:n]
        places = [str(i) for i in range(n)]
        rng.shuffle(places)
        reserve = [o["id"] for o in objects]
        rng.shuffle(reserve)
        return {"positions": [{"id": str(i), "x": (i + .5) / n, "y": .5} for i in range(n)], "objets": objects, "modele": dict(zip([o["id"] for o in objects], places)), "reserve": reserve}
    forms = rng.sample(FORMES, n)
    colors = rng.sample(list(PALETTE), n)
    before = [{"position": str(i), "forme": forms[i], "couleur": colors[i]} for i in range(n)]
    after = [dict(e) for e in before]
    if changed:
        i = rng.randrange(n)
        if params["condition"] == "association":
            j = rng.choice([j for j in range(n) if j != i])
            after[i]["couleur"], after[j]["couleur"] = after[j]["couleur"], after[i]["couleur"]
        else:
            key, bank = ("forme", FORMES) if params["condition"] == "forme" else ("couleur", list(PALETTE))
            after[i][key] = rng.choice([x for x in bank if x not in [e[key] for e in before]])
    return {"avant": before, "apres": after, "palette": PALETTE}


def observations(raw):
    if not isinstance(raw, dict) or len(raw) > 30:
        raise ValueError("Observations invalides")
    result = {}
    for key, value in raw.items():
        if key.endswith("_ms"):
            if type(value) not in (int, float) or not 0 <= value <= 86400000:
                raise ValueError("Durée invalide")
            result[key] = value
        elif key in ("modalite", "voix", "phase", "raison"):
            if not isinstance(value, str) or len(value) > 120:
                raise ValueError("Observation invalide")
            result[key] = value
        elif key in ("audio_indisponible", "absence_declaree") and type(value) is bool:
            result[key] = value
        else:
            raise ValueError("Observation inconnue")
    return result


def correction(parcours, sample, response):
    if response is None:
        return {"absence_declaree": True, "exacte": None}
    if parcours in ("code", "chemin"):
        expected = sample["chiffres"] if parcours == "code" else sample["trajet"]
        if parcours == "code":
            if not isinstance(response, str) or len(response) > 40 or not re.fullmatch(r"[0-9\s-]*", response):
                raise ValueError("Code invalide")
            answer = list(re.sub(r"[\s-]", "", response))
        else:
            if not isinstance(response, list) or len(response) > 12 or any(x not in [p["id"] for p in POSITIONS] for x in response):
                raise ValueError("Trajet invalide")
            answer = response
        if not answer and parcours == "code":
            raise ValueError("Déclarez une absence ou saisissez une réponse")
        remaining = expected.copy()
        found = 0
        for value in answer:
            if value in remaining:
                remaining.remove(value)
                found += 1
        return {"exacte": answer == expected, "attendue": "".join(expected) if parcours == "code" else expected, "positions_exactes": sum(a == b for a, b in zip(answer, expected)), "elements_retrouves": found, "longueur": len(expected)}
    if parcours == "objets":
        if not isinstance(response, dict) or set(response) - set(sample["modele"]) or any(p not in [e["id"] for e in sample["positions"]] for p in response.values()) or len(set(response.values())) != len(response):
            raise ValueError("Placement invalide")
        expected = sample["modele"]
        correct = sum(response.get(o) == p for o, p in expected.items())
        wrong = [o for o in response if response[o] != expected[o]]
        permutation = len(wrong) >= 2 and {response[o] for o in wrong} == {expected[o] for o in wrong}
        return {"exacte": correct == len(expected), "attendue": expected, "associations_exactes": correct, "associations_erronees": len(response) - correct, "non_places": len(expected) - len(response), "permutation": permutation, "nombre": len(expected)}
    if not isinstance(response, dict) or set(response) - {"decision", "localisation", "localisation_absente"} or response.get("decision") not in ("identique", "different"):
        raise ValueError("Décision invalide")
    if "localisation_absente" in response and type(response["localisation_absente"]) is not bool:
        raise ValueError("Absence de localisation invalide")
    locations = response.get("localisation", [])
    if not isinstance(locations, list) or len(set(locations)) != len(locations) or any(x not in [e["position"] for e in sample["avant"]] for x in locations):
        raise ValueError("Localisation invalide")
    changed = [a["position"] for a, b in zip(sample["avant"], sample["apres"]) if a != b]
    detected = response["decision"] == "different"
    return {"exacte": detected == bool(changed), "decision": response["decision"], "type": ("detection" if detected else "changement_manque") if changed else ("fausse_alerte" if detected else "rejet_correct"), "positions_modifiees": changed, "localisation_exacte": set(locations) == set(changed) if detected and changed and locations else None, "localisation_partielle": len(set(locations) & set(changed)) if detected and changed else None, "avant": sample["avant"], "apres": sample["apres"]}
