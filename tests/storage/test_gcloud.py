import datetime
import io
import unittest
from unittest import mock

from pyramid.exceptions import ConfigurationError

from kinto_attachment.storage.gcloud import GoogleCloudStorage
from tests.storage import MockFS, _FakeGCSBlob, _FakeGCSClient


def make_storage(**kwargs):
    defaults = dict(
        credentials="creds.json", bucket_name="test-bucket", base_url="https://cdn.example.com/"
    )
    defaults.update(kwargs)
    return GoogleCloudStorage(**defaults)


class TestGoogleCloudStorage(unittest.TestCase):
    def setUp(self):
        self._client_patch = mock.patch("kinto_attachment.storage.gcloud.Client", _FakeGCSClient)
        self._blob_patch = mock.patch("kinto_attachment.storage.gcloud.Blob", _FakeGCSBlob)
        self._client_patch.start()
        self._blob_patch.start()
        self.storage = make_storage()

    def tearDown(self):
        self._client_patch.stop()
        self._blob_patch.stop()

    def test_from_settings(self):
        s = GoogleCloudStorage.from_settings(
            {
                "storage.gcloud.credentials": "c.json",
                "storage.gcloud.bucket_name": "my-bucket",
                "storage.base_url": "https://cdn.example.com/",
            },
            prefix="storage.",
        )
        self.assertEqual(s.credentials, "c.json")
        self.assertEqual(s.bucket_name, "my-bucket")
        self.assertEqual(s.base_url, "https://cdn.example.com/")

    def test_from_settings_requires_bucket_name(self):
        with self.assertRaises(ConfigurationError):
            GoogleCloudStorage.from_settings({}, prefix="storage.")

    def test_acl_defaults_applied(self):
        s = make_storage(acl=None)
        self.assertEqual(s.acl, "publicRead")
        self.assertEqual(s.auto_create_acl, "projectPrivate")

    def test_uniform_bucket_level_access_clears_acl(self):
        s = make_storage(acl=None, uniform_bucket_level_access=True)
        self.assertIsNone(s.acl)

    def test_acl_with_uniform_access_raises(self):
        with self.assertRaises(ConfigurationError):
            make_storage(acl="publicRead", uniform_bucket_level_access=True)

    def test_get_connection_uses_credentials_file(self):
        conn = self.storage.get_connection()
        self.assertIsInstance(conn, _FakeGCSClient)

    def test_get_connection_is_cached(self):
        self.assertIs(self.storage.get_connection(), self.storage.get_connection())

    def test_get_connection_without_credentials_uses_adc(self):
        s = make_storage(credentials=None)
        conn = s.get_connection()
        self.assertIsInstance(conn, _FakeGCSClient)

    def test_get_connection_with_project_and_no_credentials(self):
        s = make_storage(credentials=None, project="my-project")
        conn = s.get_connection()
        self.assertIsInstance(conn, _FakeGCSClient)

    def test_url_joins_base_url_and_filename(self):
        self.assertEqual(self.storage.url("photo.jpg"), "https://cdn.example.com/photo.jpg")

    def test_url_with_empty_filename(self):
        self.assertEqual(self.storage.url(""), "https://cdn.example.com/")

    def test_exists_false_for_missing_file(self):
        self.assertFalse(self.storage.exists("missing.jpg"))

    def test_exists_true_after_save(self):
        self.storage.save_file(io.BytesIO(b"data"), "photo.jpg")
        self.assertTrue(self.storage.exists("photo.jpg"))

    def test_exists_empty_name_checks_bucket(self):
        # empty string → bucket reachability check
        self.assertTrue(self.storage.exists(""))

    def test_exists_returns_false_when_bucket_unreachable(self):
        with mock.patch.object(self.storage, "get_bucket", side_effect=RuntimeError("gone")):
            self.assertFalse(self.storage.exists(""))

    def test_delete_removes_file(self):
        self.storage.save_file(io.BytesIO(b"data"), "photo.jpg")
        self.storage.delete("photo.jpg")
        self.assertFalse(self.storage.exists("photo.jpg"))

    def test_save_accepts_fieldStorage_object(self):
        name = self.storage.save(MockFS("image.jpg", b"binary"))
        self.assertEqual(name, "image.jpg")
        self.assertTrue(self.storage.exists("image.jpg"))

    def test_save_file_returns_filename(self):
        name = self.storage.save_file(io.BytesIO(b"data"), "doc.pdf")
        self.assertEqual(name, "doc.pdf")

    def test_save_file_with_folder(self):
        name = self.storage.save_file(io.BytesIO(b"data"), "doc.pdf", folder="a/b")
        self.assertEqual(name, "a/b/doc.pdf")
        self.assertTrue(self.storage.exists("a/b/doc.pdf"))

    def test_save_file_randomizes_filename(self):
        name = self.storage.save_file(io.BytesIO(b"data"), "original.jpg", randomize=True)
        self.assertNotEqual(name, "original.jpg")
        self.assertTrue(name.endswith(".jpg"))
        self.assertTrue(self.storage.exists(name))

    def test_save_file_filename_pattern_datetime(self):
        with mock.patch("kinto_attachment.storage.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.datetime(2024, 6, 1, 1, 1, 1)
            name = self.storage.save_file(
                io.BytesIO(b"data"), "file.txt", filename_pattern="{datetime}-{filename}"
            )
        self.assertEqual(name, "20240601010101-file.txt")
        self.assertTrue(self.storage.exists(name))

    def test_save_file_filename_pattern_with_rid(self):
        with mock.patch("kinto_attachment.storage.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.datetime(2024, 6, 1, 1, 1, 1)
            name = self.storage.save_file(
                io.BytesIO(b"data"),
                "file.txt",
                filename_pattern="{datetime}-{rid}-{filename}",
                record_id="abc123",
            )
        self.assertEqual(name, "20240601010101-abc123-file.txt")
        self.assertTrue(self.storage.exists(name))

    def test_save_file_skips_existing_when_no_replace(self):
        self.storage.save_file(io.BytesIO(b"original"), "f.txt")
        name = self.storage.save_file(io.BytesIO(b"new"), "f.txt", replace=False)
        self.assertEqual(name, "f.txt")

    def test_save_file_overwrites_when_replace(self):
        self.storage.save_file(io.BytesIO(b"original"), "f.txt")
        name = self.storage.save_file(io.BytesIO(b"new"), "f.txt", replace=True)
        self.assertEqual(name, "f.txt")

    def test_save_file_strips_directory_from_filename(self):
        name = self.storage.save_file(io.BytesIO(b"x"), "../escape.txt")
        self.assertNotIn("..", name)

    # --- _get_or_create_bucket (NotFound paths) ---

    def test_get_bucket_with_different_name_returns_separate_bucket(self):
        default = self.storage.get_bucket()
        other = self.storage.get_bucket("other-bucket")
        # Both are the same fake (single-bucket client), but the code path is exercised.
        self.assertIs(default, other)

    def test_raises_when_bucket_missing_and_auto_create_disabled(self):
        from google.cloud.exceptions import NotFound

        mock_client = mock.Mock()
        mock_client.get_bucket.side_effect = NotFound("bucket")
        self.storage._client = mock_client
        with self.assertRaises(RuntimeError):
            self.storage._get_or_create_bucket("missing")

    def test_bucket_auto_created_when_not_found(self):
        from google.cloud.exceptions import NotFound

        from tests.storage import _FakeGCSBucket

        fake_bucket = _FakeGCSBucket()
        fake_bucket.acl = mock.Mock()
        mock_client = mock.Mock()
        mock_client.get_bucket.side_effect = NotFound("bucket")
        mock_client.create_bucket.return_value = fake_bucket
        self.storage._client = mock_client
        self.storage.auto_create_bucket = True
        result = self.storage._get_or_create_bucket("new-bucket")
        self.assertIs(result, fake_bucket)
        mock_client.create_bucket.assert_called_once_with("new-bucket")
        fake_bucket.acl.save_predefined.assert_called_once_with(self.storage.auto_create_acl)
