import json
from io import BytesIO

from pyramid import httpexceptions
from pyramid.settings import asbool
from kinto.core import logger
from kinto.core.errors import ERRORS, http_error

from kinto_attachment import utils

HEARTBEAT_CONTENT = '{"test": "write"}'
HEARTBEAT_FILENAME = 'heartbeat.json'


def post_attachment_view(request, file_field):
    settings = request.registry.settings
    keep_old_files = asbool(settings.get('attachment.keep_old_files', False))

    if not keep_old_files:
        # Remove potential existing attachment.
        utils.delete_attachment(request)

    if "multipart/form-data" not in request.headers.get('Content-Type', ''):
        raise http_error(httpexceptions.HTTPBadRequest(),
                         errno=ERRORS.INVALID_PARAMETERS,
                         message="Content-Type should be multipart/form-data")

    # Store file locally.
    try:
        content = request.POST.get(file_field)
    except ValueError as e:
        raise http_error(httpexceptions.HTTPBadRequest(),
                         errno=ERRORS.INVALID_PARAMETERS.value,
                         message=str(e))

    if content is None:
        raise http_error(httpexceptions.HTTPBadRequest(),
                         errno=ERRORS.INVALID_POSTED_DATA,
                         message="Attachment missing.")

    # Per resource settings
    resource_settings = {
        'gzipped': asbool(settings.get('attachment.gzipped', False)),
        'use_content_encoding': asbool(settings.get('attachment.use_content_encoding', False))
    }

    cid = '/buckets/{bucket_id}/collections/{collection_id}'.format_map(request.matchdict)
    bid = '/buckets/{bucket_id}'.format_map(request.matchdict)

    if bid in request.registry.attachment_resources:
        resource_settings.update(request.registry.attachment_resources[bid])

    if cid in request.registry.attachment_resources:
        resource_settings.update(request.registry.attachment_resources[cid])

    randomize = True
    if 'randomize' in request.GET:
        randomize = asbool(request.GET['randomize'])

    gzipped = resource_settings['gzipped']
    if 'gzipped' in request.GET:
        gzipped = asbool(request.GET['gzipped'])

    use_content_encoding = resource_settings['use_content_encoding']
    if 'use_content_encoding' in request.GET:
        use_content_encoding = asbool(request.GET['use_content_encoding'])

    attachment = utils.save_file(content, request, randomize=randomize,
                                 gzipped=gzipped,
                                 use_content_encoding=use_content_encoding)

    # Update related record.
    posted_data = {k: v for k, v in request.POST.items() if k != file_field}
    record = {'data': {}}
    for field in ('data', 'permissions'):
        if field in posted_data:
            try:
                record[field] = json.loads(posted_data.pop(field))
            except ValueError as e:
                error_msg = "body: %s is not valid JSON (%s)" % (field, str(e))
                raise http_error(httpexceptions.HTTPBadRequest(),
                                 errno=ERRORS.INVALID_POSTED_DATA,
                                 message=error_msg)
    # Some fields remaining in posted_data after popping: invalid!
    for field in posted_data.keys():
        error_msg = "body: %r not in ('data', 'permissions')" % field
        raise http_error(httpexceptions.HTTPBadRequest(),
                         errno=ERRORS.INVALID_POSTED_DATA,
                         message=error_msg)

    record['data'][file_field] = attachment

    utils.patch_record(record, request)

    # Return attachment data (with location header)
    request.response.headers['Location'] = utils.record_uri(request,
                                                            prefix=True)
    return attachment


def delete_attachment_view(request, file_field):
    settings = request.registry.settings
    keep_old_files = asbool(settings.get('attachment.keep_old_files', False))

    print(keep_old_files)
    if not keep_old_files:
        utils.delete_attachment(request)

    # Remove metadata.
    record = {"data": {}}
    record["data"][file_field] = None
    utils.patch_record(record, request)

    raise httpexceptions.HTTPNoContent()


def attachments_ping(request):
    """Heartbeat view for the attachments backend.
    :returns: ``True`` if succeeds to write and delete, ``False`` otherwise.
    """
    # Do nothing if server is readonly.
    if asbool(request.registry.settings.get('readonly', False)):
        return True

    status = False
    attachment = request.attachment
    try:
        location = attachment.save_file(BytesIO(HEARTBEAT_CONTENT.encode('utf-8')),
                                        HEARTBEAT_FILENAME,
                                        replace=True)
        attachment.delete(location)
        status = True
    except Exception as e:
        logger.exception(e)
    return status
