import base64
import json
import hashlib
import os

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
                     path=_record_path + '/attachment')


def sha256(filepath):
    with open(filepath) as f:
        m = hashlib.sha256()
        m.update(f.read())
    hash = m.digest()
    return base64.b64encode(hash)


def record_uri(request):
    return request.route_url('record-record', **request.matchdict)


def save_record(record, request):
    backup_pattern = request.matched_route.pattern
    backup_validated = request.validated

    # Instantiate record resource with current request.
    context = RouteFactory(request)
    context.get_permission_object_id = lambda r, i: record_uri
    record_pattern = request.matched_route.pattern.replace('/attachment', '')
    request.matched_route.pattern = record_pattern

    # Simulate update of fields.
    request.validated = {'data': record}
    resource = Record(request, context)
    try:
        saved = resource.patch()
    except httpexceptions.HTTPNotFound:
        saved = resource.put()

    request.matched_route.pattern = backup_pattern
    request.validated = backup_validated
    return saved


@attachment.post(permission=NO_PERMISSION_REQUIRED)
def attachment_post(request):
    # Store file locally.
    content = request.POST[FILE_FIELD]
    filename = request.attachment.save(content)

    # File metadata.
    path = request.attachment.path(filename)
    location = request.attachment.url(filename)
    filesize = os.path.getsize(path)
    filehash = sha256(path)
    metadata = {
        'filename': filename,
        'location': location,
        'hash': filehash,
        'mimetype': content.type,
        'filesize': filesize
    }

    # Update related record.
    attributes = request.POST.get('data', '{}')
    attributes = json.loads(attributes)
    attributes[FILE_FIELD] = metadata
    save_record(attributes, request)

    # Gently redirected to related record.
    raise httpexceptions.HTTPSeeOther(record_uri(request))
