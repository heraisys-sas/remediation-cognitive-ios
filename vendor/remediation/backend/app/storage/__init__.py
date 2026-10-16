"""Stockage en fichiers chiffrés.

Deux dépôts strictement séparés (ADR-002) :
- « entraînement » : données non médicales ;
- « bilan »        : données de santé (usage familial, périmètre HDS potentiel).

Aucune jointure inter-périmètre ; toute corrélation passe par un export explicite
de l'utilisateur. Droit à l'effacement et export patient natif obligatoires.
"""
