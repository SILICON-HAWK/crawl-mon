"""Exercise a user request across API, pipeline, storage and extraction."""
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from jevscout.application.pipeline import PipelineManager
from jevscout.core.engine import CollectionReport, PageEvidence
from jevscout.interfaces.api import create_app
from jevscout.storage.filesystem import FileRunStore

class FixtureEngine:
    name = 'fixture'
    version = '1'
    async def collect(self, spec, on_page, *, work_dir):
        on_page(PageEvidence(spec.seed_urls[0], '<script type="application/ld+json">{"@type":"JobPosting","title":"Python Engineer","description":"Python FastAPI","url":"https://jobs.test/1"}</script>', 200, 0))
        return CollectionReport(pages_saved=1)

class PipelineApiIntegration(unittest.TestCase):
    def test_api_runs_to_ranked_saved_job(self):
        with tempfile.TemporaryDirectory() as path:
            store = FileRunStore(Path(path))
            client = TestClient(create_app(store=store, pipeline_manager=PipelineManager(store, FixtureEngine())))
            response = client.post('/api/pipeline', json={'seed_urls':['https://jobs.test/'], 'profile':{'role_target':'Python Engineer','primary_skills':['Python'], 'experience_years':2,'preferred_locations':['India']}})
            self.assertEqual(response.status_code, 202)
            pipeline_id = response.json()['id']
            for _ in range(200):
                state = client.get('/api/pipeline/' + pipeline_id).json()
                if state['status'] not in ('queued', 'running'): break
                time.sleep(.01)
            self.assertEqual(state['status'], 'completed')
            self.assertEqual(state['results'][0]['title'], 'Python Engineer')
            self.assertIn('Python', state['results'][0]['matched_skills'])
            self.assertEqual(len(client.get('/api/runs/' + state['runs'][0]['run_id'] + '/results').json()), 1)
