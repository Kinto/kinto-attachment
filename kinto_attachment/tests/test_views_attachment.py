import mock
import os
import uuid

from six.moves.urllib.parse import urlparse
from kinto.tests.core.support import unittest

from . import BaseWebTestLocal, BaseWebTestS3, get_user_headers


class UploadTest(object):
    def test_returns_200_to_record_once_uploaded(self):
        self.upload(status=201)

    def test_record_is_created_with_metadata(self):
        self.upload()
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIn(self.file_field, resp.json['data'])

    def test_returns_200_if_record_already_exists(self):
        self.app.put_json(self.record_uri, {}, headers=self.headers)
        self.upload(status=200)

    def test_adds_cors_and_location_to_response(self):
        response = self.upload()
        self.assertEqual(response.headers['Location'],
                         'http://localhost/v1' + self.record_uri)
        self.assertIn('Access-Control-Allow-Origin', response.headers)

    def test_has_no_subfolder_if_setting_is_undefined(self):
        self.app.app.registry.settings.pop('attachment.folder')
        response = self.upload()
        record = self.get_record(response)
        url = urlparse(record['location'])
        self.assertNotIn('/', url.path[1:])

    def exists(self, fullurl):
        location = fullurl.replace(self.base_url, '')
        return self.backend.exists(location)

    def test_previous_attachment_is_removed_on_replacement(self):
        first = self.get_record(self.upload())
        self.assertTrue(self.exists(first['location']))
        second = self.get_record(self.upload())
        self.assertFalse(self.exists(first['location']))
        self.assertTrue(self.exists(second['location']))


class LocalUploadTest(UploadTest, BaseWebTestLocal, unittest.TestCase):
    def test_file_is_created_on_local_filesystem(self):
        attachment = self.upload().json
        fullurl = attachment['location']
        relativeurl = fullurl.replace(self.base_url, '')
        self.assertTrue(os.path.exists(os.path.join('/tmp', relativeurl)))


class S3UploadTest(UploadTest, BaseWebTestS3, unittest.TestCase):
    pass


class DeleteTest(object):
    def setUp(self):
        super(DeleteTest, self).setUp()
        self.attachment = self.upload().json

    def exists(self, fullurl):
        location = fullurl.replace(self.base_url, '')
        return self.backend.exists(location)

    def test_attachment_is_removed_on_delete(self):
        fullurl = self.attachment['location']
        self.assertTrue(self.exists(fullurl))
        self.app.delete(self.endpoint_uri, headers=self.headers, status=204)
        self.assertFalse(self.exists(fullurl))

    def test_metadata_are_removed_on_delete(self):
        self.app.delete(self.endpoint_uri, headers=self.headers, status=204)
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIsNone(resp.json['data'].get('attachment'))

    def test_link_is_removed_on_delete(self):
        storage = self.app.app.registry.storage
        links, _ = storage.get_all("", '__attachments__')
        self.assertEqual(len(links), self.nb_uploaded_files)
        self.app.delete(self.endpoint_uri, headers=self.headers, status=204)
        links, _ = storage.get_all("", '__attachments__')
        self.assertEqual(len(links), 0)

    def test_attachment_is_removed_when_record_is_deleted(self):
        fullurl = self.attachment['location']
        self.assertTrue(self.exists(fullurl))
        self.app.delete(self.record_uri, headers=self.headers)
        self.assertFalse(self.exists(fullurl))

    def test_attachments_are_removed_when_bucket_is_deleted(self):
        fullurl = self.attachment['location']
        self.assertTrue(self.exists(fullurl))
        self.app.delete('/buckets/fennec', headers=self.headers)
        self.assertFalse(self.exists(fullurl))

    def test_attachments_are_removed_when_collection_is_deleted(self):
        fullurl = self.attachment['location']
        self.assertTrue(self.exists(fullurl))
        self.app.delete('/buckets/fennec/collections/fonts',
                        headers=self.headers)
        self.assertFalse(self.exists(fullurl))

    def test_attachments_links_are_removed_forever(self):
        storage = self.app.app.registry.storage
        links, _ = storage.get_all("", '__attachments__')
        self.assertEqual(len(links), self.nb_uploaded_files)
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


