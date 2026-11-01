"""Availability ordering and explicit start at the HTTP boundary."""
import tempfile, unittest
from pathlib import Path
from fastapi.testclient import TestClient
from jevscout.application.availability import AvailabilityCheck, AvailabilityStore
from jevscout.core.models import RunSpec
from jevscout.interfaces.api import create_app
from jevscout.storage.filesystem import FileRunStore

class AvailabilityApiTests(unittest.TestCase):
    def test_reachable_first_and_inconclusive_stays_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            store=FileRunStore(Path(directory)); run=store.create(RunSpec(['https://source.test']))
            store.save_results(run.id,[{'title':'AI Engineer','application_url':'https://jobs.test/unknown'}, {'title':'Backend Developer','application_url':'https://jobs.test/open'}, {'title':'Software Engineer','application_url':'https://jobs.test/closed'}])
            checks=AvailabilityStore(Path(directory)/'listing-availability.json')
            checks.put([AvailabilityCheck('https://jobs.test/open','available',200,'2026-01-01'),AvailabilityCheck('https://jobs.test/closed','unavailable',404,'2026-01-01')])
            client=TestClient(create_app(store=store,pipeline_manager=object()))
            jobs=client.get('/api/jobs').json()
            self.assertEqual([j['title'] for j in jobs],['Backend Developer','AI Engineer','Software Engineer'])
            self.assertIsNone(jobs[1]['availability'])
            self.assertEqual(jobs[2]['availability']['state'],'unavailable')
            self.assertEqual(client.post('/api/availability/check',json={'urls':['https://jobs.test/open'],'approved':False}).status_code,422)

    def test_company_sources_use_known_ats_hosts_and_do_not_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            store=FileRunStore(Path(directory)); run=store.create(RunSpec(['https://source.test']))
            store.save_results(run.id,[{'title':'AI Engineer','company':'Example','application_url':'https://jobs.ashbyhq.com/acme/job123'}, {'title':'Software Developer','company':'Other','application_url':'https://jobs.ashbyhq.com.evil.test/acme/job'}])
            client=TestClient(create_app(store=store,pipeline_manager=object()))
            result=client.get('/api/company-sources').json()
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['company'],'Example')
            self.assertEqual(result[0]['status'],'unverified')
            self.assertEqual(result[0]['feed_url'],'https://api.ashbyhq.com/posting-api/job-board/acme?includeCompensation=true')
