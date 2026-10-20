"""Les nouveaux adaptateurs doivent exercer le service réel et la sauvegarde SQLite."""
import json
import pytest
from mobile.application_runtime import ApplicationRuntime


def call(runtime,action,**kwargs):
    return json.loads(runtime.call(json.dumps(dict(action=action,**kwargs))))


@pytest.mark.parametrize('activity',['strategie-semantique','strategie-phonologique'])
def test_real_lexical_strategy_notes_do_not_score_and_final_word_does(tmp_path,activity):
    r=ApplicationRuntime(str(tmp_path));s=call(r,'start',activity=activity)
    item_id=s['items'][0]['id'];item=r._session().items_par_id[item_id]
    args=dict(session_id=s['session_id'],item_id=item_id)
    for _ in item['contenu']['etapes']:
        view=call(r,'view');assert view['feedback'] is None
        view=call(r,'lexical-strategy-step',**args,revision=view['lexical_strategy']['revision'],operation='note',value='note personnelle non notée',elapsed_ms=100)
    restored=ApplicationRuntime(str(tmp_path));view=call(restored,'view')
    assert view['lexical_strategy']['paused']
    view=call(restored,'lexical-strategy-step',**args,revision=view['lexical_strategy']['revision'],operation='resume',elapsed_ms=0)
    view=call(restored,'lexical-strategy-step',**args,revision=view['lexical_strategy']['revision'],operation='answer',value=item['reponse']['valeur'],elapsed_ms=100)
    assert view['feedback']['correcte']
    assert call(restored,'next')['lexical_strategy']['phase']=='notes'


def test_real_actualiser_masks_messages_and_uses_structured_source_answer(tmp_path):
    r=ApplicationRuntime(str(tmp_path));s=call(r,'start',activity='actualiser-consigne')
    item_id=s['items'][0]['id'];item=r._session().items_par_id[item_id]
    assert 'etapes' not in s['items'][0]['contenu']
    args=dict(session_id=s['session_id'],item_id=item_id)
    for _ in item['contenu']['etapes']:
        view=call(r,'view');view=call(r,'functional-step',**args,revision=view['functional']['revision'],operation='next',elapsed_ms=100)
    assert 'etape' not in view['functional']
    assert 'etat_initial' not in json.dumps(view)
    view=call(r,'functional-step',**args,revision=view['functional']['revision'],operation='submit',answer=item['reponse']['valeur'],elapsed_ms=100)
    assert view['feedback']['correcte']

from mobile.application_runtime import ACTIVITIES
from mobile.memory_runtime import MEMORY_ACTIVITIES, presentation
from backend.app.api.entrainement.service import GestionnaireSessions
from backend.app.storage.store import StockageJSON
from datetime import datetime, timezone


@pytest.mark.parametrize('activity',list(ACTIVITIES))
def test_every_classic_card_starts_with_real_source_content(tmp_path,activity):
    r=ApplicationRuntime(str(tmp_path));s=call(r,'start',activity=activity);v=call(r,'view')
    assert s['items'] and v['activity']==activity and v['item']
    def keys(value):
        if isinstance(value,dict):
            assert 'reponse' not in value
            for child in value.values():keys(child)
        elif isinstance(value,list):
            for child in value:keys(child)
    keys(s);keys(v)


