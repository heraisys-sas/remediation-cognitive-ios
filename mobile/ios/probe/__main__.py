"""Même suite moteur sur ordinateur et dans le processus de l'app iOS."""

import json
from pathlib import Path
import sys

import engine
import pytest


def main() -> int:
    print(json.dumps({"platform": sys.platform, "python": sys.version,
                      "network_required": False, "http_server": False}), flush=True)
    tests = Path(engine.__file__).parent / "tests"
    # Pas de plugins du poste, de cache dans le bundle signé ou de données réelles.
    return pytest.main([str(tests), "-q", "-p", "no:cacheprovider",
                        "--override-ini", "addopts=", "--import-mode=importlib"])


if __name__ == "__main__":
    raise SystemExit(main())
