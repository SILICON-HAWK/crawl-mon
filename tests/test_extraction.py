import unittest
from pathlib import Path

from jevscout.extraction import parse_jobs


FIXTURE = Path(__file__).parent / "fixtures" / "jobs.html"


class ParseJobsTests(unittest.TestCase):
    def test_extracts_job_postings_from_json_ld(self):
        jobs = parse_jobs(
            FIXTURE.read_text(encoding="utf-8"),
            "https://careers.example.test/openings",
            "artifacts/pages/careers.html",
        )

        self.assertEqual(len(jobs), 2)
        self.assertEqual(
            jobs[0],
            {
                "schema_version": 1,
                "parser_version": "jsonld-jobs-v1",
                "title": "Platform Engineer",
                "company": "Example Labs",
                "location": "Bengaluru, IN",
                "description": "Build reliable platforms.",
                "application_url": "https://careers.example.test/careers/platform-engineer",
                "date_posted": "2026-10-20",
                "source_url": "https://careers.example.test/openings",
                "artifact_ref": "artifacts/pages/careers.html",
            },
        )
        self.assertEqual(jobs[1]["title"], "Remote Product Designer")
        self.assertIsNone(jobs[1]["location"])
        self.assertEqual(
            jobs[1]["application_url"],
            "https://jobs.example.test/remote-product-designer",
        )

    def test_skips_bad_records_and_keeps_valid_records_around_bad_scripts(self):
        html = """
        <script type="application/ld+json">{not json</script>
        <script type="application/ld+json">
          [
            {"@type":"Organization","name":"Not a job"},
            {"@type":"JobPosting","description":"No title"},
            {"@type":"JobPosting","title":"Valid role","url":"https://user:secret@example.test/apply"},
            {"@graph":[{"@type":"JobPosting","name":"Uses source","datePosted":"2026-10-01"}]}
          ]
        </script>
        """

        jobs = parse_jobs(html, "https://careers.example.test/jobs", "page-7")

        self.assertEqual([job["title"] for job in jobs], ["Valid role", "Uses source"])
        self.assertIsNone(jobs[0]["application_url"])
        self.assertEqual(jobs[1]["application_url"], "https://careers.example.test/jobs")

    def test_rejects_malformed_provided_urls_without_falling_back_to_source(self):
        html = r'''
        <script type="application/ld+json">
          [
            {"@type":"JobPosting","title":"Bad port","url":"https://jobs.example.test:bad/apply"},
            {"@type":"JobPosting","title":"Out of range","url":"https://jobs.example.test:65536/apply"},
            {"@type":"JobPosting","title":"Backslash","url":"https://jobs.example.test\\evil"},
            {"@type":"JobPosting","title":"Control","url":"https://jobs.example.test/\u0001apply"}
          ]
        </script>
        '''

        jobs = parse_jobs(html, "https://careers.example.test/jobs", "page-8")

        self.assertEqual(len(jobs), 4)
        self.assertTrue(all(job["application_url"] is None for job in jobs))


if __name__ == "__main__":
    unittest.main()