@pytest.mark.parametrize('activity',[key for key in MEMORY_ACTIVITIES if key.startswith('series-') or key in ('pqrst-rappel','quotidien')])
def test_new_presentations_keep_source_correction_and_progress(tmp_path,monkeypatch,activity):
    instant=datetime.now(timezone.utc);original=GestionnaireSessions.__init__
    def fixed(self,*a,**kw):original(self,*a,**kw);self.horloge=lambda:instant
    monkeypatch.setattr(GestionnaireSessions,'__init__',fixed)
    r=ApplicationRuntime(str(tmp_path/'ios'));reference=GestionnaireSessions(stockage=StockageJSON(tmp_path/'source'))
    theme,path,_=ACTIVITIES[activity];s=call(r,'start',activity=activity);ref=reference.demarrer(theme,parcours=path)
    assert [i['id'] for i in s['items']]==[i['id'] for i in ref['items']]
    v=call(r,'view');raw=r._session().items_par_id[v['item']['id']]
    args=dict(session_id=v['session_id'],item_id=v['item']['id'])
    if v['memory']['phase']=='pret':v=call(r,'memory-step',**args,revision=v['memory']['revision'],operation='show',elapsed_ms=0)
    seen=[]
    while v['memory']['phase']!='question':
        seen.append(v['memory']['phase'])
        if v['memory']['phase']=='audio':assert 'content' not in v['memory'] and v['memory']['audio_path'].endswith('.m4a')
        v=call(r,'memory-step',**args,revision=v['memory']['revision'],operation='advance',elapsed_ms=v['memory']['remaining_ms'])
    assert 'content' not in v['memory']
    expected=raw['reponse']['valeur'];answer=' '.join(expected) if isinstance(expected,list) else str(expected)
    v=call(r,'memory-step',**args,revision=v['memory']['revision'],operation='answer',answer=answer,elapsed_ms=1000)
    target=reference.repondre(theme,ref['session_id'],raw['id'],answer,1000)
    assert v['feedback']==target
    call(r,'finish',session_id=s['session_id']);reference.terminer(theme,ref['session_id'])
    key=f'{theme}--{path}' if path else theme
    assert r.store.lire_maitrise(key)==reference.stockage.lire_maitrise(key)
    for key_id,card in r.store.lire_cartes(key).items():
        other=reference.stockage.lire_cartes(key)[key_id]
        assert (card.stabilite,card.difficulte,card.echeance)==(other.stabilite,other.difficulte,other.echeance)
    if '-differe' in activity or '-premiere-serie' in activity:assert 'attente' in seen


@pytest.mark.parametrize('activity',['deduction','anglais','python'])
def test_new_plain_exercises_reuse_exact_original_corrector(tmp_path,activity):
    r=ApplicationRuntime(str(tmp_path));s=call(r,'start',activity=activity);v=call(r,'view')
    raw=r._session().items_par_id[v['item']['id']];answer=raw['reponse']['valeur']
    assert isinstance(answer,(str,int,float))
    result=call(r,'answer',session_id=s['session_id'],item_id=raw['id'],answer=answer,elapsed_ms=1000)
    assert result['correcte']


def test_immediate_blocks_keep_history_and_quota_across_classic_sessions(tmp_path):
    r=ApplicationRuntime(str(tmp_path));v=call(r,'start',activity='mi-code',parametres={'longueur':2})
    def step(op,**kw):
        nonlocal v
        v=call(r,'immediate-step',session_id=v['session_id'],item_id=v['item_id'],revision=v['immediate']['revision'],operation=op,elapsed_ms=0,**kw)
        return v
    for _ in range(4):
        step('show');step('exposure-ended');step('mask-ended')
        step('answer',response=None,observations={'absence_declaree':True});step('continue')
    assert v['finished'] and len(r.ui['immediate_history'])==1
    assert not r.store.lire_cartes('memoire')
    session=call(r,'start',activity='calcul-mental');call(r,'finish',session_id=session['session_id'])
    v=call(r,'start',activity='mi-chemin');assert r.ui['immediate_daily']['count']==2
    assert len(r.ui['immediate_history'])==1
    with pytest.raises(ValueError):call(r,'start',activity='calcul-mental')
    call(r,'finish',session_id=v['session_id'])
    call(r,'start',activity='mi-objets');call(r,'finish',session_id=r.ui['immediate']['session_id'])
    assert len(r.ui['immediate_history'])==3
    with pytest.raises(ValueError):call(r,'start',activity='mi-code')


def test_immediate_restart_replaces_exposure_without_inventing_answer(tmp_path):
    r=ApplicationRuntime(str(tmp_path));v=call(r,'start',activity='mi-code')
    call(r,'immediate-step',session_id=v['session_id'],item_id=v['item_id'],revision=v['immediate']['revision'],operation='show',elapsed_ms=0)
    restored=ApplicationRuntime(str(tmp_path));new=call(restored,'view')
    assert new['item_id']!=v['item_id'] and new['immediate']['phase']=='pret'
    trials=restored.ui['immediate']['trials'];assert trials[-1]['replaces']==v['item_id']
    assert trials[0]['first'] is None
