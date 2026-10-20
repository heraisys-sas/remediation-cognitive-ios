"""Parité mémoire visuelle, frontière du rappel et transitions transactionnelles."""
import json
from datetime import datetime, timezone

import pytest
from mobile.application_runtime import ApplicationRuntime
from mobile.memory_runtime import MEMORY_ACTIVITIES, presentation
from backend.app.api.entrainement.service import GestionnaireSessions
from backend.app.storage.store import StockageJSON
from engine.session.runner import SessionRunner


def call(runtime, action, **kwargs):
    return json.loads(runtime.call(json.dumps({"action": action, **kwargs})))


def step(runtime, operation, answer=None, elapsed=0):
    view=call(runtime,"view")
    return call(runtime,"memory-step",session_id=view["session_id"],item_id=view["item"]["id"],
                revision=view["memory"]["revision"],operation=operation,answer=answer,elapsed_ms=elapsed)


def encode(runtime):
    view=step(runtime,"show")
    while view["memory"]["phase"]!="question":
        view=step(runtime,"advance",elapsed=view["memory"]["remaining_ms"])
    return view


@pytest.mark.parametrize("activity",[key for key,value in MEMORY_ACTIVITIES.items() if value[0]=="memoire"])
def test_memory_matches_source_answers_reprises_and_progress(tmp_path,monkeypatch,activity):
    now=datetime.now(timezone.utc)
    original=GestionnaireSessions.__init__
    def fixed(self,*args,**kwargs):
        original(self,*args,**kwargs); self.horloge=lambda:now
    monkeypatch.setattr(GestionnaireSessions,"__init__",fixed)
    # Le résumé du runner lit sa propre horloge, distincte de celle du service.
    # Neutraliser uniquement ce temps mural dans la comparaison de parité.
    monkeypatch.setattr(SessionRunner,"_secondes_ecoulees",lambda self: 0.0)
    runtime=ApplicationRuntime(str(tmp_path/'mobile'))
    source=GestionnaireSessions(stockage=StockageJSON(tmp_path/'source'))
    actual=call(runtime,"start",activity=activity)
    expected=source.demarrer('memoire',parcours=activity)
    assert [i['id'] for i in actual['items']]==[i['id'] for i in expected['items']]
    assert 'affichage' not in json.dumps(actual)
    assert all('reponse' not in i for i in actual['items'])
    answers={i['id']:i['reponse']['valeur'] for i in source.contenu.items('memoire',activity)}
    for index,item in enumerate(expected['items']):
        ready=call(runtime,'view')
        assert ready['memory']['phase']=='pret'
        assert item['contenu']['enonce'] not in json.dumps(ready,ensure_ascii=False)
        view=encode(runtime)
        assert view['memory']['question']==item['contenu']['enonce']
        assert 'content' not in view['memory'] and 'affichage' not in json.dumps(view)
        answer=str(answers[item['id']]) if index%2 else 'inconnu'
        result=step(runtime,'answer',answer,1500)
        reference=source.repondre('memoire',expected['session_id'],item['id'],answer,1500)
        assert result['feedback']==reference
        call(runtime,'next')
    view=call(runtime,'view')
    while view.get('item'):
        assert view['reprise'] and view['memory']['phase']=='question'
        item_id=view['item']['id']
        assert view['reprise_attendue']==answers[item_id]
        result=step(runtime,'answer',str(answers[item_id]),1200)
        reference=source.repondre('memoire',expected['session_id'],item_id,str(answers[item_id]),1200)
        assert result['feedback']==reference
        view=call(runtime,'next')
    actual_summary=call(runtime,'finish',session_id=actual['session_id'])
    expected_summary=source.terminer('memoire',expected['session_id'])
    assert actual_summary['resume']==expected_summary['resume']
    key=f'memoire--{activity}'
    assert runtime.store.lire_maitrise(key)==source.stockage.lire_maitrise(key)
    assert runtime.store.lire_temps_reference(key)==source.stockage.lire_temps_reference(key)
    for item_id,card in runtime.store.lire_cartes(key).items():
        other=source.stockage.lire_cartes(key)[item_id]
        assert (card.echeance,card.stabilite,card.difficulte)==(other.echeance,other.stabilite,other.difficulte)
    assert call(runtime,'finish',session_id=actual['session_id'])==actual_summary
    assert not runtime.store.lire_cartes('calcul-mental')


