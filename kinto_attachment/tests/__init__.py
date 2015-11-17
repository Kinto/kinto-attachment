import uuid
import os

import mock
import webtest
from cliquet import utils as cliquet_utils
from cliquet.tests import support as cliquet_support


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(cliquet_utils.encode64(credentials))
    return {
        'Authorization': authorization
    }


class BaseWebTestLocal(object):
    def __init__(self, *args, **kwargs):
        super(BaseWebTestLocal, self).__init__(*args, **kwargs)
        self.app = self.make_app()
        self.storage = self.app.app.registry.storage

    def setUp(self):
        super(BaseWebTestLocal, self).setUp()
        self.headers = {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:9999'
        }
        self.headers.update(get_user_headers('mat'))

        self.create_collection('fennec', 'fonts')
        self.record_uri = self.record_uri('fennec', 'fonts', uuid.uuid4())
        self.attachment_uri = self.record_uri + '/attachment'

    def make_app(self, config='config/local.ini'):
        curdir = os.path.dirname(os.path.realpath(__file__))
        app = webtest.TestApp("config:%s" % config, relative_to=curdir)
        app.RequestClass = cliquet_support.get_request_class(prefix="v1")
        return app

    def upload(self, files=None, params=[], headers={}, status=None):
        files = files or [('attachment', 'image.jpg', '--fake--')]
        headers = headers or self.headers.copy()
        content_type, body = self.app.encode_multipart(params, files)
        headers['Content-Type'] = cliquet_utils.encode_header(content_type)
        return self.app.post(self.attachment_uri, body, headers=headers,
                             status=status)

    def create_collection(self, bucket_id, collection_id):
        bucket_uri = '/buckets/%s' % bucket_id
        self.app.put_json(bucket_uri,
                          {},
                          headers=self.headers)
        self.app.put_json(bucket_uri + '/collections/%s' % collection_id,
                          {},
                          headers=self.headers)

    def record_uri(self, bucket_id, collection_id, record_id):
        return ('/buckets/{bucket_id}/collections/{collection_id}'
                '/records/{record_id}').format(**locals())


class BaseWebTestS3(BaseWebTestLocal):
    def make_app(self, config='config/s3.ini'):
        return super(BaseWebTestS3, self).make_app(config)

    def upload(self, *args, **kwargs):
        # XXX: use moto_server instead.
        patch = mock.patch('pyramid_storage.s3.S3FileStorage.save_file',
                           return_value='upload.jpg')
        with patch.start():
            return super(BaseWebTestS3, self).upload(*args, **kwargs)
