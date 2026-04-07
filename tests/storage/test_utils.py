import unittest

from pyramid.exceptions import ConfigurationError

from kinto_attachment.storage import random_filename, read_settings, secure_filename


class TestSecureFilename(unittest.TestCase):
    def test_strips_path_separators(self):
        # os.sep is replaced by a space, then spaces become underscores
        self.assertEqual(secure_filename("foo/bar.txt"), "foo_bar.txt")

    def test_replaces_spaces_with_underscores(self):
        self.assertEqual(secure_filename("my file.txt"), "my_file.txt")

    def test_unicode_is_ascii_folded(self):
        # NFKD decomposition maps ö → o + combining umlaut; the combining char is dropped
        self.assertEqual(secure_filename("höhle.txt"), "hohle.txt")

    def test_strips_leading_dots_and_underscores(self):
        self.assertEqual(secure_filename("...hidden"), "hidden")

    def test_preserves_extension(self):
        result = secure_filename("photo.JPG")
        self.assertTrue(result.endswith(".JPG"))

    def test_strips_non_ascii_characters(self):
        self.assertEqual(secure_filename("тест.jpg"), "jpg")

    def test_empty_string_stays_empty(self):
        self.assertEqual(secure_filename(""), "")


class TestRandomFilename(unittest.TestCase):
    def test_preserves_extension(self):
        name = random_filename("report.pdf")
        self.assertTrue(name.endswith(".pdf"))

    def test_lowercases_extension(self):
        name = random_filename("photo.JPG")
        self.assertTrue(name.endswith(".jpg"))

    def test_different_on_each_call(self):
        self.assertNotEqual(random_filename("a.txt"), random_filename("a.txt"))

    def test_uuid_format(self):
        import uuid

        name = random_filename("x.png")
        stem = name[: -len(".png")]
        uuid.UUID(stem)  # raises if not valid UUID


class TestReadSettings(unittest.TestCase):
    def test_reads_value_from_settings(self):
        result = read_settings({"p.key": "val"}, [("key", False, None)], prefix="p.")
        self.assertEqual(result["key"], "val")

    def test_uses_default_when_missing(self):
        result = read_settings({}, [("key", False, "default")], prefix="p.")
        self.assertEqual(result["key"], "default")

    def test_raises_when_required_missing(self):
        with self.assertRaises(ConfigurationError):
            read_settings({}, [("key", True, None)], prefix="p.")

    def test_required_present_does_not_raise(self):
        result = read_settings({"p.key": "v"}, [("key", True, None)], prefix="p.")
        self.assertEqual(result["key"], "v")
