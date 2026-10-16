"""Même suite moteur sur ordinateur et dans le processus de l'app iOS."""

import json
import os
from pathlib import Path
import sys

import engine
import pytest


class FullSuite:
    """Refuse une preuve vide, filtrée ou partiellement ignorée."""

    def __init__(self):
        self.passed = 0
        self.collected = 0

    def pytest_runtest_logreport(self, report):
        if report.when == "call" and report.passed:
            self.passed += 1

    def pytest_sessionfinish(self, session):
        self.collected = session.testscollected


def main() -> int:
    # Ne laisser aucun réglage pytest du poste filtrer les tests ou injecter un plugin.
    for name in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        os.environ.pop(name, None)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    print(json.dumps({"platform": sys.platform, "python": sys.version,
                      "network_required": False, "http_server": False}), flush=True)
    tests = Path(engine.__file__).parent / "tests"
    # Pas de plugins du poste, de cache dans le bundle signé ou de données réelles.
    suite = FullSuite()
    result = int(pytest.main([str(tests), "-q", "-p", "no:cacheprovider",
                             "-c", os.devnull, "--import-mode=importlib"], plugins=[suite]))
    # Lié au lot de tests importé ; actualiser explicitement lors d'un portage amont.
    if suite.collected != 60 or suite.passed != 60:
        result = 1
    print("PROBE_RESULT=" + json.dumps({"platform": sys.platform,
          "collected": suite.collected, "passed": suite.passed, "exit_code": result}), flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
