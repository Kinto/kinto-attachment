import uuid

import mock
from cliquet.tests.support import unittest
from cliquet.utils import encode_header

from . import BaseWebTestLocal, BaseWebTestS3


class UploadTest(object):
    def setUp(self):
        super(UploadTest, self).setUp()
        self.create_collection('fennec', 'fonts')
        self.record_uri = self.record_uri('fennec', 'fonts', uuid.uuid4())
        self.attachment_uri = self.record_uri + '/attachment'

    def upload(self, files=None, params=[]):
        files = files or [('attachment', 'image.jpg', '--fake--')]
        headers = self.headers.copy()
        content_type, body = self.app.encode_multipart(params, files)
        headers['Content-Type'] = encode_header(content_type)
        return self.app.post(self.attachment_uri, body, headers=headers)

    def test_only_post_is_accepted(self):
        self.app.get(self.attachment_uri, headers=self.headers, status=405)
        self.app.put(self.attachment_uri, headers=self.headers, status=405)
        self.app.patch(self.attachment_uri, headers=self.headers, status=405)

    def test_returns_303_to_record_once_uploaded(self):
        response = self.upload()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['Location'],
                         'http://localhost/v1' + self.record_uri)

    def test_record_is_created_with_metadata(self):
        self.upload()
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIn('attachment', resp.json['data'])

    def test_record_is_updated_with_metadata(self):
        existing = {'data': {'theme': 'orange'}}
        self.app.put_json(self.record_uri, existing, headers=self.headers)
        self.upload()
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIn('attachment', resp.json['data'])
        self.assertIn('theme', resp.json['data'])

    def test_record_is_created_with_fields(self):
        self.upload(params=[('data', '{"category": "wallpaper"}')])
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertEqual(resp.json['data']['category'], "wallpaper")

    def test_record_is_updated_with_fields(self):
        existing = {'data': {'theme': 'orange'}}
        self.app.put_json(self.record_uri, existing, headers=self.headers)
        self.upload(params=[('data', '{"category": "wallpaper"}')])
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertEqual(resp.json['data']['category'], 'wallpaper')
        self.assertEqual(resp.json['data']['theme'], 'orange')

    # def test_record_permissions_can_also_be_specified(self):
    #     self.upload([('attachment', 'image.jpg', '--fake--')],
    #                 [('permissions', '{"read": ["system.Everyone"]}')])
    #     resp = self.app.get(self.record_uri, headers=self.headers)
    #     self.assertIn("system.Everyone", resp.json['permissions']['read'])

    def test_collection_schema_is_validated(self):
        pass

    def test_record_fields_are_validated(self):
        pass


class LocalUploadTest(UploadTest, BaseWebTestLocal, unittest.TestCase):
    pass


class S3UploadTest(UploadTest, BaseWebTestS3, unittest.TestCase):
    def upload(self, *args, **kwargs):
        patch = mock.patch('pyramid_storage.s3.S3FileStorage.save_file',
                           return_value='upload.jpg')
        with patch.start():
            return super(S3UploadTest, self).upload(*args, **kwargs)
