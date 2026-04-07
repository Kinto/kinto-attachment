import unittest

from kinto_attachment.utils import _extension_allowed, resolve_extensions


class TestResolveExtensions(unittest.TestCase):
    def test_known_group_name(self):
        self.assertIn("jpg", resolve_extensions("images"))

    def test_plus_combines_groups(self):
        result = resolve_extensions("images+documents")
        self.assertIn("jpg", result)
        self.assertIn("pdf", result)

    def test_explicit_extensions_not_in_groups(self):
        result = resolve_extensions("mp4 avi")
        self.assertIn("mp4", result)
        self.assertIn("avi", result)

    def test_any_returns_empty_set(self):
        self.assertEqual(resolve_extensions("any"), set())


class TestExtensionAllowed(unittest.TestCase):
    def test_allowed_extension(self):
        self.assertTrue(_extension_allowed("photo.jpg", {"jpg", "png"}))

    def test_disallowed_extension(self):
        self.assertFalse(_extension_allowed("virus.exe", {"jpg", "png"}))

    def test_empty_set_allows_everything(self):
        self.assertTrue(_extension_allowed("virus.exe", set()))


class _Registry(object):
    settings = {"attachment.folder": ""}
    attachment_resources = {}

    def save(self, *args, **kw):
        return "yeahok"

    def url(self, location):
        return "http://localhost/%s" % location

    def create(self, *args, **kw):
        pass

    @property
    def storage(self):
        return self


class _Request(object):
    registry = _Registry()
    matchdict = {"bucket_id": "bucket", "collection_id": "collection"}

    attachment = _Registry()

    def route_path(self, *args, **kw):
        return "fullpath"
