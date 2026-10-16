"""Sélection des items d'une séance (côté serveur).

Règle du sprint 1 (docs/30-technique/api-contract.md), dans le palier
courant uniquement :
1. d'abord les items **dus** selon FSRS (``engine.srs.fsrs.est_due``) ;
2. puis les **nouveaux** items (aucune carte FSRS persistée) du même
   palier ;
3. quota maximal de 12 items par séance.

Un thème vierge démarre au palier 1 (le palier courant est une
responsabilité du stockage backend, cf. ``storage/store.py``).
L'ordre est déterministe (ordre du contenu versionné) pour rester
reproductible en test et en suivi.
"""

from __future__ import annotations

from datetime import datetime

from engine.srs.fsrs import CarteFSRS, est_due


def selectionner_items(
    items: list[dict],
    cartes: dict[str, CarteFSRS],
    palier_courant: int,
    maintenant: datetime,
    max_items: int = 12,
    inclure_non_dus: bool = False,
) -> list[dict]:
    """Retourne les items à servir : dus d'abord, puis nouveaux, quota respecté.

    - ``items`` : items complets du thème (contenu versionné) ;
    - ``cartes`` : cartes FSRS persistées du thème (par item_id) ;
    - ``palier_courant`` : palier de travail actuel ;
    - ``maintenant`` : instant de la sélection (naïf = interprété UTC) ;
    - ``max_items`` : quota de la séance (dosage, défaut 12).

    Les items déjà vus mais non dus ne sont normalement jamais re-servis
    (répétition espacée). ``inclure_non_dus`` autorise une pratique volontaire
    propre aux thèmes courts qui la déclarent ; les échéances les plus proches
    passent alors en premier. Aucun item d'un autre palier n'est mélangé.
    """
    du_palier = [item for item in items if item.get("palier") == palier_courant]
    dus = [
        item
        for item in du_palier
        if item["id"] in cartes and est_due(cartes[item["id"]], maintenant)
    ]
    nouveaux = [item for item in du_palier if item["id"] not in cartes]
    if any(item.get("contenu", {}).get("etape_progression") for item in du_palier):
        # Les révisions faciles ne doivent pas monopoliser toutes les séances.
        # Nouveautés dans l'ordre des étapes ; révisions les plus avancées d'abord.
        nouveaux.sort(key=lambda i: i["contenu"].get("etape_progression", 1))
        dus.sort(key=lambda i: -i["contenu"].get("etape_progression", 1))
        reserve = min(len(nouveaux), max(1, max_items // 2))
        revises = dus[:max_items - reserve]
        selection = revises + nouveaux[:max_items - len(revises)]
    else:
        selection = dus + nouveaux
    if inclure_non_dus and len(selection) < max_items:
        deja_choisis = {item["id"] for item in selection}
        non_dus = [
            item for item in du_palier
            if item["id"] in cartes and item["id"] not in deja_choisis
        ]
        non_dus.sort(key=lambda item: cartes[item["id"]].echeance)
        selection.extend(non_dus[:max_items - len(selection)])
    return selection[:max_items]
