"""The built app supports direct navigation to each frontend page."""
import importlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from fastapi.testclient import TestClient

class FrontendRoutes(TestCase):
    def test_deep_links_return_frontend_and_api_is_not_shadowed(self):
        with TemporaryDirectory() as directory:
            Path(directory, 'index.html').write_text('<html>JevScout test</html>')
            with patch.dict(os.environ, {'JEVSCOUT_FRONTEND_DIR': directory}):
                production = importlib.import_module('jevscout.interfaces.production')
                client = TestClient(production.app)
                for path in ('/jobs', '/runs', '/profile', '/architecture', '/all-jobs'):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('JevScout test', response.text)
                self.assertEqual(client.get('/api/runs').status_code, 200)
