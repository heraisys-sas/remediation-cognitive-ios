import pytest
from mobile.application_runtime import ApplicationRuntime
from mobile.input_hints import answer_inputmode


@pytest.mark.parametrize('kind,value,mode', [
    ('production', 3.5, 'decimal'), ('production', -2, 'text'),
    ('production', 'went', 'text'), ('prediction-sortie', 10, 'decimal'),
    ('prediction-sortie', 'abc', 'text'), ('prise-message', 'deux', 'numeric'),
    ('prise-message', '14 h 30', 'text'), ('prise-message', 'le 3 du mois prochain', 'text'),
    ('estimation-temps', 15, 'decimal'), ('empan', '0071', 'numeric'),
    ('paires-associatives', '73', 'numeric'), ('empan-mots', 'chat feuille', 'text'),
])
def test_keyboard_preserves_codes_and_text_formats(kind, value, mode):
    assert answer_inputmode({'type': kind, 'reponse': {'valeur': value}}) == mode


def test_numeric_hint_does_not_reveal_expected_answer(tmp_path):
    import json
    runtime = ApplicationRuntime(str(tmp_path))
    runtime.call(json.dumps({'action': 'start', 'activity': 'calcul-mental'}))
    view = json.loads(runtime.call(json.dumps({'action': 'view'})))
    assert view['inputmode'] == 'decimal'
    assert 'reponse' not in view['item']
    assert 'attendue' not in view
