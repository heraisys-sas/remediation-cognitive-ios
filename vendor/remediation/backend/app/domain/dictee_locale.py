"""Transcription Apple locale d'un WAV temporaire, sans repli réseau."""
from __future__ import annotations
import base64
import binascii
import io
import json
import platform
import subprocess
import tempfile
import wave
from pathlib import Path

HELPER = Path(__file__).resolve().parents[3] / '.local/bin/dictee-apple'
TRANSCRIPTION_TIMEOUT_SECONDS = 20
MAX_AUDIO_BYTES = 3_000_000
MAX_BASE64_LENGTH = 4 * ((MAX_AUDIO_BYTES + 2) // 3)


def _executer(argument: str, timeout: int) -> dict:
    try:
        resultat = subprocess.run([str(HELPER), argument], capture_output=True,
                                  text=True, check=True, timeout=timeout)
        valeur = json.loads(resultat.stdout)
        if isinstance(valeur, dict):
            return valeur
    except subprocess.TimeoutExpired:
        return {'disponible': False, 'raison': 'transcription_trop_longue'}
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return {'disponible': False, 'raison': 'moteur_indisponible'}


def _installation() -> dict:
    if platform.system() != 'Darwin':
        return {'disponible': False, 'raison': 'macos_requis'}
    if not HELPER.is_file():
        return {'disponible': False, 'raison': 'adaptateur_non_installe'}
    return {'disponible': True}


def etat() -> dict:
    installation = _installation()
    return _executer('--status', 10) if installation['disponible'] else installation


def decoder_wav(audio_base64: str) -> bytes:
    """PCM16 mono, 8–48 kHz, au plus 60 s ; aucune réponse attendue transmise."""
    if len(audio_base64) > MAX_BASE64_LENGTH:
        raise ValueError('audio_trop_long')
    try:
        audio = base64.b64decode(audio_base64, validate=True)
        if not audio or len(audio) > MAX_AUDIO_BYTES:
            raise ValueError('audio_trop_long')
        with wave.open(io.BytesIO(audio), 'rb') as wav:
            frames, rate = wav.getnframes(), wav.getframerate()
            if (wav.getnchannels() != 1 or wav.getsampwidth() != 2
                    or wav.getcomptype() != 'NONE' or not 8000 <= rate <= 48000
                    or not 0 < frames <= rate * 60):
                raise ValueError('format_audio_invalide')
            if len(wav.readframes(frames)) != frames * 2:
                raise ValueError('audio_tronque')
        return audio
    except (binascii.Error, wave.Error, EOFError) as exc:
        raise ValueError('format_audio_invalide') from exc


def transcrire(audio_base64: str) -> dict:
    audio = decoder_wav(audio_base64)
    # Le helper vérifie les ressources lui-même : un second lancement --status
    # à chaque fragment audio ajoute un aller-retour inutile.
    disponibilite = _installation()
    if not disponibilite.get('disponible'):
        return disponibilite
    with tempfile.TemporaryDirectory(prefix='remediation-dictee-') as dossier:
        fichier = Path(dossier) / 'parole.wav'
        fichier.write_bytes(audio)
        resultat = _executer(str(fichier), TRANSCRIPTION_TIMEOUT_SECONDS)
    if resultat.get('disponible') and isinstance(resultat.get('texte'), str):
        texte = resultat['texte'].strip()
        if not texte:
            return {'disponible': False, 'raison': 'parole_non_detectee'}
        return {'disponible': True, 'texte': texte, 'fournisseur': 'apple_speech_local'}
    return {'disponible': False, 'raison': resultat.get('raison', 'transcription_echouee')}
