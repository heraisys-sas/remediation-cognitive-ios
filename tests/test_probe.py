"""Régression du défaut d'audit : aucune sélection implicite des tests."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_external_pytest_settings_cannot_filter_probe():
    env = dict(os.environ, PYTHONPATH=str(ROOT / "mobile/ios"),
               PYTEST_ADDOPTS="-k test_adaptive --maxfail=1",
               PYTEST_PLUGINS="un_plugin_qui_ne_doit_pas_etre_charge",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="0")
    result = subprocess.run([sys.executable, "-m", "probe"], cwd=ROOT, env=env,
                            text=True, capture_output=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "60 passed" in result.stdout
    assert "deselected" not in result.stdout
