from __future__ import annotations
import re
from .. import capacites
from .normalization import (
    _clef_texte,
)
from .numeric import (
    _DIZAINES_MOTS, _UNITES_MOTS, _en_nombre, _nombre_en_chiffres,
)

def _corriger_sans_espaces(reponse, attendue) -> bool:
    """Séquence ou valeur courte (empans, n-back, paires) : la saisie est normalisée.

    - espaces, casse, accents et ponctuation ignorés ;
    - **nombres en toutes lettres convertis** : une réponse dictée arrive souvent en mots
      (« zéro sept un » pour « 071 », « soixante-treize » pour « 73 ») ;
    - l'ORDRE reste strict : c'est la tâche.
    """
    def clef(valeur) -> str:
        jetons = []
        for jeton in _clef_texte(valeur).split():
            nombre = _en_nombre(jeton)
            if nombre is not None and float(nombre).is_integer():
                jetons.append(str(int(nombre)))
            else:
                jetons.append(jeton)
        return "".join(jetons)

    return clef(reponse) == clef(attendue)

_NUMERAUX_QUOTIDIEN = {
    "zero": "0", "un": "1", "une": "1", "deux": "2", "trois": "3",
    "quatre": "4", "cinq": "5", "six": "6", "sept": "7", "huit": "8",
    "neuf": "9", "dix": "10", "onze": "11", "douze": "12", "treize": "13",
    "quatorze": "14", "quinze": "15", "seize": "16", "vingt": "20",
    "trente": "30", "quarante": "40", "cinquante": "50", "soixante": "60",
    "cent": "100", "mille": "1000",
}

_MOTS_HEURE = r"(?:h\b|heures?\b|hrs?\b)"

def _normaliser_horaires(texte: str) -> str:
    """Ramène les façons françaises de dire l'heure à la forme « 15h » / « 15h30 ».

    « 15 h », « 15 heures », « quinze heures », « 15:30 », « 15 heures 30 »,
    « trois heures et demie », « 15 heures moins le quart », « midi », « 8 heures
    du soir » : tout cela désigne la même heure. L'exercice porte sur le raisonnement,
    pas sur la façon d'écrire l'heure.
    """
    texte = re.sub(r"\bmidi\b", "12h", texte)
    texte = re.sub(r"\bminuit\b", "0h", texte)

    def avec_periode(correspondance):
        heure = int(correspondance.group(1))
        minutes = correspondance.group(2) or ""
        periode = correspondance.group(3) or ""
        if heure < 12 and periode.startswith(("du soir", "de l'apres-midi")):
            heure += 12
        return f"{heure}h{minutes}"

    texte = re.sub(
        rf"(\d{{1,2}})\s*{_MOTS_HEURE}(?:\s*(\d{{1,2}}))?(?:\s*(du soir|de l'apres-midi|du matin))?",
        avec_periode, texte)
    texte = re.sub(r"(\d{1,2})h\s*et\s*quart\b", lambda m: f"{m.group(1)}h15", texte)
    texte = re.sub(r"(\d{1,2})h\s*et\s*demie?\b", lambda m: f"{m.group(1)}h30", texte)
    texte = re.sub(r"(\d{1,2})h\s*moins\s*le\s*quart\b",
                   lambda m: f"{int(m.group(1)) - 1}h45", texte)
    # Minutes sur un seul chiffre : « 15h5 » vaut « 15h05 ».
    texte = re.sub(r"h(\d)\b", lambda m: f"h0{m.group(1)}", texte)
    return texte

_UNITES_QUANTITE = ("euros", "euro", "centimes", "centime", "litres", "litre", "kilos",
                    "kilo", "grammes", "gramme", "metres", "metre", "kilometres",
                    "kilometre", "minutes", "minute", "jours", "jour", "mois", "ans",
                    "personnes", "fois")

_MOTIF_NOMBRE_LETTRES = "|".join(sorted(
    {*_UNITES_MOTS, *_DIZAINES_MOTS, "cent", "mille", "quatre", "vingt", "et",
     "quatrevingt", "quatrevingtdix"}, key=len, reverse=True))

def _normaliser_quantites(texte: str) -> str:
    """Montants et quantités : « 180 € », « 180 eur » et « cent quatre-vingts euros ».

    Une réponse dictée arrive souvent écrite autrement que la réponse attendue : le
    symbole au lieu du mot, ou le montant en toutes lettres. L'exercice porte sur le
    raisonnement (ou la mémoire), pas sur la façon d'écrire un montant.
    """
    texte = re.sub(r"(?<=\d)\s*€", " euros", texte)          # « 180 € » -> « 180 euros »
    texte = re.sub(r"€\s*(?=\d)", "", texte)                 # « € 180 » -> « 180 euros »
    texte = re.sub(r"\b(?:euros?|eur\.?)\b", "euros", texte)  # « 180 eur » -> « 180 euros »

    def en_chiffres(correspondance):
        valeur = _nombre_en_chiffres(correspondance.group(1))
        if valeur is None:
            return correspondance.group(0)
        entier = int(valeur) if float(valeur).is_integer() else valeur
        return f"{entier} {correspondance.group(2)}"

    motif = (rf"((?:{_MOTIF_NOMBRE_LETTRES})s?(?:[\s-]+(?:{_MOTIF_NOMBRE_LETTRES})s?)*)"
             rf"\s+({'|'.join(_UNITES_QUANTITE)}s?)")
    return re.sub(motif, en_chiffres, texte)

