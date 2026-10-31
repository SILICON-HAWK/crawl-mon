import unittest
from jevscout.modules.jobs.filters import is_technical_job

class TechnicalJobsTests(unittest.TestCase):
    def test_includes_ai_backend_and_development_and_excludes_sales_and_teaching(self):
        for title in ('AI Engineer','Forward Deployed Software Engineer','Backend Developer','Data Scientist','Machine Learning Engineer','DevOps Engineer'):
            self.assertTrue(is_technical_job({'title':title}),title)
        for title in ('Sales Manager','Sales Engineer','Math Teacher','Software Engineering Instructor','Technical Recruiter','Artificial Intelligence Payment Specialist','Tech AI Data Delivery Manager'):
            self.assertFalse(is_technical_job({'title':title}),title)
