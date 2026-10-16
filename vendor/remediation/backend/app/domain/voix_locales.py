"""Voix françaises macOS de qualité supérieure, accessibles même hors Web Speech."""
import platform
import subprocess
import tempfile
from pathlib import Path


def voix_disponibles():
    if platform.system() != 'Darwin':
        return []
    try:
        sortie = subprocess.run(['say', '-v', '?'], capture_output=True, text=True, check=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    voix = []
    for ligne in sortie.splitlines():
        if 'fr_FR' not in ligne:
            continue
        nom = ligne.split('fr_FR', 1)[0].strip()
        if any(qualite in nom for qualite in ('Premium', 'Enhanced')):
            voix.append({'id': nom, 'nom': nom.replace('(Premium)', '(haute qualité)').replace('(Enhanced)', '(améliorée)')})
    return voix


def synthetiser(texte, voix):
    if voix not in {v['id'] for v in voix_disponibles()}:
        return None
    try:
        with tempfile.TemporaryDirectory() as dossier:
            brut, final = Path(dossier)/'voix.aiff', Path(dossier)/'voix.wav'
            subprocess.run(['say', '-v', voix, '-o', str(brut), '--', texte], check=True, capture_output=True, timeout=40)
            subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16', str(brut), str(final)], check=True, capture_output=True, timeout=40)
            return final.read_bytes(), 'audio/wav'
    except (OSError, subprocess.SubprocessError):
        return None
