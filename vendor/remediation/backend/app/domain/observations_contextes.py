"""Faits de présentation bornés ; la première réponse vient du correcteur serveur."""

PASSES = ("decouverte", "rappel")
TEMPS = ("presentee_ms", "exposition_ms", "photo_revelee_ms")
BOOLEENS = ("presentee", "incident_photo", "photo_apres_erreur")


def normaliser_faits(item: dict, donnees: dict, ordre: int) -> dict:
    if item.get("type") != "rappel-source" or not isinstance(donnees, dict):
        raise ValueError("observation incompatible")
    if donnees.get("passe") not in PASSES or type(donnees.get("ordre")) is not int or donnees["ordre"] != ordre:
        raise ValueError("passe ou ordre invalide")
    faits = {"item_id": item["id"], "passe": donnees["passe"], "ordre": ordre}
    for cle in TEMPS:
        if cle in donnees:
            valeur = donnees[cle]
            if type(valeur) is not int or not 0 <= valeur <= 10**14:
                raise ValueError("horodatage invalide")
            faits[cle] = valeur
    for cle in BOOLEENS:
        if cle in donnees:
            if type(donnees[cle]) is not bool:
                raise ValueError("fait invalide")
            faits[cle] = donnees[cle]
    if "photo_revelee_ms" in faits and not faits.get("photo_apres_erreur"):
        raise ValueError("révélation non déclarée")
    return faits


def fusionner_faits(observation: dict, faits: dict) -> None:
    premiere = observation.get("premiere_reponse")
    if faits.get("photo_apres_erreur") and (faits["passe"] != "rappel" or not premiere or premiere["correcte"]):
        raise ValueError("révélation incompatible")
    for cle, valeur in faits.items():
        if cle in BOOLEENS:
            observation[cle] = observation.get(cle, False) or valeur
        else:
            observation.setdefault(cle, valeur)