_DETERMINANTS = {"un", "une", "1", "le", "la", "les", "des", "du", "de", "mon", "ma",
                 "mes", "ton", "ta", "tes", "son", "sa", "ses", "ce", "cet", "cette",
                 "ces", "l", "d"}

def _sans_determinant(texte: str) -> str:
    """Retire un déterminant de tête, s'il en reste quelque chose.

    « un verre » vaut « verre », « la carte de mutuelle » vaut « carte de mutuelle ». Le
    mot doit exister sans son déterminant : on ne vide pas une réponse qui serait
    seulement « un ».
    """
    jetons = texte.split()
    if len(jetons) > 1 and jetons[0] in _DETERMINANTS:
        return " ".join(jetons[1:])
    return texte

def _meme_mot(clef_a: str, clef_b: str) -> bool:
    """Deux clés désignent-elles le même mot ? Le **pluriel simple** est toléré.

    « des gares » vaut « gare » : le pluriel est une forme légitime, pas une autre réponse.
    La tolérance ne s'applique qu'à des mots d'au moins trois lettres, et jamais à une
    différence interne (« gare » / « garde » restent deux mots distincts).
    """
    if clef_a == clef_b:
        return True
    if not clef_a or not clef_b:
        return False
    if clef_a.rstrip("s") == clef_b.rstrip("s"):
        return min(len(clef_a), len(clef_b)) >= 3
    return False

def _contient_reponse(reponse, attendue, mots_max: int = 12) -> bool:
    """La réponse attendue est-elle **écrite dans** une petite phrase de la personne ?

    « on attend devant la gare » vaut « la gare », « un verre d'eau » vaut « verre »,
    « jeudi soir, comme prévu » vaut « jeudi soir ». Bornes, parce qu'accepter trop large
    est plus grave que refuser :

    - la réponse attendue reste **courte** (trois mots au plus) ;
    - la phrase donnée reste **courte** aussi (douze mots au plus) : au-delà, ce n'est plus
      une réponse, et le mot pourrait s'y trouver par hasard ;
    - aucun **jalon de sens** ne doit différer (jour, moment, nombre) ;
    - la correspondance se fait sur des **mots entiers** (jamais au milieu d'un mot).
    """
    clef = _clef_reponse(attendue)
    donnees = _clef_reponse(reponse)
    if not clef or not donnees or len(clef.split()) > 3:
        return False
    if len(donnees.split()) > mots_max:
        return False
    if _jetons_critiques(reponse) != _jetons_critiques(attendue):
        return False
    if clef == donnees:
        return True
    for variante in (clef, f"{clef}s" if not clef.endswith("s") else clef[:-1]):
        if re.search(rf"(?<![0-9a-z]){re.escape(variante)}(?![0-9a-z])", donnees):
            return True
    return False

def _clef_reponse(valeur) -> str:
    """Clé d'une réponse texte : casse, accents, espaces, horaires et nombres.

    - « 15 h », « 15h », « 15:00 » et « 15 heures » sont équivalents ;
    - « 15 heures 30 » vaut « 15h30 », « trois heures et demie » vaut « 3h30 » ;
    - « deux » et « 2 » sont équivalents (nombre en toutes lettres → chiffres).
    """
    texte = _clef_texte(valeur)
    # Déterminant de tête retiré **avant** tout le reste : « un verre » doit devenir
    # « verre », pas « 1 verre » (la conversion des nombres en lettres passe après).
    texte = _sans_determinant(texte)
    # 1. Montants et quantités en toutes lettres : « cent quatre-vingts euros » -> « 180 euros »
    #    (avant la conversion mot à mot, qui casserait les nombres composés).
    texte = _normaliser_quantites(texte)
    # 2. Nombres en toutes lettres isolés : « quinze heures » -> « 15 heures ».
    jetons = [_NUMERAUX_QUOTIDIEN.get(jeton, jeton) for jeton in texte.split()]
    texte = " ".join(jetons)
    # 3. Heures : « 15 h », « 15 heures », « 3 heures et demie », « midi »…
    texte = _normaliser_horaires(texte)
    # Séparateur d'heure restant (« 15:30 »), avec ou sans minutes.
    texte = re.sub(r"(\d{1,2})\s*[:h]\s*(\d*)", r"\1h\2", texte)
    # « 15h00 » vaut « 15h » (heure pleine).
    texte = re.sub(r"(\d)h00\b", r"\1h", texte)
    jetons = [_NUMERAUX_QUOTIDIEN.get(jeton, jeton) for jeton in texte.split()]
    jetons = _sans_determinant(" ".join(jetons)).split()
    return " ".join(jetons)

_JOURS = {"lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"}

