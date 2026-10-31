import unittest
from jevscout.modules.jobs.filters import is_technical_job

class TechnicalJobsTests(unittest.TestCase):
    def test_includes_ai_backend_and_development_and_excludes_sales_and_teaching(self):
        for title in ('AI Engineer','Forward Deployed Software Engineer','Backend Developer','Data Scientist','Machine Learning Engineer','DevOps Engineer'):
            self.assertTrue(is_technical_job({'title':title}),title)
        for title in ('Sales Manager','Sales Engineer','Math Teacher','Software Engineering Instructor','Technical Recruiter','Artificial Intelligence Payment Specialist','Tech AI Data Delivery Manager'):
            self.assertFalse(is_technical_job({'title':title}),title)

    def test_unrecognized_title_is_undetermined(self):
        from jevscout.modules.jobs.filters import classify_job_category
        self.assertEqual(classify_job_category({'title':'Forward Deployed Engineer'}), 'technical')
        self.assertEqual(classify_job_category({'title':'Product Specialist'}), 'undetermined')
        self.assertEqual(classify_job_category({'title':'Sales Manager'}), 'non_technical')

    def test_extraction_persists_undetermined_for_later_review(self):
        from dataclasses import replace
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from jevscout.application.operations import extract_run
        from jevscout.core.models import RunSpec
        from jevscout.storage.filesystem import FileRunStore
        with TemporaryDirectory() as directory:
            store = FileRunStore(Path(directory))
            run = store.create(RunSpec(['https://example.com/jobs']))
            html = '<script type="application/ld+json">{"@type":"JobPosting","title":"Product Specialist"}</script>'
            store.save_page(run.id, 'https://example.com/jobs', html, {'status_code':200})
            store.update(replace(run, status='completed'))
            extract_run(store, run.id)
            self.assertEqual(store.list_results(run.id)[0]['job_category'], 'undetermined')
