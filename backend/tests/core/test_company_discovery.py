import unittest
from jevscout.modules.jobs.company_discovery import career_feed_candidate

class CompanyDiscoveryTests(unittest.TestCase):
    def test_finds_only_verified_hosted_board_urls(self):
        self.assertEqual(career_feed_candidate('https://job-boards.greenhouse.io/acme/jobs/123'), 'https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true')
        self.assertEqual(career_feed_candidate('https://jobs.ashbyhq.com/acme/123'), 'https://api.ashbyhq.com/posting-api/job-board/acme?includeCompensation=true')
        self.assertEqual(career_feed_candidate('https://jobs.lever.co/acme/123'), 'https://api.lever.co/v0/postings/acme?mode=json')
        self.assertIsNone(career_feed_candidate('https://jobs.ashbyhq.com.evil.test/acme/123'))
        self.assertIsNone(career_feed_candidate('https://company.test/careers'))
