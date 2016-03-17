from cliquet.tests.support import unittest

from . import BaseBundleWebTestLocal
from .test_views_attachment import DeleteTest, AttachmentViewTest


class BundleDeleteTest(DeleteTest, BaseBundleWebTestLocal, unittest.TestCase):
    def setUp(self):
        super(BundleDeleteTest, self).setUp()
        self.endpoint_uri = self.record_uri + '/attachments'
        self.attachment = self.upload().json[0]


class BundleAttachmentViewTest(AttachmentViewTest, BaseBundleWebTestLocal,
                               unittest.TestCase):
    def test_record_metadata_has_hash_hexdigest(self):
        resp = self.upload(self.default_files)
        hashes = [r['hash'] for r in resp.json]
        expected = (
            'd29cbf24c31584fcbcc5eb70ea909f76b206cd7d05dba049a8d776dcd24fb8d0',
            '9e49985ecf3d95c5a21642cdfc24f92954959b82bc9c58ea6d2dd7583a168337')
        self.assertEqual(hashes[0], expected[0])
        self.assertEqual(hashes[1], expected[1])

    def test_record_metadata_does_not_randomize_location(self):
        r = self.upload(files=[
            (b'attachments', b'my-report.pdf', b'--binary--')
        ])
        self.assertIn('report', r.json[0]['location'])

    def test_record_metadata_provides_original_filename(self):
        r = self.upload(files=[
            (b'attachments', b'my-report.pdf', b'--binary--'),
        ])
        self.assertEqual('my-report.pdf', r.json[0]['filename'])

    def test_record_metadata_has_randomized_location(self):
        pass

    def test_record_location_contains_subfolder(self):
        self.upload()
        resp = self.app.get(self.record_uri, headers=self.headers)
        location = resp.json['data'][self.file_field][0]['location']
        self.assertIn('fennec/fonts/', location)
