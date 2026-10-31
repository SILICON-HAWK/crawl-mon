import unittest

from jevscout.adapters.sources.quality import (
    clean_department,
    is_technical_posting,
    sanitize_description,
)


class QualityGuardsTests(unittest.TestCase):
    def test_sanitize_description_strips_cdn_and_scripts(self):
        raw_html = (
            "<p>Join our team. Visit //cdn2.hubspot.net/hubfs/banner.png or "
            "//static.xx.fbcdn.net/images/emoji.php/v9/t51/1/16/1f44d.png for info. "
            "Contact careers@example.com for questions.</p>"
        )
        cleaned = sanitize_description(raw_html)
        self.assertNotIn("hubspot.net", cleaned)
        self.assertNotIn("emoji.php", cleaned)
        self.assertNotIn("careers@example.com", cleaned)
        self.assertIn("Join our team.", cleaned)

    def test_is_technical_posting_recognizes_tech_titles(self):
        self.assertTrue(is_technical_posting("Staff Platform Engineer", "Infrastructure"))
        self.assertTrue(is_technical_posting("Backend Developer", "Product"))
        self.assertTrue(is_technical_posting("Data Analyst", "Analytics"))
        self.assertTrue(is_technical_posting("DevOps Lead", None))
        self.assertTrue(is_technical_posting("Software Engineer in Test", "QA"))

    def test_is_technical_posting_rejects_non_tech_titles(self):
        self.assertFalse(is_technical_posting("Home Care Nurse", "Patient Care"))
        self.assertFalse(is_technical_posting("Dialectical Behavior Therapist", "Clinical"))
        self.assertFalse(is_technical_posting("Regional Sales Representative", "Sales"))
        self.assertFalse(is_technical_posting("Executive Assistant", "Operations"))

    def test_clean_department_suppresses_when_board_has_too_many_departments(self):
        # 25 or fewer departments is considered a functional organization
        self.assertEqual(clean_department("Engineering", total_departments=12), "Engineering")
        self.assertEqual(clean_department("Product", total_departments=25), "Product")

        # More than 25 departments indicates site/branch subcodes (e.g. 190 home-care visit branches)
        self.assertIsNone(clean_department("Baltimore Visits (BV) - 94", total_departments=26))
        self.assertIsNone(clean_department("Regional Branch 42", total_departments=150))

    def test_clean_department_handles_none_or_empty(self):
        self.assertIsNone(clean_department(None, total_departments=5))
        self.assertIsNone(clean_department("", total_departments=5))
        self.assertIsNone(clean_department("   ", total_departments=5))
