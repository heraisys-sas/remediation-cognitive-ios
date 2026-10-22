"""Prises de message : fait précis, jamais accepté par proximité vectorielle."""

import re

from .text import _clef_reponse, _negative

# Compatibilité explicite des items historiques, sans modifier leurs données.
# La cible est vérifiée : un identifiant réutilisé ne reprend pas ces variantes.
_LEGACY_VARIANTS = {
    "qo-1-message-04": ("la porte de la cave", ("la cave",)),
    "qo-1-message-06": ("chez la gardienne", ("la gardienne",)),
}
_PREFIXES = ("", "c'est", "la réponse est", "je dirais")
_SUFFIXES = ("", "comme prévu")
_CONTEXT = {
    "qo-1-message-01": ("le rendez-vous est à",),
    "qo-1-message-03": ("la pharmacie rouvre",),
    "qo-1-message-05": ("le train de",),
    "qo-1-message-06": ("le colis est", "le colis se trouve"),
    "qo-1-message-08": ("la voiture sera prête",),
}


def _key(value) -> str:
    return " ".join(re.findall(r"[0-9a-z]+", _clef_reponse(value)))


def correct_message(item: dict, response) -> bool:
    """Égalité normalisée ou variante explicite dans une enveloppe neutre bornée.

    Une phrase arbitraire contenant la cible ne prouve pas le fait demandé :
    « derrière chez la gardienne » ne vaut pas « chez la gardienne ».
    """
    if not isinstance(response, str) or not response.strip():
        return False
    block = item.get("reponse") or {}
    target = block.get("valeur")
    if not isinstance(target, str) or not target.strip():
        return False
    if _negative(response) != _negative(target):
        return False
    variants = [target, *(block.get("variantes") or [])]
    identifier = item.get("id")
    legacy_target, legacy_variants = _LEGACY_VARIANTS.get(identifier, (None, ()))
    if target == legacy_target:
        variants.extend(legacy_variants)
    prefixes = (*_PREFIXES, *_CONTEXT.get(identifier, ()))
    given = _key(response)
    return any(given == _key(" ".join((prefix, variant, suffix)))
               for variant in variants if isinstance(variant, str) and variant.strip()
               for prefix in prefixes for suffix in _SUFFIXES)
