import unittest
from kinto_attachment import __version__
from . import BaseWebTestLocal


class HelloViewTest(BaseWebTestLocal, unittest.TestCase):
    def test_capability_is_exposed(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("attachments", capabilities)
        expected = {
            "version": __version__,
            "description": "Add file attachments to records",
            "url": "https://github.com/Kinto/kinto-attachment/",
            "base_url": "https://files.server.com/root/",
            "gzipped": False
        }
        self.assertEqual(expected, capabilities["attachments"])
