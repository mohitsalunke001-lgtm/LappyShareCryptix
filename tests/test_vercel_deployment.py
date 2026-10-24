import os
import unittest
from unittest.mock import patch

from app import create_app


class VercelDeploymentTestCase(unittest.TestCase):
    def test_fresh_vercel_database_can_render_homepage(self):
        with patch.dict(os.environ, {"VERCEL": "1"}):
            app = create_app("testing")

        response = app.test_client().get("/")

        self.assertEqual(response.status_code, 200)
