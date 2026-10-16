"""Couche de capacités du poste — chaque fonction choisit la meilleure implémentation
disponible, avec un repli qui ne dépend de rien.

Le logiciel reste **local** : aucune capacité ne sort de la machine. Pour chaque
besoin, on prend d'abord ce que le système fournit, puis un petit moteur embarqué,
puis un repli déterministe.

- ``similarite`` : **empreintes de phrases d'Apple** (`NaturalLanguage` /
  `NLEmbedding`, hors ligne, aucun modèle à embarquer) si disponibles ; sinon
  comparaison **lexicale** (n-grammes de caractères + recouvrement de mots) —
  toujours présente, sans dépendance.
- ``synthese`` : la **voix du système** (`say` sur macOS, `powershell`/SAPI sur
  Windows, `espeak` sur Linux), renvoyée en WAV.
- ``voix`` (reconnaissance) : assurée **côté client** (navigateur, ou OS de la
  tablette) — le serveur ne peut pas capter le micro.

Portabilité : aucun paquet n'est obligatoire ; chaque fournisseur est détecté à
l'exécution. Ajouter un moteur embarqué (ONNX Runtime + mini-modèle) revient à
ajouter une branche dans ``_fournisseur_similarite`` — voir
``docs/30-technique/pistes-extension-ia.md``.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

#: Seuil historique des réponses libres. Les scores observés sur un poste ne
#: constituent pas une calibration transférable entre fournisseurs (issue #6).
SEUIL_SIMILARITE = 0.78

_EMBEDDINGS: object | None = None
_FOURNISSEUR: str | None = None


# --- Normalisation ------------------------------------------------------------


def _normaliser(texte: str) -> str:
    sans_accent = unicodedata.normalize("NFD", str(texte or "").casefold())
    sans_accent = "".join(c for c in sans_accent if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^0-9a-z]+", " ", sans_accent).split())


def _ngrammes(texte: str, taille: int = 3) -> set[str]:
    plat = _normaliser(texte).replace(" ", "")
    if len(plat) < taille:
        return {plat} if plat else set()
    return {plat[i:i + taille] for i in range(len(plat) - taille + 1)}


# --- Similarité ---------------------------------------------------------------


def _embeddings_apple():
    """Empreintes de phrases d'Apple, ou None si indisponibles (hors macOS)."""
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        try:
            import NaturalLanguage as nl  # pyobjc — macOS uniquement

            _EMBEDDINGS = nl.NLEmbedding.sentenceEmbeddingForLanguage_("fr") or False
        except Exception:
            _EMBEDDINGS = False
    return _EMBEDDINGS or None


def fournisseur_similarite() -> str:
    """Fournisseur retenu : ``nle_embedding`` (Apple) ou ``lexical`` (repli)."""
    global _FOURNISSEUR
    if _FOURNISSEUR is None:
        _FOURNISSEUR = "nle_embedding" if _embeddings_apple() is not None else "lexical"
    return _FOURNISSEUR


def _similarite_apple(a: str, b: str) -> float:
    embeddings = _embeddings_apple()
    va, vb = embeddings.vectorForString_(a), embeddings.vectorForString_(b)
    if va is None or vb is None:
        return 0.0
    va = [float(x) for x in va]
    vb = [float(x) for x in vb]
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(x * x for x in vb))
    if not na or not nb:
        return 0.0
    return max(0.0, min(1.0, sum(x * y for x, y in zip(va, vb)) / (na * nb)))


