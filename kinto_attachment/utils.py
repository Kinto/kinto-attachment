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
from pyramid_storage.local import LocalFileStorage
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


def save_file(content, request, randomize=True, gzipped=False,
              use_content_encoding=False):
    folder_pattern = request.registry.settings.get('attachment.folder', '')
    folder = folder_pattern.format(**request.matchdict) or None

    # Read file to compute hash.
    if not isinstance(content, cgi.FieldStorage):
        error_msg = 'Filename is required.'
        raise_invalid(request, location='body', description=error_msg)

    content.file.seek(0)
    filecontent = content.file.read()
    filehash = sha256(filecontent)
    size = len(filecontent)

    original = None
    save_options = {'folder': folder,
                    'randomize': randomize}

    should_gzip_content = False

    if use_content_encoding:
        # Http will decompress gzipped data automatically if the header
        # 'Content-Encoding' is present. So, this mimetype here we can
        # still use the original one as well as the file name.
        mimetype = content.type
        filename = content.filename
        save_options['headers'] = {
            'content-type': mimetype,
            'content-encoding': 'gzip'
        }
        should_gzip_content = not isinstance(request.attachment, LocalFileStorage)

    elif gzipped:
        original = {
            'filename': content.filename,
            'hash': filehash,
            'mimetype': content.type,
            'size': size,
        }
        mimetype = 'application/x-gzip'
        filename = content.filename + '.gz'
        save_options['extensions'] = ['gz']
        should_gzip_content = True

    if should_gzip_content:
        # in-memory gzipping
        out = BytesIO()
        with gzip.GzipFile(fileobj=out, mode="w") as f:
            f.write(filecontent)

        filecontent = out.getvalue()
        out.seek(0)
        content.file = out
        content.filename = filename
        if not use_content_encoding:
            filehash = sha256(filecontent)
            size = len(filecontent)
    else:
        mimetype = content.type
        filename = content.filename

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

    # Store link between record and attachment (for later deletion).
    request.registry.storage.create("", FILE_LINKS, {
        'location': location,  # store relative location.
        'bucket_uri': bucket_uri(request),
        'collection_uri': collection_uri(request),
        'record_uri': record_uri(request)
    })

    return attachment
