import unittest

from jevscout.feeds.location import is_india_eligible, normalize_india_location


class IndiaLocationFilterTests(unittest.TestCase):
    def test_accepts_canonical_indian_tech_hubs(self):
        cases = [
            ("Bengaluru, Karnataka, India", "Bengaluru, Karnataka, India"),
            ("Bangalore", "Bengaluru, India"),
            ("Hyderabad, Telangana", "Hyderabad, Telangana, India"),
            ("Pune, Maharashtra, India", "Pune, Maharashtra, India"),
            ("Mumbai", "Mumbai, Maharashtra, India"),
            ("Gurgaon, Haryana", "Gurgaon, Haryana, India"),
            ("Gurugram", "Gurgaon, Haryana, India"),
            ("Noida, Uttar Pradesh", "Noida, Uttar Pradesh, India"),
            ("New Delhi, India", "Delhi, India"),
            ("Delhi NCR", "Delhi NCR, India"),
            ("Chennai, Tamil Nadu", "Chennai, Tamil Nadu, India"),
            ("Kochi, Kerala", "Kochi, Kerala, India"),
            ("Kolkata", "Kolkata, West Bengal, India"),
            ("Ahmedabad, Gujarat", "Ahmedabad, Gujarat, India"),
        ]
        for raw, expected_normalized in cases:
            with self.subTest(location=raw):
                self.assertTrue(is_india_eligible(raw), f"Expected '{raw}' to be India eligible")
                self.assertEqual(normalize_india_location(raw), expected_normalized)

    def test_accepts_india_eligible_remote_roles(self):
        cases = [
            ("India - Remote", "India - Remote"),
            ("Remote - India", "India - Remote"),
            ("Remote (India)", "India - Remote"),
            ("Remote, India", "India - Remote"),
            ("Worldwide Remote", "Worldwide Remote"),
            ("Anywhere in the world", "Worldwide Remote"),
            ("Remote - Global", "Worldwide Remote"),
        ]
        for raw, expected_normalized in cases:
            with self.subTest(location=raw):
                self.assertTrue(is_india_eligible(raw), f"Expected '{raw}' to be India eligible remote")
                self.assertEqual(normalize_india_location(raw), expected_normalized)

    def test_remote_workplace_type_with_india_country(self):
        self.assertTrue(is_india_eligible("India", workplace_type="remote"))
        self.assertTrue(is_india_eligible("Bangalore", workplace_type="hybrid"))

    def test_strictly_rejects_foreign_locations(self):
        foreign_locations = [
            "San Francisco, CA",
            "New York, NY, United States",
            "London, United Kingdom",
            "Berlin, Germany",
            "Toronto, Ontario, Canada",
            "Singapore",
            "Sydney, Australia",
            "Tokyo, Japan",
            "Dublin, Ireland",
        ]
        for raw in foreign_locations:
            with self.subTest(location=raw):
                self.assertFalse(is_india_eligible(raw), f"Expected '{raw}' to be rejected")
                self.assertIsNone(normalize_india_location(raw))

    def test_strictly_rejects_non_india_remote_roles(self):
        restricted_remotes = [
            "Remote - US",
            "Remote (US Only)",
            "Remote - North America",
            "US Remote",
            "Remote - EMEA",
            "Remote - Europe",
            "Remote - UK",
            "Remote - LatAm",
            "Remote (Canada)",
        ]
        for raw in restricted_remotes:
            with self.subTest(location=raw):
                self.assertFalse(is_india_eligible(raw), f"Expected '{raw}' to be rejected")
                self.assertIsNone(normalize_india_location(raw))

    def test_handles_empty_or_none_safely(self):
        self.assertFalse(is_india_eligible(None))
        self.assertFalse(is_india_eligible(""))
        self.assertFalse(is_india_eligible("   "))
        self.assertIsNone(normalize_india_location(None))
        self.assertIsNone(normalize_india_location(""))