_MOIS = {"janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout",
         "septembre", "octobre", "novembre", "decembre"}

_MOMENTS = {"matin", "midi", "apres-midi", "soir", "minuit", "nuit"}

_MOTS_NOMBRES = (set(_UNITES_MOTS) | set(_DIZAINES_MOTS) | {"cent", "mille"}) - {"un", "une"}

def _jetons_critiques(texte) -> frozenset[str]:
    """Jalons de sens d'une réponse : jours, mois, moments, nombres (chiffres ou lettres).

    Le découpage se fait sur tout caractère non alphanumérique : sans cela, « jeudi soir,
    comme prévu » ne contenait pas le jalon « soir » (le jeton était « soir, »), et la
    comparaison des jalons refusait à tort une réponse correcte.
    """
    jalons = set()
    for jeton in re.split(r"[^0-9a-z]+", _clef_texte(texte)):
        if (jeton in _JOURS or jeton in _MOIS or jeton in _MOMENTS
                or (jeton in _MOTS_NOMBRES and len(jeton) > 2)
                or any(caractere.isdigit() for caractere in jeton)):
            jalons.add(jeton)
    return frozenset(jalons)

def _sens_proche(reponse, attendues) -> bool:
    """Le poste reconnaît-il la réponse comme le même **sens** (dernier recours) ?

    Encadré : on ne traverse jamais un jalon de sens. Mesuré sur ce poste — « vendredi
    soir » ≈ « jeudi soir » 0,85, « jeudi matin » ≈ « jeudi soir » 0,81, « 14 h 30 » ≈
    « 15 h 30 » 0,999. Ces écarts-là sont des erreurs, pas des façons de dire : dès que
    les jalons diffèrent, la proximité de sens ne s'applique pas. Les variantes
    acceptables (réponse plus courte, synonyme) se déclarent dans l'item.
    """
    if not isinstance(reponse, str) or not reponse.strip():
        return False
    jalons = _jetons_critiques(reponse)
    # Une proximité vectorielle ne distingue pas toujours une phrase de sa négation.
    negations = {"pas", "jamais", "sans", "aucun", "aucune", "non"}
    polarite = lambda valeur: bool(negations & set(_clef_texte(valeur).split()))
    for cible in attendues:
        if not cible:
            continue
        if _jetons_critiques(cible) != jalons or polarite(cible) != polarite(reponse):
            continue
        if capacites.proche(str(reponse or ""), [str(cible)]):
            return True
    return False

def _est_reponse_libre(attendue) -> bool:
    """La réponse attendue est-elle une **phrase** (et non une valeur courte) ?

    Pour une heure, un nombre ou un code, seule la comparaison normalisée compte :
    comparer le « sens » n'aurait pas de sens. Pour une phrase, la comparaison
    sémantique du poste (embeddings Apple, repli lexical) tolère une reformulation.
    """
    texte = str(attendue or "").strip()
    if len(texte.split()) < 3:
        return False
    return not re.fullmatch(r"[\d\s:h.,;/+-]+", texte)

def _distance(a: str, b: str) -> int:
    if a == b:
        return 0
    precedent = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        courant = [i]
        for j, cb in enumerate(b, 1):
            courant.append(min(precedent[j] + 1, courant[j - 1] + 1,
                               precedent[j - 1] + (1 if ca != cb else 0)))
        precedent = courant
    return precedent[-1]

def _corriger_mot(reponse, item: dict) -> bool:
    """Réponse d'un seul mot (accès lexical) : tolérance de saisie et petite faute.

    - accents, casse et ponctuation ignorés ;
    - variantes acceptées si l'item les déclare (``reponse.variantes`` : synonymes,
      autre écriture) ;
    - une faute de frappe mineure reste acceptée (distance 1, ou 2 pour un mot long) :
      l'exercice porte sur la mémoire, pas sur l'orthographe.
    """
    bloc = item.get("reponse") or {}
    cibles = [bloc.get("valeur"), *(bloc.get("variantes") or [])]
    donnees = _clef_reponse(reponse)
    for cible in cibles:
        clef = _clef_reponse(cible)
        if not clef:
            continue
        if donnees == clef:
            return True
        # Pluriel simple : « des gares » vaut « gare » (même mot, autre forme).
        if _meme_mot(donnees, clef):
            return True
        if " " not in clef and " " not in donnees:
            # Faute de frappe tolérée seulement sur les mots assez longs : sur un mot court,
            # une lettre change crée un AUTRE mot (« gare » / « garde »). Accepter une réponse
            # fausse est plus grave que refuser une faute de frappe (ADR-008).
            tolerance = 2 if len(clef) >= 10 else 1 if len(clef) >= 7 else 0
            if tolerance and _distance(donnees, clef) <= tolerance:
                return True
        # Le mot attendu peut avoir été écrit dans une phrase (« un verre d'eau »).
        if _contient_reponse(reponse, cible):
            return True
    # Accès lexical : retrouver le mot demandé, pas un voisin sémantique.
    # Les synonymes légitimes restent possibles via les variantes du contenu.
    return False
