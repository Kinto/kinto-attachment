from kinto.tests.core.support import unittest

from . import BaseWebTestLocal


class HelloViewTest(BaseWebTestLocal, unittest.TestCase):
    def test_capability_is_exposed(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('attachments', capabilities)
        expected = {
            "description": "Add file attachments to records",
            "url": "https://github.com/Kinto/kinto-attachment/",
        }
        self.assertEqual(expected, capabilities['attachments'])

    def test_public_url_is_provided_in_public_settings(self):
        resp = self.app.get('/')
        settings = resp.json['settings']
        self.assertEqual(settings['attachment.base_url'],
                         'https://cdn.firefox.net/')
