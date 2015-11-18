from cliquet.tests.support import unittest

from . import BaseWebTestLocal


class HelloViewTest(BaseWebTestLocal, unittest.TestCase):
    def test_public_url_is_provided_in_public_settings(self):
        resp = self.app.get('/')
        settings = resp.json['settings']
        self.assertEqual(settings['attachment.base_url'],
                         'https://cdn.firefox.net/')
