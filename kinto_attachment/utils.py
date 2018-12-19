import cgi
import json
import hashlib
import gzip
from io import BytesIO

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
            request.current_resource_name = 'record'
            request.validated.setdefault('header', {})
            request.validated.setdefault('querystring', {})
            resource = Record(request, context=self)
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
    uri = core_utils.instance_uri(request, resource_name=resource_name, **matchdict)
    if prefix:
        uri = f"/{request.registry.route_prefix}{uri}"
    return uri


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
    context.resource_name = 'record'
    context.get_permission_object_id = lambda r, i: record_uri(r)
    record_pattern = request.matched_route.pattern.replace('/attachment', '')
    request.matched_route.pattern = record_pattern

    # Simulate update of fields.
    request.validated = dict(body=record, **backup_validated)

    request.body = json.dumps(record).encode('utf-8')
    resource = Record(request, context=context)
    setattr(request, '_attachment_auto_save', True)  # Flag in update listener.

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


def save_file(request, content, folder=None, keep_link=True, replace=False):
    gzipped = setting_value(request, 'gzipped', default=False)
    randomize = setting_value(request, 'randomize', default=True)

    # Read file to compute hash.
    if not isinstance(content, cgi.FieldStorage):
        error_msg = 'Filename is required.'
        raise_invalid(request, location='body', description=error_msg)

    # Posted file attributes.
    content.file.seek(0)
    filecontent = content.file.read()
    filehash = sha256(filecontent)
    size = len(filecontent)
    mimetype = content.type
    filename = content.filename

    original = None
    save_options = {'folder': folder, 'randomize': randomize, 'replace': replace}

    if gzipped:
        original = {
            'filename': filename,
            'hash': filehash,
            'mimetype': mimetype,
            'size': size,
        }
        mimetype = 'application/x-gzip'
        filename += '.gz'
        content.filename = filename
        save_options['extensions'] = ['gz']

        # in-memory gzipping
        out = BytesIO()
        with gzip.GzipFile(fileobj=out, mode="w") as f:
            f.write(filecontent)

        filecontent = out.getvalue()
        out.seek(0)
        content.file = out

        # We give the hash and size of the gzip content in the attachment
        # metadata.
        filehash = sha256(filecontent)
        size = len(filecontent)

    try:
        location = request.attachment.save(content, **save_options)
    except FileNotAllowed:
        error_msg = 'File extension is not allowed.'
        raise_invalid(request, location='body', description=error_msg)

    # File metadata.
    fullurl = request.attachment.url(location)
    attachment = {
        'filename': filename,
        'location': fullurl,
        'hash': filehash,
        'mimetype': mimetype,
        'size': size
    }
    if original is not None:
        attachment['original'] = original

    if keep_link:
        # Store link between record and attachment (for later deletion).
        request.registry.storage.create("", FILE_LINKS, {
            'location': location,  # store relative location.
            'bucket_uri': bucket_uri(request),
            'collection_uri': collection_uri(request),
            'record_uri': record_uri(request)
        })

    return attachment


def setting_value(request, name, default):
    value = request.registry.settings.get('attachment.{}'.format(name), default)
    if 'bucket_id' in request.matchdict:
        uri = '/buckets/{bucket_id}'.format(**request.matchdict)
        if uri in request.registry.attachment_resources:
            value = request.registry.attachment_resources[uri].get(name, value)
        if 'collection_id' in request.matchdict:
            uri = '/buckets/{bucket_id}/collections/{collection_id}'.format(**request.matchdict)
            if uri in request.registry.attachment_resources:
                value = request.registry.attachment_resources[uri].get(name, value)
    return value
