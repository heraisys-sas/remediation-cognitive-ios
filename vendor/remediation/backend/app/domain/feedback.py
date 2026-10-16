#!/usr/bin/env python3
"""Quand révéler la réponse après une erreur — décision pédagogique par type d'exercice.

Deux pratiques s'opposent dans la littérature, et elles ne s'appliquent pas au même type
d'exercice (voir ADR-014) :

- **errorless learning** (Baddeley & Wilson ; Middleton & Schwartz, 2012) : sur une erreur,
  donner la réponse **tout de suite**, pour ne pas laisser ré-encoder une erreur — indiqué
  quand la personne ne peut pas se corriger seule (mnésique, accès lexical) ;
- **pratique de récupération / effet de test** (Roediger & Karpicke) et **hypothèse de
  guidage** (Schmidt, 1991 ; Winstein & Schmidt, 1990) : c'est **l'essai** qui apprend, et un
  retour immédiat améliore la performance en séance mais **dégrade la rétention** — indiqué
  quand la réponse se **raisonne**.

D'où la règle retenue : jamais de réponse **avant** un essai ; réponse immédiate quand
l'information se **récupère** ; **un second essai** avant la réponse quand la tâche se
**raisonne**.
"""

from __future__ import annotations

#: Types d'exercices où la réponse se **raisonne** : la personne a les moyens de trouver.
#: Une première erreur donne donc un second essai (sans révéler la réponse) ; la réponse
#: n'apparaît qu'après cet essai — ou à la reprise, en fin de séance.
TYPES_ESSAI_SUPPLEMENTAIRE = frozenset({
    # Méthodes : choisir un plan, une auto-instruction, vérifier un plan.
    "but-etapes",
    "auto-instruction",
    "plan-a-verifier",
})


def essai_supplementaire(type_item: str) -> bool:
    """Une première erreur sur ce type d'exercice ouvre-t-elle un second essai ?"""
    return type_item in TYPES_ESSAI_SUPPLEMENTAIRE
