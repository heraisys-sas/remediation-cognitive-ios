from __future__ import annotations

def _corriger_grille(item: dict, reponse) -> bool:
    """Grille de déduction : la grille soumise doit être exacte (9 cases).

    La réponse est une chaîne « figure:couleur;… » (ordre de lecture) ; la
    comparaison est insensible à la casse, le découpage sur « ; ».
    """
    attendue = str((item.get("reponse") or {}).get("valeur") or "")
    cellules_attendues = [c.strip().lower() for c in attendue.split(";") if c.strip()]
    cellules_donnees = [c.strip().lower() for c in str(reponse or "").split(";") if c.strip()]
    return cellules_donnees == cellules_attendues
