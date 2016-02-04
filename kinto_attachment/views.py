import json
import hashlib

from cliquet import Service
from cliquet import utils as cliquet_utils
from cliquet.errors import raise_invalid
from cliquet.storage import Filter
from cliquet.events import ResourceChanged
from cliquet.authorization import DYNAMIC as DYNAMIC_PERMISSION
from kinto.views.records import Record
from kinto.authorization import RouteFactory
from pyramid.events import subscriber
from pyramid import httpexceptions
from pyramid_storage.exceptions import FileNotAllowed


FILE_FIELD = 'attachment'
FILE_LINKS = '__attachments__'


class AttachmentRouteFactory(RouteFactory):
    def __init__(self, request):
        """Attachment is not a Cliquet resource.

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


_record_path = ('/buckets/{bucket_id}/collections/{collection_id}'
                '/records/{id}')

attachment = Service(name='attachment',
                     description='Attach file to record',
                     path=_record_path + '/attachment',
                     cors_enabled=True,
                     cors_origins='*',
                     factory=AttachmentRouteFactory)


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()


def _object_uri(request, resource_name, matchdict, prefix):
    route_name = '%s-record' % resource_name
    full = request.route_path(route_name, **matchdict)
    if not prefix:
        return cliquet_utils.strip_uri_prefix(full)
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


def save_record(record, request):
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
    request.body = json.dumps(record)
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


def delete_attachment(request):
    """Delete existing file and link."""
    storage = request.registry.storage
    uri = record_uri(request)
    filters = [Filter("record_uri", uri, cliquet_utils.COMPARISON.EQ)]

    # Remove file.
    file_links, _ = storage.get_all("", FILE_LINKS, filters=filters)
    for link in file_links:
        request.attachment.delete(link['location'])

    # Remove link.
    storage.delete_all("", FILE_LINKS, filters=filters, with_deleted=False)


@subscriber(ResourceChanged)
def on_delete_record(event):
    """When a resource record is deleted, delete all related attachments.
    When a bucket or collection is deleted, it removes the attachments of
    every underlying records.
    """
    if event.payload['action'] != 'delete':
        return

    resource_name = event.payload['resource_name']
    if resource_name not in ('record', 'collection', 'bucket'):
        return

    # Retrieve attachments for these records using links.
    storage = event.request.registry.storage
    uri = event.payload['uri']
    filter_field = '%s_uri' % resource_name
    filters = [Filter(filter_field, uri, cliquet_utils.COMPARISON.EQ)]
    file_links, _ = storage.get_all("", FILE_LINKS, filters=filters)

    # Delete attachment files.
    # XXX: add bulk delete for s3 ?
    for link in file_links:
        event.request.attachment.delete(link['location'])

    # Delete links between records and attachements.
    storage.delete_all("", FILE_LINKS, filters=filters, with_deleted=False)


@attachment.post(permission=DYNAMIC_PERMISSION)
def attachment_post(request):
    # Remove potential existing attachment.
    delete_attachment(request)

    # Store file locally.
    folder_pattern = request.registry.settings.get('attachment.folder', '')
    folder = folder_pattern.format(**request.matchdict) or None
    content = request.POST[FILE_FIELD]
    try:
        location = request.attachment.save(content,
                                           randomize=True,
                                           folder=folder)
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

    # Update related record.
    record = {k: v for k, v in request.POST.items() if k != FILE_FIELD}
    for k, v in record.items():
        record[k] = json.loads(v)
    record.setdefault('data', {})[FILE_FIELD] = attachment
    save_record(record, request)

    # Return attachment data (with location header)
    request.response.headers['Location'] = record_uri(request, prefix=True)
    return attachment


@attachment.delete(permission=DYNAMIC_PERMISSION)
def attachment_delete(request):
    delete_attachment(request)

    # Remove metadata.
    record = {"data": {}}
    record["data"][FILE_FIELD] = None
    save_record(record, request)

    raise httpexceptions.HTTPNoContent()
