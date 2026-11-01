import unittest
from jevscout.modules.jobs.extraction import parse_jobs

HTML = '''<div class="mb-6 w-full rounded border border-gray-400 bg-white">
<a href="/company/example"><span>Example Labs</span></a>
<div><a href="/jobs/123-python-engineer"><span>Python Engineer</span></a></div>
<div><a href="/jobs/124-product-manager">Product Manager</a></div>
</div><a href="/jobs/not-a-job">bad</a>'''

class WellfoundRoleTests(unittest.TestCase):
    def test_extracts_jobs_with_employer_and_provenance(self):
        items=parse_jobs(HTML,'https://wellfound.com/role/l/software-engineer/india','pages/example.html')
        self.assertEqual([item['title'] for item in items],['Python Engineer','Product Manager'])
        self.assertEqual(items[0]['company'],'Example Labs')
        self.assertEqual(items[0]['application_url'],'https://wellfound.com/jobs/123-python-engineer')
        self.assertEqual(items[0]['artifact_ref'],'pages/example.html')
        self.assertIsNone(items[0]['location'])
        self.assertIsNone(items[0]['salary'])

    def test_does_not_parse_other_domains_or_invent_india_location(self):
        self.assertEqual(parse_jobs(HTML,'https://wellfound.com.evil.test/role/x','ref'),[])
        self.assertEqual(parse_jobs(HTML,'https://wellfound.com/role/l/software-engineer/india','ref',india_only=True),[])

    def test_saved_page_replays_into_persisted_results(self):
        from dataclasses import replace
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from jevscout.application.operations import extract_run
        from jevscout.core.models import RunSpec
        from jevscout.storage.filesystem import FileRunStore
        with TemporaryDirectory() as folder:
            store=FileRunStore(Path(folder)); url='https://wellfound.com/role/l/software-engineer/india'
            run=store.create(RunSpec([url],max_pages=1,max_depth=0))
            store.save_page(run.id,url,HTML,{'status_code':200,'depth':0})
            store.update(replace(run,status='completed'))
            extracted=extract_run(store,run.id)
            self.assertEqual(extracted,store.list_results(run.id))
            self.assertEqual(extracted[0]['job_category'],'technical')
            self.assertEqual(extracted[0]['company'],'Example Labs')
