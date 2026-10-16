"""Prépare une app XCTest avec le vrai moteur, sans serveur ni données personnelles.

Le runtime externe reste dans .local ; aucune modification des installations Apple.
Exécuter avec le Python de développement équipé de pytest et fsrs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from provenance import file_hash, tree_hash

ROOT = Path(__file__).resolve().parents[2]



def prepare(support: Path, destination: Path, wheels: Path) -> None:
    support = support.resolve()
    destination = destination.resolve()
    # Pas d'écrasement d'une app précédente, ni copie d'un checkout utilisateur.
    if destination.exists():
        raise ValueError(f"Destination déjà présente : {destination}")
    if not destination.is_relative_to(ROOT / ".local"):
        raise ValueError("La destination doit être dans .local de ce checkout")
    framework = support / "Python.xcframework"
    testbed = support / "testbed"
    if not framework.is_dir() or not (testbed / "__main__.py").is_file():
        raise ValueError("Distribution iOS Python/BeeWare incomplète")
    lock = json.loads((ROOT / "mobile/ios/probe-lock.json").read_text())
    if tree_hash(support) != lock["runtime"]["tree_sha256"]:
        raise ValueError("Le runtime extrait ne correspond pas à la référence verrouillée")
    # Vérifier toutes les entrées avant de créer un projet partiel.
    for wheel in lock["wheels"]:
        archive = wheels / wheel["filename"]
        if not archive.is_file() or file_hash(archive) != wheel["sha256"]:
            raise ValueError(f"Wheel absent ou modifié : {archive}")
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                path = Path(name)
                if path.is_absolute() or ".." in path.parts or "\\" in name:
                    raise ValueError(f"Chemin de wheel invalide : {name}")
                if path.suffix in {".so", ".dylib", ".pyd"}:
                    raise ValueError(f"Extension binaire non portable : {name}")
    subprocess.run(
        [sys.executable, str(testbed), "clone", "--platform", "iOS",
         "--framework", str(framework), str(destination)], check=True,
    )
    app = destination / "iOSTestbed" / "app"
    packages = destination / "iOSTestbed" / "app_packages"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "engine", app / "engine", ignore=ignore)
    shutil.copytree(ROOT / "mobile" / "ios" / "probe", app / "ios_probe", ignore=ignore)
    for wheel in lock["wheels"]:
        with zipfile.ZipFile(wheels / wheel["filename"]) as bundle:
            bundle.extractall(packages)
    plan_path = destination / "iOSTestbed.xctestplan"
    plan = json.loads(plan_path.read_text())
    plan["defaultOptions"]["commandLineArgumentEntries"] = [{"argument": "ios_probe"}]
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    manifest = {
        "schema": 2, "dependencies": lock["wheels"],
        "runtime_source": lock["runtime"],
        "app_sha256": tree_hash(app), "packages_sha256": tree_hash(packages),
        "upstream": json.loads((ROOT / "UPSTREAM.json").read_text()),
        "runtime": (support / "VERSIONS").read_text(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip(),
        "scope": "engine/tests only; no backend, content or personal data",
    }
    (destination / "probe-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Projet prêt : {destination / 'iOSTestbed.xcodeproj'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support", type=Path, required=True)
    parser.add_argument("--destination", type=Path, default=ROOT / ".local" / "engine-ios-probe")
    parser.add_argument("--wheels", type=Path, default=ROOT / ".local/locked-wheels")
    args = parser.parse_args()
    prepare(args.support, args.destination, args.wheels)
