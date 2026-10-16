"""Télécharge et vérifie le runtime verrouillé, uniquement dans .local."""

import json
from pathlib import Path
import tarfile
import urllib.request

from provenance import file_hash, tree_hash

ROOT = Path(__file__).resolve().parents[2]


def main():
    lock = json.loads((ROOT / "mobile/ios/probe-lock.json").read_text())["runtime"]
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    support = local / "ios-python"
    if support.exists():
        if tree_hash(support) != lock["tree_sha256"]:
            raise ValueError("Le runtime existant diffère du verrou ; aucun écrasement")
        return
    archive = local / "python-ios-support.tar.gz"
    if not archive.exists():
        with urllib.request.urlopen(lock["url"], timeout=120) as source, archive.open("xb") as target:
            while block := source.read(1024 * 1024):
                target.write(block)
    if file_hash(archive) != lock["archive_sha256"]:
        raise ValueError("Archive Python modifiée ou incomplète")
    with tarfile.open(archive) as bundle:
        bundle.extractall(support, filter="data")
    if tree_hash(support) != lock["tree_sha256"]:
        raise ValueError("L'arbre extrait ne correspond pas au verrou")


if __name__ == "__main__":
    main()
