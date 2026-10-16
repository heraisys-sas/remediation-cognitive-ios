"""Exécute le banc verrouillé sur un vrai runtime simulateur déjà installé."""

import argparse
import json
from pathlib import Path
import platform
import plistlib
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("iPhone 17", "iPhone Air"), default="iPhone 17")
    parser.add_argument("--probe", type=Path, default=ROOT / ".local/engine-ios-locked")
    args = parser.parse_args()
    runtimes = json.loads(subprocess.check_output(
        ["xcrun", "simctl", "list", "runtimes", "--json"], text=True))["runtimes"]
    compatible = [r for r in runtimes if r.get("isAvailable") and
                  r["identifier"].startswith("com.apple.CoreSimulator.SimRuntime.iOS-") and
                  int(r["version"].split(".")[0]) >= 26]
    if not compatible:
        raise SystemExit("Aucun runtime iOS 26+ installé ; exécution impossible, compilation seule insuffisante")
    runtime = max(compatible, key=lambda r: tuple(map(int, r["version"].split("."))))
    device_id = subprocess.check_output([
        "xcrun", "simctl", "create", "Remediation Probe " + args.device,
        "com.apple.CoreSimulator.SimDeviceType." + args.device.replace(" ", "-"),
        runtime["identifier"],
    ], text=True).strip()
    local = ROOT / ".local"
    result = local / ("probe-" + device_id + ".xcresult")
    log = local / ("probe-" + device_id + ".log")
    try:
        with log.open("w") as output:
            execution = subprocess.run([
                "xcodebuild", "test", "-project", str(args.probe / "iOSTestbed.xcodeproj"),
                "-scheme", "iOSTestbed", "-destination", "id=" + device_id,
                "-derivedDataPath", str(local / "ios-derived"),
                "-resultBundlePath", str(result), "-parallel-testing-enabled", "NO",
                "ARCHS=" + ("arm64" if platform.machine() == "arm64" else "x86_64"),
                "IPHONEOS_DEPLOYMENT_TARGET=26.0", "CODE_SIGNING_ALLOWED=NO",
                "EXPANDED_CODE_SIGN_IDENTITY=-",
            ], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, timeout=1200)
        if execution.returncode:
            print(log.read_text()[-16000:])
            raise SystemExit(execution.returncode)
        if args.probe.name == "calculation-pilot":
            app = local / "ios-derived/Build/Products/Debug-iphonesimulator/iOSTestbed.app"
            bundle = plistlib.loads((app / "Info.plist").read_bytes())["CFBundleIdentifier"]
            # XCTest peut utiliser un clone puis arrêter la destination demandée.
            # La capture est une étape distincte : démarrer et installer explicitement.
            devices = json.loads(subprocess.check_output(
                ["xcrun", "simctl", "list", "devices", "--json"], text=True))["devices"]
            selected = next(d for group in devices.values() for d in group if d["udid"] == device_id)
            if selected["state"] == "Shutdown":
                subprocess.run(["xcrun", "simctl", "boot", device_id], check=True, timeout=60)
            subprocess.run(["xcrun", "simctl", "bootstatus", device_id, "-b"], check=True, timeout=180)
            subprocess.run(["xcrun", "simctl", "install", device_id, str(app)], check=True, timeout=60)
            subprocess.run(["xcrun", "simctl", "launch", device_id, bundle], check=True)
            time.sleep(3)
            subprocess.run(["xcrun", "simctl", "io", device_id, "screenshot",
                            str(local / ("pilot-" + device_id + ".png"))], check=True)
        # XCTest impose les invariants de la sonde ou ceux du parcours pilote.
        print(json.dumps({"device": args.device, "runtime": {k: runtime[k] for k in ("identifier", "version", "buildversion")},
                          "result_bundle": str(result), "log": str(log), "xctest_exit_code": 0}))
    finally:
        subprocess.run(["xcrun", "simctl", "shutdown", device_id], capture_output=True)
        subprocess.run(["xcrun", "simctl", "delete", device_id], capture_output=True)


if __name__ == "__main__":
    main()