class AttachmentViewTest(object):

    def test_only_post_and_options_is_accepted(self):
        self.app.get(self.endpoint_uri, headers=self.headers, status=405)
        self.app.put(self.endpoint_uri, headers=self.headers, status=405)
        self.app.patch(self.endpoint_uri, headers=self.headers, status=405)
        headers = self.headers.copy()
        headers['Access-Control-Request-Method'] = 'POST'
        self.app.options(self.endpoint_uri, headers=headers, status=200)

    def test_record_is_updated_with_metadata(self):
        existing = {'data': {'author': 'frutiger'}}
        self.app.put_json(self.record_uri, existing, headers=self.headers)
        self.upload()
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIn(self.file_field, resp.json['data'])
        self.assertIn('author', resp.json['data'])

    def test_record_metadata_has_hash_hexdigest(self):
        r = self.upload()
        h = 'db511d372e98725a61278e90259c7d4c5484fc7a781d7dcc0c93d53b8929e2ba'
        self.assertEqual(self.get_record(r)['hash'], h)

    def test_record_metadata_has_randomized_location(self):
        resp = self.upload(files=[
            (self.file_field, b'my-report.pdf', b'--binary--')
        ])
        record = self.get_record(resp)
        self.assertNotIn('report', record['location'])

    def test_record_metadata_can_unrandomize_location(self):
        resp = self.upload(files=[
            (self.file_field, b'my-report.pdf', b'--binary--')
        ], randomize=False)
        record = self.get_record(resp)
        self.assertIn('report', record['location'])

    def test_record_location_contains_subfolder(self):
        self.upload()
        resp = self.app.get(self.record_uri, headers=self.headers)
        location = resp.json['data'][self.file_field]['location']
        self.assertIn('fennec/fonts/', location)

    def test_record_metadata_provides_original_filename(self):
        resp = self.upload(files=[
            (self.file_field, b'my-report.pdf', b'--binary--')
        ])
        record = self.get_record(resp)
        self.assertEqual('my-report.pdf', record['filename'])

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
        self.upload(params=[('permissions', '{"read": ["system.Everyone"]}')])
        resp = self.app.get(self.record_uri, headers=self.headers)
        self.assertIn('system.Everyone', resp.json['permissions']['read'])

    # Content Validation.

    def test_record_fields_are_validated_against_schema(self):
        resp = self.upload(params=[('data', '{"author": 12}')], status=400)
        self.assertIn("12 is not of type 'string'", resp.json['message'])

    def test_upload_refused_if_extension_not_allowed(self):
        resp = self.upload(files=[(self.file_field, b'virus.exe',
                                   b'--fake--')], status=400)
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


class SingleAttachmentViewTest(AttachmentViewTest, BaseWebTestLocal,
                               unittest.TestCase):
    pass


class DefaultBucketTest(BaseWebTestLocal, unittest.TestCase):
    def setUp(self):
        super(DefaultBucketTest, self).setUp()
        self.record_uri = self.get_record_uri('default', 'pix', uuid.uuid4())
        self.endpoint_uri = self.record_uri + '/attachment'

    def test_implicit_collection_creation_on_upload(self):
        resp = self.upload()
        record_uri = resp.headers['Location']
        self.assertIn('/buckets/c0343679-10aa-a101-bf0f-e96f917f3e27',
                      record_uri)


class KeepOldFilesTest(BaseWebTestLocal, unittest.TestCase):
    def make_app(self):
        import webtest
        from kinto import main as testapp
        from kinto import DEFAULT_SETTINGS
        from kinto.tests.core import support as core_support

        settings = core_support.DEFAULT_SETTINGS.copy()
        settings.update(**DEFAULT_SETTINGS)
        settings['storage_backend'] = 'kinto.core.storage.memory'
        settings['permission_backend'] = 'kinto.core.permission.memory'
        settings['userid_hmac_secret'] = "this is not a secret"
        settings['includes'] = "kinto_attachment"

        settings['kinto.attachment.base_path'] = "/tmp"
        settings['kinto.attachment.base_url'] = ""
        settings['kinto.attachment.keep_old_files'] = "true"

        app = webtest.TestApp(testapp({}, **settings))
        app.RequestClass = core_support.get_request_class(prefix="v1")
        return app

    def test_files_are_kept_when_attachment_is_replaced(self):
        resp = self.upload(status=201)
        location1 = resp.json["location"]
        resp = self.upload(status=200)
        location2 = resp.json["location"]
        self.assertNotEqual(location1, location2)
        self.assertTrue(self.backend.exists(location2))
        self.assertTrue(self.backend.exists(location1))


class HeartbeartTest(BaseWebTestS3, unittest.TestCase):
    def test_attachments_is_added_to_heartbeat_view(self):
        resp = self.app.get('/__heartbeat__')
        self.assertIn('attachments', resp.json)

    def test_heartbeat_is_false_if_error_happens(self):
        with mock.patch('pyramid_storage.s3.S3FileStorage.delete') as mocked:
            mocked.side_effect = ValueError
            resp = self.app.get('/__heartbeat__', status=503)
        self.assertFalse(resp.json['attachments'])

    def test_heartbeat_is_true_if_server_is_readonly(self):
        patch = mock.patch('pyramid_storage.s3.S3FileStorage.delete')
        self.addCleanup(patch.stop)
        mocked = patch.start()
        mocked.side_effect = ValueError

        with mock.patch.dict(self.app.app.registry.settings,
                             [('readonly', 'true')]):
            resp = self.app.get('/__heartbeat__')
        self.assertTrue(resp.json['attachments'])
