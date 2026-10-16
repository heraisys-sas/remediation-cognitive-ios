"""Génère le pilote autonome à partir du runtime et des dépendances verrouillés."""

import json
from pathlib import Path
import shutil
import plistlib

from prepare_engine_probe import prepare, ROOT
from provenance import tree_hash


def main():
    destination = ROOT / ".local/calculation-pilot"
    prepare(ROOT / ".local/ios-python", destination, ROOT / ".local/locked-wheels")
    app = destination / "iOSTestbed/app"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.sqlite")
    shutil.copytree(ROOT / "vendor", app / "vendor", ignore=ignore)
    shutil.copytree(ROOT / "mobile", app / "mobile", ignore=ignore)
    shutil.copy2(ROOT / "UPSTREAM.json", app / "UPSTREAM.json")
    native = ROOT / "mobile/ios/pilot"
    shutil.copy2(native / "SceneDelegate.m", destination / "iOSTestbed/SceneDelegate.m")
    shutil.copy2(native / "PilotTests.m", destination / "TestbedTests/TestbedTests.m")
    # Réutilise une ressource-folder déjà déclarée dans le projet Xcode.
    pilot = destination / "iOSTestbed/app/pilot"
    pilot.mkdir()
    for name in ("index.html", "pilot.css", "active-clock.js", "pilot.js"):
        shutil.copy2(native / name, pilot / name)
    scene = destination / "iOSTestbed/SceneDelegate.m"
    scene.write_text(scene.read_text().replace('@"pilot" isDirectory:YES', '@"app/pilot" isDirectory:YES'))
    info_path = destination / "iOSTestbed/iOSTestbed-Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    info.update(CFBundleDisplayName="Remédiation", CFBundleDevelopmentRegion="fr",
                CFBundleIdentifier="$(PRODUCT_BUNDLE_IDENTIFIER)")
    info.pop("UIRequiresFullScreen", None)
    info_path.write_bytes(plistlib.dumps(info))
    project = destination / "iOSTestbed.xcodeproj/project.pbxproj"
    project.write_text(project.read_text().replace("org.python.iOSTestbed", "fr.heraisys.remediation.pilot"))
    manifest_path = destination / "probe-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(scope="Calcul mental : service, corrections, SQLite et pont natif ; clavier seulement",
                    app_sha256=tree_hash(app), native_sha256=tree_hash(destination / "iOSTestbed"))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(destination / "iOSTestbed.xcodeproj")


if __name__ == "__main__":
    main()
