import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from jevscout.core.models import RunSpec
from jevscout.interfaces.api import create_app
from jevscout.modules.jobs.scoring.models import NoulAnswer
from jevscout.storage.filesystem import FileRunStore

class Client:
    model='fixture'
    def __init__(self, **kwargs): pass
    def evaluate(self,state,questions):
        assert 'FastAPI' in state
        return {name:NoulAnswer(type='noul',noul=0.7) for name in questions}

class TestClassification(unittest.TestCase):
    def test_saved_job_classification_persists_dimensions(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'OPENROUTER_API_KEY':'test'}, clear=False):
            store=FileRunStore(Path(directory)); run=store.create(RunSpec(['https://example.com']))
            store.save_results(run.id,[{'title':'AI Engineer','description':'Python','application_url':'https://example.com/job'}])
            app=create_app(store=store,pipeline_manager=object()); profile=app.state.profile_store
            profile.put('alice',freeform_context='FastAPI and AI',structured_fields={})
            with patch('jevscout.modules.jobs.scoring.client.OpenRouterDecisionClient',Client):
                client=TestClient(app)
                response=client.post('/api/classify',json={'username':'alice','run_id':run.id,'job_index':0})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['dimensions']['career_direction'],0.7)
                self.assertEqual(client.get('/api/runs/'+run.id+'/evaluations').json()[0]['job_index'],0)

    def test_missing_profile_and_job_are_distinguished(self):
        with tempfile.TemporaryDirectory() as directory:
            store=FileRunStore(Path(directory)); run=store.create(RunSpec(['https://example.com']))
            store.save_results(run.id,[{'title':'Engineer'}])
            app=create_app(store=store,pipeline_manager=object()); client=TestClient(app)
            missing=client.post('/api/classify',json={'username':'nobody','run_id':run.id,'job_index':0})
            self.assertEqual(missing.status_code,404)
            self.assertEqual(missing.json()['detail'],'Profile not found; save it on the Profile page')
            app.state.profile_store.put('alice',freeform_context='Python',structured_fields={})
            missing_job=client.post('/api/classify',json={'username':'alice','run_id':run.id,'job_index':5})
            self.assertEqual(missing_job.status_code,404)
            self.assertEqual(missing_job.json()['detail'],'Job not found; refresh the Jobs page')

    def test_cached_result_avoids_new_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            store=FileRunStore(Path(directory)); run=store.create(RunSpec(['https://example.com']))
            store.save_results(run.id,[{'title':'AI Engineer'}])
            store.save_evaluations(run.id,[{'job_index':0,'username':'alice','model':'saved','dimensions':{'qualification':0.8}}])
            app=create_app(store=store,pipeline_manager=object())
            app.state.profile_store.put('alice',freeform_context='Python',structured_fields={})
            with patch('jevscout.modules.jobs.scoring.client.OpenRouterDecisionClient') as remote:
                response=TestClient(app).post('/api/classify',json={'username':'alice','run_id':run.id,'job_index':0})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.json()['model'],'saved')
                remote.assert_not_called()

    def test_rate_limit_is_reported_without_leaking_provider_response(self):
        class Limited(Client):
            def evaluate(self,state,questions): raise RuntimeError('OpenRouter Decisions API returned HTTP 429: secret payload')
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'OPENROUTER_API_KEY':'test'}, clear=False):
            store=FileRunStore(Path(directory)); run=store.create(RunSpec(['https://example.com']))
            store.save_results(run.id,[{'title':'AI Engineer'}])
            app=create_app(store=store,pipeline_manager=object())
            app.state.profile_store.put('alice',freeform_context='Python',structured_fields={})
            with patch('jevscout.modules.jobs.scoring.client.OpenRouterDecisionClient',Limited):
                response=TestClient(app).post('/api/classify',json={'username':'alice','run_id':run.id,'job_index':0})
                self.assertEqual(response.status_code,429)
                self.assertNotIn('secret payload',response.text)

    def test_saved_decision_reused_for_same_job_in_another_run(self):
        with tempfile.TemporaryDirectory() as directory:
            store=FileRunStore(Path(directory)); old=store.create(RunSpec(['https://example.com/old'])); new=store.create(RunSpec(['https://example.com/new']))
            store.save_results(old.id,[{'title':'AI Engineer','application_url':'https://example.com/job#apply'}])
            store.save_results(new.id,[{'title':'AI Engineer','application_url':'https://example.com/job'}])
            store.save_evaluations(old.id,[{'job_index':0,'username':'alice','model':'saved','dimensions':{'qualification':0.8}}])
            app=create_app(store=store,pipeline_manager=object()); app.state.profile_store.put('alice',freeform_context='Python',structured_fields={})
            with patch('jevscout.modules.jobs.scoring.client.OpenRouterDecisionClient') as remote:
                response=TestClient(app).post('/api/classify',json={'username':'alice','run_id':new.id,'job_index':0})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.json()['model'],'saved')
                remote.assert_not_called()
