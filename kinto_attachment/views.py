import base64
import json
import hashlib

from cliquet import Service
from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.views.records import Record
from kinto.authorization import RouteFactory


FILE_FIELD = 'attachment'


_record_path = ('/buckets/{bucket_id}/collections/{collection_id}'
                '/records/{id}')

attachment = Service(name='attachment',
                     description='Attach file to record',
                     path=_record_path + '/attachment',
                     cors_enabled=True,
                     cors_origins='*')


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    hash = m.digest()
    return base64.b64encode(hash)


def record_uri(request):
    return request.route_url('record-record', **request.matchdict)


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
    try:
        saved = resource.patch()
    except httpexceptions.HTTPNotFound:
        saved = resource.put()

    request.matched_route.pattern = backup_pattern
    request.body = backup_body
    request.validated = backup_validated
    return saved


@attachment.post(permission=NO_PERMISSION_REQUIRED)
def attachment_post(request):
    # Store file locally.
    content = request.POST[FILE_FIELD]
    filename = request.attachment.save(content)

    content.file.seek(0)
    filecontent = content.file.read()

    # File metadata.
    location = request.attachment.url(filename)
    filesize = len(filecontent)
    filehash = sha256(filecontent)
    metadata = {
        'filename': filename,
        'location': location,
        'hash': filehash,
        'mimetype': content.type,
        'filesize': filesize
    }

    # Update related record.
    record = {k: v for k, v in request.POST.items() if k != FILE_FIELD}
    for k, v in record.items():
        record[k] = json.loads(v)
    record.setdefault('data', {})[FILE_FIELD] = metadata
    save_record(record, request)

    # Gently redirected to related record.
    raise httpexceptions.HTTPSeeOther(record_uri(request))