def _similarite_lexicale(a: str, b: str) -> float:
    na, nb = _normaliser(a), _normaliser(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    grammes = _ngrammes(a) | _ngrammes(b)
    jaccard = len(_ngrammes(a) & _ngrammes(b)) / len(grammes) if grammes else 0.0
    mots_a, mots_b = set(na.split()), set(nb.split())
    recouvrement = len(mots_a & mots_b) / max(len(mots_a), len(mots_b))
    return round(0.5 * jaccard + 0.5 * recouvrement, 4)


def similarite(a: str, b: str) -> float:
    """Proximité de deux textes, de 0 (rien à voir) à 1 (identiques ou équivalents)."""
    if fournisseur_similarite() == "nle_embedding":
        return round(_similarite_apple(a, b), 4)
    return _similarite_lexicale(a, b)


def proche(reponse: str, attendues: list[str], seuil: float | None = None) -> bool:
    """La réponse est-elle « assez proche » d'une des formulations attendues ?"""
    limite = SEUIL_SIMILARITE if seuil is None else seuil
    return any(similarite(reponse, attendue) >= limite for attendue in attendues if attendue)


# --- Synthèse vocale (voix du système) ----------------------------------------

_SYNTHESE_PLATEFORMES = {
    "Darwin": ("say", "afconvert"),
    "Linux": ("espeak-ng", "espeak"),
    "Windows": (None, None),   # via PowerShell / SAPI
}


def synthese_disponible() -> bool:
    """La voix du système est-elle utilisable depuis ce poste ?"""
    import platform

    if platform.system() == "Windows":
        return shutil.which("powershell") is not None or shutil.which("pwsh") is not None
    if platform.system() == "Darwin":
        return bool(shutil.which("say") and shutil.which("afconvert"))
    for outil in _SYNTHESE_PLATEFORMES.get(platform.system(), (None, None)):
        if outil and shutil.which(outil):
            return True
    return False


def synthese(texte: str) -> tuple[bytes, str] | None:
    """Synthétise ``texte`` avec la voix du système → (octets WAV, mime) ou None."""
    import platform
    import tempfile

    texte = (texte or "").strip()
    if not texte:
        return None
    systeme = platform.system()
    with tempfile.TemporaryDirectory() as dossier:
        brut = Path(dossier) / "voix.aiff"   # « say » ajoute l'extension .aiff
        final = Path(dossier) / "voix.wav"
        # La voix du système peut être lente au premier appel : on retente une fois.
        for tentative in (1, 2):
            try:
                if systeme == "Darwin":
                    subprocess.run(["say", "-o", str(brut), texte], check=True,
                                   capture_output=True, timeout=40)
                    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16",
                                    str(brut), str(final)], check=True,
                                   capture_output=True, timeout=40)
                elif systeme == "Linux":
                    outil = shutil.which("espeak-ng") or shutil.which("espeak")
                    if not outil:
                        return None
                    subprocess.run([outil, "-w", str(final), texte], check=True,
                                   capture_output=True, timeout=40)
                elif systeme == "Windows":
                    import base64
                    import os
                    script = ("Add-Type -AssemblyName System.Speech; "
                              "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                              "$s.SetOutputToWaveFile($env:TTS_OUT); "
                              "$s.Speak([Environment]::GetEnvironmentVariable('TTS_TEXT')); "
                              "$s.Dispose()")
                    exe = shutil.which("powershell") or shutil.which("pwsh")
                    if not exe:
                        return None
                    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
                    subprocess.run([exe, "-NoProfile", "-EncodedCommand", encoded], check=True,
                                   capture_output=True, timeout=60,
                                   env={**os.environ, "TTS_TEXT": texte, "TTS_OUT": str(final)})
                else:
                    return None
                if final.exists() and final.stat().st_size > 0:
                    return final.read_bytes(), "audio/wav"
            except (subprocess.SubprocessError, OSError):
                continue
        return None


# --- État des capacités -------------------------------------------------------


def capacites() -> dict:
    """Ce que ce poste sait faire, et par quel moyen — pour l'interface et le diagnostic."""
    import platform

    return {
        "similarite": {"disponible": True, "fournisseur": fournisseur_similarite(),
                       "seuil": SEUIL_SIMILARITE},
        "synthese": {"disponible": synthese_disponible(), "moyen": "voix du système"},
        "voix": {"disponible": None, "moyen": "client (navigateur ou OS de la tablette)"},
        "plateforme": platform.system(),
        "principe": "local — aucune donnée ne quitte le poste",
    }
