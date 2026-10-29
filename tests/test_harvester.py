import unittest

from jevscout.feeds.harvester import (
    build_provider_endpoint,
    extract_token_from_surt,
    extract_tokens_from_cdx_lines,
)


class HarvesterTests(unittest.TestCase):
    def test_extract_token_from_path_based_surts(self):
        # Greenhouse
        gh_surt = "io,greenhouse,boards)/stripe/jobs 20250101000000 https://boards.greenhouse.io/stripe/jobs text/html 200 ..."
        self.assertEqual(extract_token_from_surt(gh_surt, "greenhouse"), "stripe")

        # Ashby
        ashby_surt = "com,ashbyhq,jobs)/retool 20250101000000 https://jobs.ashbyhq.com/retool text/html 200 ..."
        self.assertEqual(extract_token_from_surt(ashby_surt, "ashby"), "retool")

        # Lever
        lever_surt = "co,lever,jobs)/postman 20241201000000 https://jobs.lever.co/postman text/html 200 ..."
        self.assertEqual(extract_token_from_surt(lever_surt, "lever"), "postman")

    def test_extract_token_from_subdomain_based_surts(self):
        # Breezy
        breezy_surt = "hr,breezy,acme)/ 20250101000000 https://acme.breezy.hr/ text/html 200 ..."
        self.assertEqual(extract_token_from_surt(breezy_surt, "breezy"), "acme")

        # Recruitee
        recruitee_surt = "com,recruitee,techco)/ 20250101000000 https://techco.recruitee.com/ text/html 200 ..."
        self.assertEqual(extract_token_from_surt(recruitee_surt, "recruitee"), "techco")

        # Teamtailor
        tt_surt = "com,teamtailor,coolbrand)/jobs 20250101000000 https://coolbrand.teamtailor.com/jobs text/html 200 ..."
        self.assertEqual(extract_token_from_surt(tt_surt, "teamtailor"), "coolbrand")

    def test_skips_reserved_subdomains_and_invalid_tokens(self):
        # Skip www, api, app, embed
        self.assertIsNone(extract_token_from_surt("hr,breezy,www)/ ...", "breezy"))
        self.assertIsNone(extract_token_from_surt("com,recruitee,api)/ ...", "recruitee"))
        self.assertIsNone(extract_token_from_surt("io,greenhouse,boards)/embed/ ...", "greenhouse"))
        self.assertIsNone(extract_token_from_surt("co,lever,jobs)/robots.txt ...", "lever"))

    def test_build_provider_endpoint_constructs_exact_apis(self):
        self.assertEqual(
            build_provider_endpoint("greenhouse", "stripe"),
            "https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true",
        )
        self.assertEqual(
            build_provider_endpoint("ashby", "retool"),
            "https://api.ashbyhq.com/posting-api/job-board/retool?includeCompensation=true",
        )
        self.assertEqual(
            build_provider_endpoint("lever", "postman"),
            "https://api.lever.co/v0/postings/postman?mode=json",
        )
        self.assertEqual(
            build_provider_endpoint("breezy", "acme"),
            "https://acme.breezy.hr/json",
        )
        self.assertEqual(
            build_provider_endpoint("recruitee", "techco"),
            "https://techco.recruitee.com/api/offers/",
        )
        self.assertEqual(
            build_provider_endpoint("teamtailor", "coolbrand"),
            "https://coolbrand.teamtailor.com/jobs.json",
        )

    def test_extract_tokens_from_cdx_lines_deduplicates(self):
        lines = [
            "io,greenhouse,boards)/stripe/jobs 200 ...",
            "io,greenhouse,boards)/stripe/jobs/123 200 ...",
            "io,greenhouse,boards)/inmobi 200 ...",
            "io,greenhouse,boards)/embed/test 200 ...",  # reserved
            "unrelated line",
        ]
        tokens = extract_tokens_from_cdx_lines(lines, "greenhouse")
        self.assertEqual(tokens, {"stripe", "inmobi"})
