import cgi
import json
from io import BytesIO

from kinto.core import logger, Service
from kinto.core.authorization import DYNAMIC as DYNAMIC_PERMISSION
from kinto.core.errors import ERRORS, http_error
from pyramid import httpexceptions
from pyramid.settings import asbool

from kinto_attachment import utils


HEARTBEAT_CONTENT = '{"test": "write"}'
HEARTBEAT_FILENAME = 'heartbeat'
SINGLE_FILE_FIELD = 'attachment'


attachment = Service(name='attachment',
                     description='Attach a file to a record',
                     path=utils.RECORD_PATH + '/attachment',
                     factory=utils.AttachmentRouteFactory)


@attachment.post(permission=DYNAMIC_PERMISSION)
def attachment_post(request):
    return post_attachment_view(request, SINGLE_FILE_FIELD)


@attachment.delete(permission=DYNAMIC_PERMISSION)
def attachment_delete(request):
    return delete_attachment_view(request, SINGLE_FILE_FIELD)


def post_attachment_view(request, file_field):
    keep_old_files = asbool(utils.setting_value(request, 'keep_old_files', default=False))

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

    folder_pattern = utils.setting_value(request, 'folder', default='')
    folder = folder_pattern.format(**request.matchdict) or None
    attachment = utils.save_file(request, content, folder=folder)

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
    keep_old_files = asbool(utils.setting_value(request, 'keep_old_files', default=False))

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

    # We will fake a file upload, so pick a file extension that is allowed.
    extensions = request.attachment.extensions or {'json'}
    allowed_extension = "." + list(extensions)[-1]

    status = False
    try:
        content = cgi.FieldStorage()
        content.filename = HEARTBEAT_FILENAME + allowed_extension
        content.file = BytesIO(HEARTBEAT_CONTENT.encode('utf-8'))
        content.type = 'application/octet-stream'

        stored = utils.save_file(request, content, keep_link=False, replace=True)

        relative_location = stored['location'].replace(request.attachment.base_url, '')
        request.attachment.delete(relative_location)

        status = True
    except Exception as e:
        logger.exception(e)
    return status
