import json
import hashlib

from kinto.core import utils as core_utils
from kinto.core.errors import raise_invalid
from kinto.core.storage import Filter

from kinto.views.records import Record
from kinto.authorization import RouteFactory
from pyramid import httpexceptions
from pyramid_storage.exceptions import FileNotAllowed

FILE_LINKS = '__attachments__'


RECORD_PATH = '/buckets/{bucket_id}/collections/{collection_id}/records/{id}'


class AttachmentRouteFactory(RouteFactory):
    def __init__(self, request):
        """Attachment is not a Kinto resource.

        The required permission is:
        * ``write`` if the related record exists;
        * ``record:create`` on the related collection otherwise.
        """
        super(AttachmentRouteFactory, self).__init__(request)
        self.resource_name = 'record'
        try:
            resource = Record(request, self)
            request.current_resource_name = 'record'
            existing = resource.get()
        except httpexceptions.HTTPNotFound:
            existing = None
        if existing:
            self.permission_object_id = record_uri(request)
            self.required_permission = 'write'
        else:
            self.permission_object_id = collection_uri(request)
            self.required_permission = 'create'


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()


def _object_uri(request, resource_name, matchdict, prefix):
    route_name = '%s-record' % resource_name
    full = request.route_path(route_name, **matchdict)
    if not prefix:
        return core_utils.strip_uri_prefix(full)
    return full


def bucket_uri(request, prefix=False):
    matchdict = dict(request.matchdict)
    matchdict['id'] = matchdict['bucket_id']
    return _object_uri(request, 'bucket', matchdict, prefix)


def collection_uri(request, prefix=False):
    matchdict = dict(request.matchdict)
    matchdict['id'] = matchdict['collection_id']
    return _object_uri(request, 'collection', matchdict, prefix)


def record_uri(request, prefix=False):
    return _object_uri(request, 'record', request.matchdict, prefix)


def patch_record(record, request):
    # XXX: add util clone_request()
    backup_pattern = request.matched_route.pattern
    backup_body = request.body
    backup_validated = request.validated

    # Instantiate record resource with current request.
    context = RouteFactory(request)
    context.get_permission_object_id = lambda r, i: record_uri(r)
    record_pattern = request.matched_route.pattern.replace('/attachment', '')
    request.matched_route.pattern = record_pattern

    # Simulate update of fields.
    request.validated = record
    request.body = json.dumps(record).encode('utf-8')
    resource = Record(request, context)
    request.current_resource_name = 'record'
    try:
        saved = resource.patch()
    except httpexceptions.HTTPNotFound:
        saved = resource.put()

    request.matched_route.pattern = backup_pattern
    request.body = backup_body
    request.validated = backup_validated
    return saved


def delete_attachment(request, link_field=None, uri=None):
    """Delete existing file and link."""
    if link_field is None:
        link_field = "record_uri"
    if uri is None:
        uri = record_uri(request)

    # Remove file.
    filters = [Filter(link_field, uri, core_utils.COMPARISON.EQ)]
    storage = request.registry.storage
    file_links, _ = storage.get_all("", FILE_LINKS, filters=filters)
    for link in file_links:
        request.attachment.delete(link['location'])

    # Remove link.
    storage.delete_all("", FILE_LINKS, filters=filters, with_deleted=False)


def save_file(content, request, randomize=True):
    folder_pattern = request.registry.settings.get('attachment.folder', '')
    folder = folder_pattern.format(**request.matchdict) or None

    try:
        location = request.attachment.save(content, folder=folder,
                                           randomize=randomize)
    except FileNotAllowed:
        error_msg = 'File extension is not allowed.'
        raise_invalid(request, location='body', description=error_msg)

    # Read file to compute hash.
    content.file.seek(0)
    filecontent = content.file.read()

    # File metadata.
    fullurl = request.attachment.url(location)
    size = len(filecontent)
    filehash = sha256(filecontent)
    attachment = {
        'filename': content.filename,
        'location': fullurl,
        'hash': filehash,
        'mimetype': content.type,
        'size': size
    }

    # Store link between record and attachment (for later deletion).
    request.registry.storage.create("", FILE_LINKS, {
        'location': location,  # store relative location.
        'bucket_uri': bucket_uri(request),
        'collection_uri': collection_uri(request),
        'record_uri': record_uri(request)
    })

    return attachment
