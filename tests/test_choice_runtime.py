"""Parité stratégie : second essai, réponses et progression sans service web."""
import json
from datetime import datetime, timezone
import pytest
from mobile.application_runtime import ApplicationRuntime
from mobile.choice_runtime import CHOICE_ACTIVITIES
from backend.app.api.entrainement.service import GestionnaireSessions
from backend.app.storage.store import StockageJSON


def call(runtime, action, **kwargs):
    return json.loads(runtime.call(json.dumps({"action":action, **kwargs})))


def answer(runtime, value, elapsed=1000):
    view=call(runtime,"view")
    return call(runtime,"choice-answer",session_id=view["session_id"],item_id=view["item"]["id"],
                revision=view["choice_revision"],answer=value,elapsed_ms=elapsed)


@pytest.mark.parametrize("activity",CHOICE_ACTIVITIES)
def test_strategy_matches_source_including_second_attempt_and_cards(tmp_path,monkeypatch,activity):
    now=datetime.now(timezone.utc)
    original=GestionnaireSessions.__init__
    def fixed(self,*args,**kwargs):
        original(self,*args,**kwargs); self.horloge=lambda:now
    monkeypatch.setattr(GestionnaireSessions,"__init__",fixed)
    runtime=ApplicationRuntime(str(tmp_path/'mobile'))
    source=GestionnaireSessions(stockage=StockageJSON(tmp_path/'source'))
    session=call(runtime,"start",activity=activity)
    theme,parcours,_=CHOICE_ACTIVITIES[activity]
    reference=source.demarrer(theme,parcours=parcours)
    assert session['items']==reference['items']
    answers={i['id']:i['reponse']['valeur'] for i in source.contenu.items(theme,parcours)}
    # Une erreur et une réussite dès le premier essai, puis deux erreurs :
    # couvre aussi les reprises ajoutées à la fin par le service source.
    for index,item in enumerate(session['items']):
        correct=answers[item['id']]
        wrong=next(o for o in item['contenu']['options'] if o!=correct)
        first=correct if index%3==1 else wrong
        result=answer(runtime,first)
        expected=source.repondre(theme,reference['session_id'],item['id'],first,1000)
        if expected.get('essai_supplementaire'):
            assert not result['feedback'] and result['retry_feedback']==expected['feedback']
            assert not runtime._session().reponses.get(item['id'])
            assert expected['attendue'] is None
            second=correct if index%3==0 else wrong
            result=answer(runtime,second,1500)
            expected=source.repondre(theme,reference['session_id'],item['id'],second,2500)
        assert result['feedback']==expected
        call(runtime,'next')
    view=call(runtime,'view')
    while view.get('item'):
        item=view['item']; correct=answers[item['id']]
        assert view['reprise_attendue']==correct
        actual=answer(runtime,correct)['feedback']
        expected=source.repondre(theme,reference['session_id'],item['id'],correct,1000)
        assert actual==expected
        view=call(runtime,'next')
    actual=call(runtime,'finish',session_id=session['session_id'])
    expected=source.terminer(theme,reference['session_id'])
    assert actual['resume']==expected['resume']
    key=f'{theme}--{parcours}'
    assert runtime.store.lire_maitrise(key)==source.stockage.lire_maitrise(key)
    assert runtime.store.lire_temps_reference(key)==source.stockage.lire_temps_reference(key)
    for item_id,card in runtime.store.lire_cartes(key).items():
        other=source.stockage.lire_cartes(key)[item_id]
        assert (card.echeance,card.stabilite,card.difficulte)==(other.echeance,other.stabilite,other.difficulte)
    assert not runtime.store.lire_cartes('methodes--pqrst-guide')


def test_retry_survives_restart_and_lost_response_does_not_consume_second_attempt(tmp_path):
    runtime=ApplicationRuntime(str(tmp_path))
    session=call(runtime,'start',activity='choisir-plan')
    item=session['items'][0]
    correct=runtime._session().items_par_id[item['id']]['reponse']['valeur']
    wrong=next(o for o in item['contenu']['options'] if o!=correct)
    payload=dict(session_id=session['session_id'],item_id=item['id'],revision=0,answer=wrong,elapsed_ms=1000)
    first=call(runtime,'choice-answer',**payload)
    restored=ApplicationRuntime(str(tmp_path))
    payload['elapsed_ms']=15000
    assert call(restored,'choice-answer',**payload)==first
    assert restored._session().essais[item['id']]==1
    assert item['id'] not in restored._session().reponses
    second=answer(restored,correct,500)
    assert second['feedback']['correcte']
    assert restored._session().temps_reference==[1500.0]
    with pytest.raises(ValueError):
        answer(restored,wrong)
    assert call(restored,'view')['feedback']['correcte']


def test_strategy_guards_and_rollback(tmp_path,monkeypatch):
    runtime=ApplicationRuntime(str(tmp_path))
    session=call(runtime,'start',activity='verifier-plan')
    item=session['items'][0]
    with pytest.raises(ValueError):
        answer(runtime,'réponse inventée')
    with pytest.raises(ValueError):
        call(runtime,'answer',session_id=session['session_id'],item_id=item['id'],answer='x',elapsed_ms=1000)
    original=runtime.store._ecrire_json
    def fail(path,value):
        if path==runtime.checkpoint: raise OSError('disque indisponible')
        return original(path,value)
    view=call(runtime,'view')
    monkeypatch.setattr(runtime.store,'_ecrire_json',fail)
    with pytest.raises(OSError):
        call(runtime,'choice-answer',session_id=session['session_id'],item_id=item['id'],revision=0,
             answer=item['contenu']['options'][0],elapsed_ms=1000)
    monkeypatch.setattr(runtime.store,'_ecrire_json',original)
    assert call(runtime,'view')==view
    assert not runtime._session().essais
