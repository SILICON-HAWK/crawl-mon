import unittest

from jevscout.models import RunSpec


class RunScopeTests(unittest.TestCase):
    def test_local_fixture_access_is_explicit_and_survives_serialization(self):
        default = RunSpec.from_dict({"seed_urls": ["https://example.test"]})
        self.assertFalse(default.allow_local)
        local = RunSpec(["http://127.0.0.1:8123"], allow_local=True)
        self.assertTrue(RunSpec.from_dict(local.to_dict()).allow_local)

    def test_local_access_flag_must_be_boolean(self):
        with self.assertRaises(ValueError):
            RunSpec(["https://example.test"], allow_local="yes")