def test_timeline_matches_source_element_and_blank_durations():
    item={'contenu':{'affichage':{'mode':'sequence','elements':['4','0','9'],'duree_par_item_ms':2000,'pause_item_ms':2000}}}
    events=presentation(item)
    assert [event['phase'] for event in events]==['element','blanc','element','blanc','element','blanc']
    assert [event['content'] for event in events if 'content' in event]==['4','0','9']
    assert sum(e['duration_ms'] for e in events)==12000
    del item['contenu']['affichage']['pause_item_ms']
    events=presentation(item)
    assert len(events)==5 and sum(e['duration_ms'] for e in events)==10000


def test_interruption_retains_current_stage_without_redisplaying_previous_elements(tmp_path):
    runtime=ApplicationRuntime(str(tmp_path))
    call(runtime,'start',activity='chiffres-endroit')
    first=step(runtime,'show')
    assert first['memory']['position']==1
    partial=step(runtime,'advance',elapsed=500)
    assert partial['memory']['position']==1 and partial['memory']['remaining_ms']==1500
    step(runtime,'pause',elapsed=250)
    restored=ApplicationRuntime(str(tmp_path))
    paused=call(restored,'view')
    assert paused['memory']['paused'] and 'content' not in paused['memory']
    resumed=step(restored,'resume',elapsed=900000)
    assert resumed['memory']['remaining_ms']==1250
    blank=step(restored,'advance',elapsed=1250)
    assert blank['memory']['phase']=='blanc' and 'content' not in blank['memory']
    second=step(restored,'advance',elapsed=2000)
    assert second['memory']['position']==2
    relaunched=ApplicationRuntime(str(tmp_path))
    assert call(relaunched,'view')['memory']['paused']
    resumed=step(relaunched,'resume')
    assert resumed['memory']['position']==2
    assert resumed['memory']['interruptions']==2
    assert not relaunched.store.lire_cartes('memoire--chiffres-endroit')


def test_recall_pause_and_lost_native_response_preserve_first_answer_and_active_time(tmp_path):
    runtime=ApplicationRuntime(str(tmp_path))
    call(runtime,'start',activity='associations')
    encode(runtime)
    step(runtime,'pause',elapsed=1000)
    restored=ApplicationRuntime(str(tmp_path))
    step(restored,'resume',elapsed=900000)
    view=call(restored,'view')
    item_id=view['item']['id']
    expected=restored._session().items_par_id[item_id]['reponse']['valeur']
    payload=dict(session_id=view['session_id'],item_id=item_id,revision=view['memory']['revision'],
                 operation='answer',answer=str(expected),elapsed_ms=500)
    actual=call(restored,'memory-step',**payload)
    payload['elapsed_ms']=9999
    assert call(restored,'memory-step',**payload)==actual
    assert restored._session().temps_reference==[1500.0]
    with pytest.raises(ValueError):
        step(restored,'answer','faux',100)
    assert restored._session().reponses[item_id]


def test_memory_stage_guards_rollback_and_early_finish(tmp_path,monkeypatch):
    runtime=ApplicationRuntime(str(tmp_path))
    session=call(runtime,'start',activity='mots')
    with pytest.raises(ValueError):
        step(runtime,'answer','chat')
    with pytest.raises(ValueError):
        call(runtime,'answer',session_id=session['session_id'],item_id=session['items'][0]['id'],answer='chat',elapsed_ms=1000)
    before=call(runtime,'view')
    original=runtime.store._ecrire_json
    def fail(path,value):
        if path==runtime.checkpoint: raise OSError('stockage indisponible')
        return original(path,value)
    monkeypatch.setattr(runtime.store,'_ecrire_json',fail)
    with pytest.raises(OSError):
        call(runtime,'memory-step',session_id=before['session_id'],item_id=before['item']['id'],
             revision=before['memory']['revision'],operation='show',elapsed_ms=0)
    monkeypatch.setattr(runtime.store,'_ecrire_json',original)
    assert call(runtime,'view')==before
    step(runtime,'show')
    step(runtime,'skip')
    assert call(runtime,'view')['memory']['skipped']
    summary=call(runtime,'finish',session_id=session['session_id'])
    assert summary['resume']['items']==0
    assert not runtime.store.lire_cartes('memoire--mots')


def test_empty_memory_session_can_close_and_restore(tmp_path,monkeypatch):
    original=GestionnaireSessions.demarrer
    def empty(self,*args,**kwargs):
        result=original(self,*args,**kwargs);result['items']=[];return result
    monkeypatch.setattr(GestionnaireSessions,'demarrer',empty)
    runtime=ApplicationRuntime(str(tmp_path))
    session=call(runtime,'start',activity='position')
    assert call(runtime,'view')['item'] is None
    restored=ApplicationRuntime(str(tmp_path))
    assert call(restored,'view')['item'] is None
    assert call(restored,'finish',session_id=session['session_id'])['resume']['items']==0
