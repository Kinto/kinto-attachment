import io


class MockFS:
    """Minimal cgi.FieldStorage-like object for testing storage backends."""

    def __init__(self, filename, data=b""):
        self.filename = filename
        self.file = io.BytesIO(data)


class _FakeGCSBucket:
    def __init__(self):
        self._blobs = {}

    def get_blob(self, name):
        return self._blobs.get(name)

    def delete_blob(self, name):
        self._blobs.pop(name, None)


class _FakeGCSBlob:
    def __init__(self, name, bucket):
        self.name = name
        self._bucket = bucket
        self.cache_control = None

    def upload_from_file(self, file, **kwargs):
        self._bucket._blobs[self.name] = self


class _FakeGCSClient:
    def __init__(self, **kwargs):
        self._bucket = _FakeGCSBucket()

    @classmethod
    def from_service_account_json(cls, **kwargs):
        return cls()

    def get_bucket(self, name):
        return self._bucket
