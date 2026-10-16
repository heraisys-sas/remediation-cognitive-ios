from engine.mastery.criteria import palier_maitrise_historique

SEUIL_MAITRISE = 0.9
SESSIONS_CONSECUTIVES_MAITRISE = 3

# Calibration de l'entrée adulte en calcul mental : le palier 5 évite les faits
# élémentaires, mais une difficulté nette sur un échantillon suffisant ramène au
# palier 3 lors de la séance automatique suivante.
from .catalog import CATALOGUE
PALIER_DEPART_CALCUL = CATALOGUE["calcul-mental"].start_level
PALIER_REPLI_CALCUL = 3
SEUIL_REPLI_CALCUL = 0.5
MIN_REPONSES_CALIBRATION = 8


def progression_apres_session(session, nb_repondu: int, taux: float, etat: dict):
    if nb_repondu <= 0:
        return
    # Les premières étapes préparent le palier : trois répétitions de ces
    # seules grilles ne démontrent pas la maîtrise de sa dernière étape.
    etapes = [i.get("contenu", {}).get("etape_progression", 0)
              for i in session.items_disponibles if i.get("palier") == session.palier]
    etape_finale = max(etapes, default=0)
    if etape_finale and not any(
        session.items_par_id[i]["contenu"].get("etape_progression") == etape_finale
        for i in session.reponses
    ):
        return
    historique_avant = list(etat["historique"])
    historique = list(historique_avant)
    historique.append((session.palier, float(taux)))
    historique_etapes = None
    corpus_renouvele = etape_finale or any(i.startswith("ev2-") for i in session.reponses) or (
        session.theme == "calcul-mental"
        and any(i.startswith("cm4-") for i in session.reponses)
    )
    if corpus_renouvele:
        # Les taux de l'ancien corpus ne prouvent pas la maîtrise de ces
        # nouvelles étapes ; les conserver sans les réutiliser pour avancer.
        historique_etapes = list(etat.get("historique_etapes", []))
        historique_etapes.append((session.palier, float(taux)))
    palier = etat["palier_courant"]
    calibration_en_echec = (
        session.theme == "calcul-mental"
        and not session.palier_force
        and session.palier == PALIER_DEPART_CALCUL
        and not historique_avant
        and nb_repondu >= MIN_REPONSES_CALIBRATION
        and taux < SEUIL_REPLI_CALCUL
    )
    if calibration_en_echec:
        palier = PALIER_REPLI_CALCUL
    elif palier_maitrise_historique(
        historique_etapes if corpus_renouvele else historique,
        palier=session.palier,
        seuil=SEUIL_MAITRISE,
        sessions_consecutives=SESSIONS_CONSECUTIVES_MAITRISE,
    ):
        palier = max(palier, session.palier + 1)
    return palier, historique, historique_etapes
