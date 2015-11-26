import os

from pyramid_storage.interfaces import IFileStorage
from cliquet.tests.support import unittest

from . import BaseWebTestLocal, BaseWebTestS3, get_user_headers


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
    def test_file_is_created_on_local_filesystem(self):
        attachment = self.upload().json
        filename = attachment['filename']
        self.assertTrue(os.path.exists(os.path.join('/tmp', filename)))


class S3UploadTest(UploadTest, BaseWebTestS3, unittest.TestCase):
    pass


class DeleteTest(object):
    def setUp(self):
        super(DeleteTest, self).setUp()
        self.attachment = self.upload().json
        self.backend = self.app.app.registry.getUtility(IFileStorage)

    def exists(self, filename):
        return self.backend.exists(filename)

    def test_attachment_is_removed_on_delete(self):
        filename = self.attachment['filename']
        self.assertTrue(self.exists(filename))
        self.app.delete(self.attachment_uri, headers=self.headers, status=204)
        self.assertFalse(self.exists(filename))

    def test_metadata_are_removed_on_delete(self):
        self.app.delete(self.attachment_uri, headers=self.headers, status=204)
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIsNone(resp.json['data'].get('attachment'))

    def test_link_is_removed_on_delete(self):
        storage = self.app.app.registry.storage
        links, _ = storage.get_all("", '__attachments__')
        self.assertEqual(len(links), 1)
        self.app.delete(self.attachment_uri, headers=self.headers, status=204)
        links, _ = storage.get_all("", '__attachments__')
        self.assertEqual(len(links), 0)

    def test_attachment_is_removed_when_record_is_deleted(self):
        filename = self.attachment['filename']
        self.assertTrue(self.exists(filename))
        self.app.delete(self.record_uri, headers=self.headers)
        self.assertFalse(self.exists(filename))

    def test_attachments_are_removed_when_bucket_is_deleted(self):
        filename = self.attachment['filename']
        self.assertTrue(self.exists(filename))
        self.app.delete('/buckets/fennec', headers=self.headers)
        self.assertFalse(self.exists(filename))

    def test_attachments_are_removed_when_collection_is_deleted(self):
        filename = self.attachment['filename']
        self.assertTrue(self.exists(filename))
        self.app.delete('/buckets/fennec/collections/fonts',
                        headers=self.headers)
        self.assertFalse(self.exists(filename))

    def test_attachments_links_are_removed_forever(self):
        storage = self.app.app.registry.storage
        links, _ = storage.get_all("", '__attachments__')
        self.assertEqual(len(links), 1)
        self.app.delete(self.record_uri, headers=self.headers)
        links, _ = storage.get_all("", '__attachments__')
        self.assertEqual(len(links), 0)

    def test_no_error_when_other_resource_is_deleted(self):
        group_url = '/buckets/default/groups/admins'
        self.app.put_json(group_url, {"data": {"members": ["them"]}},
                          headers=self.headers)
        self.app.delete(group_url, headers=self.headers)


class LocalDeleteTest(DeleteTest, BaseWebTestLocal, unittest.TestCase):
    pass


class S3DeleteTest(DeleteTest, BaseWebTestS3, unittest.TestCase):
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
        existing = {'data': {'author': 'frutiger'}}
        self.app.put_json(self.record_uri, existing, headers=self.headers)
        self.upload()
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIn('attachment', resp.json['data'])
        self.assertIn('author', resp.json['data'])

    def test_record_is_created_with_fields(self):
        self.upload(params=[('data', '{"family": "sans"}')])
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertEqual(resp.json['data']['family'], "sans")

    def test_record_is_updated_with_fields(self):
        existing = {'data': {'author': 'frutiger'}}
        self.app.put_json(self.record_uri, existing, headers=self.headers)
        self.upload(params=[('data', '{"family": "sans"}')])
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertEqual(resp.json['data']['family'], 'sans')
        self.assertEqual(resp.json['data']['author'], 'frutiger')

    def test_record_is_created_with_appropriate_permissions(self):
        self.upload()
        current_principal = ("basicauth:c6c27f0c7297ba7d4abd2a70c8a2cb88a06a3"
                             "bb793817ef2c85fe8a709b08022")
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertEqual(resp.json['permissions'],
                         {"write": [current_principal]})

    def test_record_permissions_can_also_be_specified(self):
        self.upload(files=[('attachment', 'image.jpg', '--fake--')],
                    params=[('permissions', '{"read": ["system.Everyone"]}')])
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIn('system.Everyone', resp.json['permissions']['read'])

    # Content Validation.

    def test_record_fields_are_validated_against_schema(self):
        resp = self.upload(params=[('data', '{"author": 12}')], status=400)
        self.assertIn("12 is not of type 'string'", resp.json['message'])

    def test_upload_refused_if_extension_not_allowed(self):
        resp = self.upload(files=[('attachment', 'virus.exe', '--fake--')],
                           status=400)
        self.assertEqual(resp.json['message'],
                         'body: File extension is not allowed.')

    # Permissions.

    def test_upload_refused_if_not_authenticated(self):
        self.headers.pop('Authorization')
        self.upload(status=401)

    def test_upload_refused_if_not_allowed(self):
        self.headers.update(get_user_headers('jean-louis'))
        self.upload(status=403)

    def test_upload_replace_refused_if_only_create_allowed(self):
        # Allow any authenticated to write in this bucket.
        perm = {'permissions': {'record:create': ['system.Authenticated']}}
        self.app.patch_json('/buckets/fennec/collections/fonts',
                            perm, headers=self.headers)
        self.upload(status=201)

        self.headers.update(get_user_headers('jean-louis'))
        self.upload(status=403)

    def test_upload_create_accepted_if_create_allowed(self):
        # Allow any authenticated to write in this bucket.
        perm = {'permissions': {'record:create': ['system.Authenticated']}}
        self.app.patch_json('/buckets/fennec/collections/fonts',
                            perm, headers=self.headers)

        self.headers.update(get_user_headers('jean-louis'))
        self.upload(status=201)

    def test_upload_create_accepted_if_write_allowed(self):
        # Allow any authenticated to write in this bucket.
        perm = {'permissions': {'write': ['system.Authenticated']}}
        self.app.patch_json('/buckets/fennec', perm, headers=self.headers)

        self.headers.update(get_user_headers('jean-louis'))
        self.upload(status=201)

    def test_upload_replace_accepted_if_write_allowed(self):
        # Allow any authenticated to write in this bucket.
        perm = {'permissions': {'write': ['system.Authenticated']}}
        self.app.patch_json('/buckets/fennec', perm, headers=self.headers)
        self.upload(status=201)

        self.headers.update(get_user_headers('jean-louis'))
        self.upload(status=200)

#
# XXX: see bug https://github.com/Kinto/kinto/issues/277
#
# class DefaultBucketTest(BaseWebTestLocal, unittest.TestCase):
#     def setUp(self):
#         super(DefaultBucketTest, self).setUp()
#         self.record_uri = self.get_record_uri('default', 'pix', uuid.uuid4())
#         self.attachment_uri = self.record_uri + '/attachment'

#     def test_implicit_collection_creation_on_upload(self):
#         resp = self.upload()
#         record_uri = resp.headers['Location']
#         self.assertIn('/buckets/c0343679-10aa-a101-bf0f-e96f917f3e27',
#                       record_uri)
