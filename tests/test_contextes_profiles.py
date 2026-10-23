"""Profil de source : choix réellement vus, reprise durable et progression finale seule."""
from mobile.application_runtime import ApplicationRuntime
from test_contextes_runtime import call, step, expose, KEY


def test_seen_sources_profile_keeps_choices_and_discovery_across_restore(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, 'start', activity='memoire-source', profil_contextes='sources-vues')
    assert session['protocole_contextes'] == {'version':'contextes-source-v2','profil':'sources-vues'}
    ids = [item['id'] for item in session['items']]
    sources = {runtime._session().items_par_id[identifier]['reponse']['valeur'] for identifier in ids}
    frozen = {item['id']:item['contenu']['options_rappel'] for item in runtime.ui['session']['items']}
    for index, identifier in enumerate(ids):
        expose(runtime)
        expected = runtime._session().items_par_id[identifier]['reponse']['valeur']
        step(runtime, 'answer', expected)
        step(runtime, 'next')
        if index == 2:
            runtime = ApplicationRuntime(str(tmp_path))
            assert call(runtime, 'view')['contextes']['paused']
            step(runtime, 'resume')
            assert runtime._session().items_decouverts == set(ids[:3])
    assert not runtime.store.lire_cartes(KEY)
    for identifier in ids:
        view = call(runtime, 'view')
        assert view['contextes']['options'] == frozen[identifier]
        assert set(view['contextes']['options']) <= sources
        assert len(set(view['contextes']['options'])) == len(view['contextes']['options'])
        step(runtime, 'answer', runtime._session().items_par_id[identifier]['reponse']['valeur'])
        step(runtime, 'next')
    view = call(runtime, 'view')
    assert view['finished']
    assert view['summary']['resume']['correctes'] == len(ids)
    assert set(runtime.store.lire_cartes(KEY)) == set(ids)
    observations = runtime.store.lire_observations(session['session_id'])
    assert observations['protocole_contextes']['profil'] == 'sources-vues'


def test_profile_photo_retry_records_success_without_erasing_incident(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    session = call(runtime, 'start', activity='memoire-source', profil_contextes='sources-vues')
    step(runtime, 'show')
    step(runtime, 'image-error')
    expose(runtime)
    item = runtime._session().items_par_id[session['items'][0]['id']]
    step(runtime, 'answer', item['reponse']['valeur'])
    record = runtime.store.lire_observations(session['session_id'])['contextes']['decouverte'][0]
    assert record['incident_photo'] is True
    assert record['photo_chargee'] is True


def test_old_checkpoint_without_profile_fields_resumes_original_protocol(tmp_path):
    runtime = ApplicationRuntime(str(tmp_path))
    call(runtime, 'start', activity='memoire-source')
    saved = runtime.store._lire_json(runtime.checkpoint)
    saved['ui']['session'].pop('protocole_contextes', None)
    for stored in saved['sessions']:
        stored['session'].pop('protocole_contextes', None)
        stored['session'].pop('items_decouverts', None)
    runtime.store._ecrire_json(runtime.checkpoint, saved)
    restored = ApplicationRuntime(str(tmp_path))
    view = call(restored, 'view')
    assert view['contextes']['profil'] == 'origine'
    assert restored._session().protocole_contextes is None
    step(restored, 'resume')
    expose(restored)
    item = restored._session().items_par_id[view['item']['id']]
    assert step(restored, 'answer', item['reponse']['valeur'])['feedback']['correcte']
