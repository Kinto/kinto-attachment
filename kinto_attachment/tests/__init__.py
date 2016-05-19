import uuid
import os

import webtest
from kinto.core import utils as core_utils
from kinto.tests.core import support as core_support
from pyramid_storage.s3 import S3FileStorage
from pyramid_storage.interfaces import IFileStorage


SAMPLE_SCHEMA = {
    "title": "Font file",
    "type": "object",
    "properties": {
        "family": {"type": "string"},
        "author": {"type": "string"},
    }
}


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(core_utils.encode64(credentials))
    return {
        'Authorization': authorization
    }


class BaseWebTest(object):
    config = ''

    def __init__(self, *args, **kwargs):
        super(BaseWebTest, self).__init__(*args, **kwargs)
        self.app = self.make_app()
        self.backend = self.app.app.registry.getUtility(IFileStorage)
        self.base_url = self.backend.url('')
        self._created = []

    def setUp(self):
        super(BaseWebTest, self).setUp()
        self.headers = {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:9999'
        }
        self.headers.update(get_user_headers('mat'))

        self.create_collection('fennec', 'fonts')
        self.record_id = _id = str(uuid.uuid4())
        self.record_uri = self.get_record_uri('fennec', 'fonts', _id)
        self.endpoint_uri = self.record_uri + '/attachment'
        self.default_files = [('attachment', 'image.jpg', b'--fake--')]
        self.file_field = 'attachment'

    @property
    def nb_uploaded_files(self):
        return len(self.default_files)

    def make_app(self):
        curdir = os.path.dirname(os.path.realpath(__file__))
        app = webtest.TestApp("config:%s" % self.config, relative_to=curdir)
        app.RequestClass = core_support.get_request_class(prefix="v1")
        return app

    def upload(self, files=None, params=[], headers={}, status=None,
               randomize=True):
        files = files or self.default_files
        headers = headers or self.headers.copy()
        content_type, body = self.app.encode_multipart(params, files)
        headers['Content-Type'] = core_utils.encode_header(content_type)

        if not randomize:
            endpoint_url = self.endpoint_uri + '?randomize=false'
        else:
            endpoint_url = self.endpoint_uri

        resp = self.app.post(endpoint_url, body, headers=headers,
                             status=status)
        if 200 <= resp.status_code < 300:
            self._add_to_cleanup(resp.json)

        return resp

    def _add_to_cleanup(self, attachment):
        relativeurl = attachment['location'].replace(self.base_url, '')
        self._created.append(relativeurl)

    def create_collection(self, bucket_id, collection_id):
        bucket_uri = '/buckets/%s' % bucket_id
        self.app.put_json(bucket_uri,
                          {},
                          headers=self.headers)
        collection_uri = bucket_uri + '/collections/%s' % collection_id
        collection = {
            'schema': SAMPLE_SCHEMA
        }
        self.app.put_json(collection_uri,
                          {'data': collection},
                          headers=self.headers)

    def get_record_uri(self, bucket_id, collection_id, record_id):
        return ('/buckets/{bucket_id}/collections/{collection_id}'
                '/records/{record_id}').format(**locals())

    def get_record(self, resp):
        # Alias to resp.json, in a separate method to easily be extended.
        return resp.json


class BaseWebTestLocal(BaseWebTest):
    config = 'config/local.ini'

    def tearDown(self):
        """Delete uploaded local files.
        """
        super(BaseWebTest, self).tearDown()
        basepath = self.app.app.registry.settings['kinto.attachment.base_path']
        for created in self._created:
            filepath = os.path.join(basepath, created)
            if os.path.exists(filepath):
                os.remove(filepath)


class BaseWebTestS3(BaseWebTest):
    config = 'config/s3.ini'

    def __init__(self, *args, **kwargs):
        self._s3_bucket_created = False
        super(BaseWebTestS3, self).__init__(*args, **kwargs)

    def make_app(self):
        app = super(BaseWebTestS3, self).make_app()

        # Create the S3 bucket if necessary
        if not self._s3_bucket_created:
            prefix = 'kinto.attachment.'
            settings = app.app.registry.settings
            fs = S3FileStorage.from_settings(settings, prefix=prefix)

            bucket_name = settings[prefix + 'aws.bucket_name']
            fs.get_connection().create_bucket(bucket_name)
            self._s3_bucket_created = True

        return app
