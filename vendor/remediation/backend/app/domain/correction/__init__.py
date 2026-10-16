from .. import capacites as capacites
"""API stable de correction côté serveur ; aucune réponse révélée avant soumission."""
from .numeric import (
    TOLERANCE_NUMERIQUE, _UNITES_MOTS, _DIZAINES_MOTS, _nombre_en_chiffres, _en_nombre, _corriger_numerique, _corriger_estimation,
)
from .normalization import (
    _normaliser_texte, _clef_texte,
)
from .sequence import (
    ETAPES_JUGEES_SEQUENCE, _mots_sequence, _liste_mots_sequence, _positions_expression, _evaluer_critere_sequence, _idee_retrouvee, corriger_sequence,
)
from .text import (
    _corriger_sans_espaces, _NUMERAUX_QUOTIDIEN, _MOTS_HEURE, _normaliser_horaires, _UNITES_QUANTITE, _MOTIF_NOMBRE_LETTRES, _normaliser_quantites, _DETERMINANTS, _sans_determinant, _meme_mot, _contient_reponse, _clef_reponse, _JOURS, _MOIS, _MOMENTS, _MOTS_NOMBRES, _jetons_critiques, _sens_proche, _est_reponse_libre, _distance, _corriger_mot,
)
from .recall import (
    _mots, _corriger_mots_ordonnes, corriger_rappel_libre, _corriger_rappel_libre,
)
from .deduction import (
    _corriger_grille,
)
from .dispatch import (
    corriger,
)

from .result import CorrectionResult, evaluer

__all__ = ['capacites', 'TOLERANCE_NUMERIQUE', '_UNITES_MOTS', '_DIZAINES_MOTS', '_nombre_en_chiffres', '_en_nombre', '_corriger_numerique', '_corriger_estimation', '_normaliser_texte', '_clef_texte', 'ETAPES_JUGEES_SEQUENCE', '_mots_sequence', '_liste_mots_sequence', '_positions_expression', '_evaluer_critere_sequence', '_idee_retrouvee', 'corriger_sequence', '_corriger_sans_espaces', '_NUMERAUX_QUOTIDIEN', '_MOTS_HEURE', '_normaliser_horaires', '_UNITES_QUANTITE', '_MOTIF_NOMBRE_LETTRES', '_normaliser_quantites', '_DETERMINANTS', '_sans_determinant', '_meme_mot', '_contient_reponse', '_clef_reponse', '_JOURS', '_MOIS', '_MOMENTS', '_MOTS_NOMBRES', '_jetons_critiques', '_sens_proche', '_est_reponse_libre', '_distance', '_corriger_mot', '_mots', '_corriger_mots_ordonnes', 'corriger_rappel_libre', '_corriger_rappel_libre', '_corriger_grille', 'corriger', 'CorrectionResult', 'evaluer']
