"""Public scoring regressions using saved evidence and offline decisions."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from jevscout.application import score_run
from jevscout.models import RunSpec
from jevscout.scoring.client import LocalHeuristicDecisionClient
from jevscout.scoring.engine import JobMatchEngine
from jevscout.scoring.models import CandidateProfile, JobPosting
from jevscout.storage import FileRunStore
from tests.cli.test_cli import invoke


PROFILE = CandidateProfile('Engineer', ['Python'], 3, ['India'])
URLS = ['https://example.test/jobs/1', 'https://example.test/jobs/2']


def jobs():
    return [dict(title='Engineer', location='India', description='Python',
                 application_url=url) for url in URLS]


def saved_run(store, postings):
    run = store.create(RunSpec(['https://example.test/jobs']))
    document = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'JobPosting', 'title': job['title'],
         'description': job['description'], 'url': job['application_url']}
        for job in postings
    ]}
    store.save_page(run.id, 'https://example.test/jobs',
                    '<script type="application/ld+json">' + json.dumps(document) + '</script>',
                    {'status_code': 200, 'depth': 0})
    store.update(replace(run, status='completed'))
    return run


class ScoringRegressionTests(unittest.TestCase):
    def test_scores_saved_evidence_without_preextracted_results(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = saved_run(store, jobs())
            self.assertEqual(store.list_results(run.id), [])
            try:
                evaluations = score_run(store, run.id, PROFILE,
                                        client=LocalHeuristicDecisionClient())
                self.assertEqual(len(evaluations), 2)
                self.assertEqual(len(store.list_results(run.id)), 2)
                self.assertEqual(store.list_evaluations(run.id), evaluations)
            finally:
                with store.operation_lock():
                    self.assertEqual(store.get(run.id).status, 'completed')

    def test_automatic_extraction_preserves_terminal_guard_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            for status in ('pending', 'running'):
                with self.subTest(status=status):
                    run = saved_run(store, jobs())
                    store.update(replace(run, status=status))
                    with self.assertRaisesRegex(RuntimeError, 'finish collection'):
                        score_run(store, run.id, PROFILE, client=LocalHeuristicDecisionClient())
                    self.assertEqual(store.list_results(run.id), [])
                    self.assertEqual(store.list_evaluations(run.id), [])
            run = saved_run(store, jobs())
            store.write_execution(run.id, {'items_extracted': 0, 'engine': 'fixture'})
            score_run(store, run.id, PROFILE, client=LocalHeuristicDecisionClient())
            report = store.read_execution(run.id)
            self.assertEqual(report['items_extracted'], 2)
            self.assertEqual(report['engine'], 'fixture')
            self.assertTrue(report['last_extracted_at'])

    def test_empty_saved_evidence_returns_no_evaluations_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = saved_run(store, [])
            try:
                self.assertEqual(score_run(store, run.id, PROFILE,
                                           client=LocalHeuristicDecisionClient()), [])
                self.assertEqual(store.list_evaluations(run.id), [])
            finally:
                with store.operation_lock():
                    self.assertEqual(store.get(run.id).status, 'completed')

    def test_same_title_postings_keep_application_url_identity_in_either_order(self):
        engine = JobMatchEngine(LocalHeuristicDecisionClient())
        for postings, expected in [(jobs(), URLS), (list(reversed(jobs())), list(reversed(URLS)))]:
            with self.subTest(order=expected):
                results = engine.evaluate_batch(PROFILE, postings)
                self.assertEqual([result.job_id for result in results], expected)

    def test_application_url_identities_survive_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = saved_run(store, [])
            store.save_results(run.id, jobs())
            results = score_run(store, run.id, PROFILE, client=LocalHeuristicDecisionClient())
            self.assertEqual([item['job_id'] for item in results], URLS)
            reopened = FileRunStore(Path(directory))
            self.assertEqual([item['job_id'] for item in reopened.list_evaluations(run.id)], URLS)

    def test_existing_identity_inputs_remain_supported(self):
        engine = JobMatchEngine(LocalHeuristicDecisionClient())
        cases = [
            ({'id': 'posting-1', 'url': URLS[1], 'application_url': URLS[0], 'title': 'Engineer'}, 'posting-1'),
            ({'url': URLS[0], 'title': 'Engineer'}, URLS[0]),
            (JobPosting(title='Engineer', location='India', url=URLS[0]), URLS[0]),
            ({'title': 'Engineer'}, 'Engineer'),
            ({'id': '', 'url': None, 'application_url': '', 'title': 'Engineer'}, 'Engineer'),
        ]
        for job, expected in cases:
            with self.subTest(job=job):
                self.assertEqual(engine.evaluate_job(PROFILE, job).job_id, expected)

    def test_offline_cli_scores_saved_evidence_and_lists_persisted_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            store = FileRunStore(data_dir)
            run = saved_run(store, jobs())
            self.assertEqual(store.list_results(run.id), [])
            scored = invoke(data_dir, 'runs', 'score', run.id, '--offline')
            self.assertEqual(scored.returncode, 0, scored.stderr)
            evaluations = json.loads(scored.stdout)
            self.assertEqual([item['job_id'] for item in evaluations], URLS)
            listed = invoke(data_dir, 'runs', 'evaluations', run.id)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(json.loads(listed.stdout), evaluations)
