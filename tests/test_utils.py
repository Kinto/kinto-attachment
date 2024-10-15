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
