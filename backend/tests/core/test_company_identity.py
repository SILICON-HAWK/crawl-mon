import unittest
from jevscout.modules.jobs.company_identity import resolve_company

class CompanyIdentityTests(unittest.TestCase):
    def test_curated_board_uses_employer_not_department(self):
        job={'company':'Engineering','source_url':'https://boards-api.greenhouse.io/v1/boards/sonicwall/jobs?content=true'}
        self.assertEqual(resolve_company(job), 'SonicWall')
    def test_unknown_employer_not_inferred_from_domain(self):
        self.assertIsNone(resolve_company({'company':None,'source_url':'https://unknown.example/jobs'}))
