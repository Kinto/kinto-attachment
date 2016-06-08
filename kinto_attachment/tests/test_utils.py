from six import BytesIO
import mock

from kinto.tests.core.support import unittest
from kinto_attachment.utils import save_file


class _Registry(object):
    settings = {'attachment.folder': ''}

    def save(self, *args, **kw):
        return 'yeahok'

    def url(self, location):
        return 'http://localhost/%s' % location

    def create(self, *args, **kw):
        pass

    @property
    def storage(self):
        return self


class _Request(object):
    registry = _Registry()
    matchdict = {'bucket_id': 'bucket',
                 'collection_id': 'collection'}

    attachment = _Registry()

    def route_path(self, *args, **kw):
        return 'fullpath'


class TestUtils(unittest.TestCase):

    def test_save_file_gzip(self):
        my_font = mock.Mock()
        my_font.filename = 'font.ttf'
        my_font.file = BytesIO(b'content')
        my_font.type = 'application/x-font'

        request = _Request()
        res = save_file(my_font, request, gzipped=True)
        self.assertTrue('original' in res)

    def test_save_file_not_gzip(self):
        my_font = mock.Mock()
        my_font.filename = 'font.ttf'
        my_font.file = BytesIO(b'content')
        my_font.type = 'application/x-font'

        request = _Request()
        res = save_file(my_font, request)
        self.assertFalse('original' in res)
