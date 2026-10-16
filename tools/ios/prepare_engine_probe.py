"""Prépare une app XCTest avec le vrai moteur, sans serveur ni données personnelles.

Le runtime externe reste dans .local ; aucune modification des installations Apple.
Exécuter avec le Python de développement équipé de pytest et fsrs.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MODULES = {
    "fsrs": "fsrs",
    "typing_extensions": "typing_extensions",
    "pytest": "pytest",
    "_pytest": "pytest",
    "pluggy": "pluggy",
    "iniconfig": "iniconfig",
    "packaging": "packaging",
    "pygments": "Pygments",
}


def prepare(support: Path, destination: Path) -> None:
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
    specs = {name: importlib.util.find_spec(name) for name in MODULES}
    if any(spec is None or spec.origin is None for spec in specs.values()):
        raise ValueError("Installer les dépendances de développement dans un venv séparé")
    if importlib.metadata.version("fsrs").split(".")[0] != "6":
        raise ValueError("Ce moteur exige FSRS 6")
    subprocess.run(
        [sys.executable, str(testbed), "clone", "--platform", "iOS",
         "--framework", str(framework), str(destination)], check=True,
    )
    app = destination / "iOSTestbed" / "app"
    packages = destination / "iOSTestbed" / "app_packages"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "engine", app / "engine", ignore=ignore)
    shutil.copytree(ROOT / "mobile" / "ios" / "probe", app / "ios_probe", ignore=ignore)
    versions = {}
    for name, distribution in MODULES.items():
        spec = specs[name]
        source = Path(spec.origin)
        if spec.submodule_search_locations:
            shutil.copytree(source.parent, packages / name, ignore=ignore)
        else:
            shutil.copy2(source, packages / source.name)
        dist = importlib.metadata.distribution(distribution)
        versions[distribution] = dist.version
        # Conserver licences et métadonnées nécessaires aux imports.
        for entry in dist.files or []:
            if ".dist-info" in entry.parts[0] and ".." not in entry.parts:
                target = packages / entry
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dist.locate_file(entry), target)
    binaries = [path for path in packages.rglob("*") if path.suffix in {".so", ".dylib"}]
    if binaries:
        raise ValueError(f"Dépendances non portables à empaqueter : {binaries}")
    plan_path = destination / "iOSTestbed.xctestplan"
    plan = json.loads(plan_path.read_text())
    plan["defaultOptions"]["commandLineArgumentEntries"] = [{"argument": "ios_probe"}]
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    manifest = {
        "schema": 1, "dependencies": versions,
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
    args = parser.parse_args()
    prepare(args.support, args.destination)
