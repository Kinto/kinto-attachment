import io
import os
import shutil
import tempfile
import unittest

from pyramid.exceptions import ConfigurationError

from kinto_attachment.storage.local import LocalFileStorage
from tests.storage import MockFS


class TestLocalFileStorage(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = LocalFileStorage(base_path=self.tmpdir, base_url="http://example.com/")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_from_settings(self):
        s = LocalFileStorage.from_settings(
            {"storage.base_path": self.tmpdir, "storage.base_url": "http://cdn.com/"},
            prefix="storage.",
        )
        self.assertEqual(s.base_path, self.tmpdir)
        self.assertEqual(s.base_url, "http://cdn.com/")

    def test_from_settings_base_url_defaults_to_empty(self):
        s = LocalFileStorage.from_settings({"storage.base_path": self.tmpdir}, prefix="storage.")
        self.assertEqual(s.base_url, "")

    def test_from_settings_requires_base_path(self):
        with self.assertRaises(ConfigurationError):
            LocalFileStorage.from_settings({}, prefix="storage.")

    def test_url_joins_base_url_and_filename(self):
        self.assertEqual(self.storage.url("foo.jpg"), "http://example.com/foo.jpg")

    def test_path_joins_base_path_and_filename(self):
        self.assertEqual(self.storage.path("foo.jpg"), os.path.join(self.tmpdir, "foo.jpg"))

    def test_exists_returns_false_for_missing_file(self):
        self.assertFalse(self.storage.exists("missing.jpg"))

    def test_exists_returns_true_after_save(self):
        self.storage.save_file(io.BytesIO(b"data"), "photo.jpg")
        self.assertTrue(self.storage.exists("photo.jpg"))

    def test_delete_removes_file(self):
        self.storage.save_file(io.BytesIO(b"data"), "photo.jpg")
        self.storage.delete("photo.jpg")
        self.assertFalse(self.storage.exists("photo.jpg"))

    def test_delete_returns_true_when_file_existed(self):
        self.storage.save_file(io.BytesIO(b"data"), "photo.jpg")
        self.assertTrue(self.storage.delete("photo.jpg"))

    def test_delete_returns_false_when_file_missing(self):
        self.assertFalse(self.storage.delete("ghost.jpg"))

    def test_save_accepts_fieldStorage_object(self):
        name = self.storage.save(MockFS("image.jpg", b"binary"))
        self.assertEqual(name, "image.jpg")
        self.assertTrue(self.storage.exists("image.jpg"))

    def test_save_file_returns_filename(self):
        name = self.storage.save_file(io.BytesIO(b"data"), "test.txt")
        self.assertEqual(name, "test.txt")

    def test_save_file_writes_content(self):
        self.storage.save_file(io.BytesIO(b"hello"), "hello.txt")
        with open(self.storage.path("hello.txt"), "rb") as f:
            self.assertEqual(f.read(), b"hello")

    def test_save_file_with_folder(self):
        name = self.storage.save_file(io.BytesIO(b"data"), "doc.pdf", folder="a/b")
        self.assertEqual(name, os.path.join("a", "b", "doc.pdf"))
        self.assertTrue(os.path.exists(os.path.join(self.tmpdir, "a", "b", "doc.pdf")))

    def test_save_file_creates_missing_directories(self):
        self.storage.save_file(io.BytesIO(b"x"), "f.txt", folder="deep/nested/dir")
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, "deep", "nested", "dir")))

    def test_save_file_randomizes_filename(self):
        name = self.storage.save_file(io.BytesIO(b"data"), "original.jpg", randomize=True)
        self.assertNotEqual(name, "original.jpg")
        self.assertTrue(name.endswith(".jpg"))
        self.assertTrue(self.storage.exists(name))

    def test_save_file_resolves_name_collision(self):
        self.storage.save_file(io.BytesIO(b"first"), "file.txt")
        name = self.storage.save_file(io.BytesIO(b"second"), "file.txt")
        self.assertEqual(name, "file-1.txt")
        self.assertTrue(self.storage.exists("file.txt"))
        self.assertTrue(self.storage.exists("file-1.txt"))

    def test_save_file_resolves_multiple_collisions(self):
        for _ in range(3):
            self.storage.save_file(io.BytesIO(b"x"), "x.txt")
        self.assertTrue(self.storage.exists("x-2.txt"))

    def test_save_file_strips_directory_from_filename(self):
        # An attacker-controlled filename with path traversal should be sanitised.
        name = self.storage.save_file(io.BytesIO(b"x"), "../escape.txt")
        self.assertNotIn("..", name)
        self.assertFalse(os.path.exists(os.path.join(self.tmpdir, "..", "escape.txt")))
