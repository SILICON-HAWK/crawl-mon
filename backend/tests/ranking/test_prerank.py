"""Structured pre-ranking: loose title, salary and location match before any model."""

import unittest

from jevscout.modules.jobs.prerank import pre_rank

PROFILE = {"role_target": "AI / Forward Deployed Software Engineer",
           "preferred_locations": ["India"], "remote_only": False, "min_salary_inr": 0}


def job(**kw):
    return {"title": "Software Engineer", "location": "Bangalore, India", "salary": None, **kw}


class PreRankTests(unittest.TestCase):
    def test_score_is_bounded_and_has_components(self):
        r = pre_rank(job(), PROFILE)
        self.assertTrue(0 <= r["score"] <= 100)
        for key in ("title", "salary", "location"):
            self.assertTrue(0 <= r[key] <= 100)
        self.assertIsInstance(r["reasons"], list)

    def test_closer_title_scores_higher(self):
        close = pre_rank(job(title="Forward Deployed AI Engineer"), PROFILE)["score"]
        loose = pre_rank(job(title="Backend Software Engineer"), PROFILE)["score"]
        far = pre_rank(job(title="Embedded Firmware Technician"), PROFILE)["score"]
        self.assertGreater(close, loose)
        self.assertGreater(loose, far)

    def test_business_intelligence_and_learning_are_not_ai(self):
        bi = pre_rank(job(title="BI (Business Intelligence) Developer"), PROFILE)["title"]
        hr = pre_rank(job(title="Learning and Development Engineer"), PROFILE)["title"]
        ai = pre_rank(job(title="Machine Learning Engineer"), PROFILE)["title"]
        self.assertGreater(ai, bi)
        self.assertGreater(ai, hr)

    def test_preferred_location_beats_other_and_unknown_is_between(self):
        here = pre_rank(job(location="Hyderabad, India"), PROFILE)["location"]
        there = pre_rank(job(location="Berlin, Germany"), PROFILE)["location"]
        unknown = pre_rank(job(location=None), PROFILE)["location"]
        self.assertGreater(here, unknown)
        self.assertGreater(unknown, there)

    def test_remote_is_partial_credit_unless_remote_only(self):
        loose = pre_rank(job(location="Remote"), PROFILE)["location"]
        strict = pre_rank(job(location="Remote"), {**PROFILE, "remote_only": True})["location"]
        self.assertGreater(loose, 0)
        self.assertGreater(strict, loose)

    def test_salary_meeting_minimum_beats_below_and_unknown_is_neutral(self):
        profile = {**PROFILE, "min_salary_inr": 2_000_000}
        meets = pre_rank(job(salary="INR 2500000–3000000"), profile)["salary"]
        below = pre_rank(job(salary="INR 500000–800000"), profile)["salary"]
        unknown = pre_rank(job(salary=None), profile)["salary"]
        self.assertGreater(meets, unknown)
        self.assertGreater(unknown, below)

    def test_foreign_currency_is_converted_loosely(self):
        profile = {**PROFILE, "min_salary_inr": 2_000_000}
        usd = pre_rank(job(salary="USD 50000–55000"), profile)["salary"]  # ~4M+ INR
        self.assertGreater(usd, 70)

    def test_zero_or_garbage_salary_and_no_minimum_are_neutral(self):
        profile = {**PROFILE, "min_salary_inr": 2_000_000}
        self.assertEqual(pre_rank(job(salary="GBP 0–0"), profile)["salary"],
                         pre_rank(job(salary=None), profile)["salary"])
        self.assertEqual(pre_rank(job(salary="competitive"), profile)["salary"],
                         pre_rank(job(salary=None), profile)["salary"])
        self.assertEqual(pre_rank(job(salary="INR 100"), PROFILE)["salary"],
                         pre_rank(job(salary=None), PROFILE)["salary"])

    def test_dict_salary_and_missing_profile_fields_do_not_crash(self):
        pre_rank(job(salary={"min": 90000, "currency": "INR"}), PROFILE)
        r = pre_rank(job(), {})
        self.assertTrue(0 <= r["score"] <= 100)


if __name__ == "__main__":
    unittest.main()
