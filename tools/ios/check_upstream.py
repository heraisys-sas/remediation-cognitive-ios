"""Vérifie que le moteur importé correspond à sa référence enregistrée."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
lock = json.loads((ROOT / "UPSTREAM.json").read_text())
actual = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
          for path in sorted((ROOT / "engine").rglob("*.py"))}
if actual != lock["sha256"]:
    raise SystemExit("Moteur modifié : documenter le portage et actualiser UPSTREAM.json après revue")
if "vendor_sha256" in lock:
    vendor = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted((ROOT / "vendor/remediation").rglob("*"))
              if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    if vendor != lock["vendor_sha256"]:
        raise SystemExit("Le service ou le contenu importé diffère de la référence enregistrée")
print(f"Moteur conforme à {lock['commit']}")
