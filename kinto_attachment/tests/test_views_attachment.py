from cliquet.tests.support import unittest

from . import BaseWebTestLocal, BaseWebTestS3


class UploadTest(object):
    def test_returns_200_to_record_once_uploaded(self):
        self.upload(status=201)

    def test_record_is_created_with_metadata(self):
        self.upload()
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIn('attachment', resp.json['data'])

    def test_returns_200_if_record_already_exists(self):
        self.app.put_json(self.record_uri, {}, headers=self.headers)
        self.upload(status=200)

    def test_adds_cors_and_location_to_response(self):
        response = self.upload()
        self.assertEqual(response.headers['Location'],
                         'http://localhost/v1' + self.record_uri)
        self.assertIn('Access-Control-Allow-Origin', response.headers)


class LocalUploadTest(UploadTest, BaseWebTestLocal, unittest.TestCase):
    pass


class S3UploadTest(UploadTest, BaseWebTestS3, unittest.TestCase):
    pass


class AttachmentViewTest(BaseWebTestLocal, unittest.TestCase):

    def test_only_post_and_options_is_accepted(self):
        self.app.get(self.attachment_uri, headers=self.headers, status=405)
        self.app.put(self.attachment_uri, headers=self.headers, status=405)
        self.app.patch(self.attachment_uri, headers=self.headers, status=405)
        headers = self.headers.copy()
        headers['Access-Control-Request-Method'] = 'POST'
        self.app.options(self.attachment_uri, headers=headers, status=200)

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

    # def test_collection_schema_is_validated(self):
    #     pass

    # def test_record_fields_are_validated(self):
    #     pass
