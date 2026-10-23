"""Identifiants historiques et ressources hors connexion du lot source 0ed9207."""
import hashlib
import json
from pathlib import Path

from mobile.application_runtime import ApplicationRuntime

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'vendor/remediation'


def test_historical_items_are_unchanged_and_exactly_ninety_are_added():
    baseline = json.loads((ROOT / 'tests/fixtures/banques-44acda5.json').read_text())
    added = 0
    for path, old in baseline.items():
        rows = json.loads((VENDOR / path).read_text())
        items = {item['id']: item for item in rows}
        assert len(items) == len(rows)
        for identifier, digest in old.items():
            assert hashlib.sha256(json.dumps(items[identifier], sort_keys=True, ensure_ascii=False).encode()).hexdigest() == digest
        added += len(set(items) - set(old))
    assert added == 90


def test_all_context_images_are_embedded_and_primary_hashes_match():
    scenes = json.loads((VENDOR / 'frontend/images/contextes/manifest.json').read_text())['scenes']
    assert len(scenes) == 20
    for scene in scenes:
        image = scene['image']
        assert hashlib.sha256((VENDOR / 'frontend' / image['src']).read_bytes()).hexdigest() == image['sha256']
        for candidate in image['srcset'].split(','):
            data = (VENDOR / 'frontend' / candidate.strip().split()[0]).read_bytes()
            assert data[:4] == b'RIFF' and data[8:12] == b'WEBP'


def test_enriched_auditory_series_have_all_offline_audio():
    rows = json.loads((VENDOR / 'content/entrainement/series-entendues/paliers/palier-04.json').read_text())
    for item in rows:
        for path in item['contenu']['affichage']['audio'].values():
            assert (VENDOR / 'frontend' / path.removeprefix('/ui/')).stat().st_size > 0


def test_context_bank_twenty_scenes_keeps_session_limit_ten(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    assert len(runtime.manager.contenu.items('evocation', 'memoire-source')) == 20
    session = runtime.manager.demarrer('evocation', parcours='memoire-source')
    assert len(session['items']) == 10
    assert len({item['id'] for item in session['items']}) == 10
