import json

from pyramid import httpexceptions
from pyramid.settings import asbool
from kinto.core import logger
from kinto.core.errors import ERRORS, http_error
from six import StringIO

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

    randomize = True
    if 'randomize' in request.GET:
        randomize = asbool(request.GET['randomize'])

    gzipped = asbool(settings.get('attachment.gzipped', False))
    if 'gzipped' in request.GET:
        gzipped = asbool(request.GET['gzipped'])

    attachment = utils.save_file(content, request, randomize=randomize,
                                 gzipped=gzipped)

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
        location = attachment.save_file(StringIO(HEARTBEAT_CONTENT),
                                        HEARTBEAT_FILENAME,
                                        replace=True)
        attachment.delete(location)
        status = True
    except Exception as e:
        logger.exception(e)
    return status
