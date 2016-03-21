import json

from pyramid import httpexceptions
from pyramid.settings import asbool
from cliquet import logger
from six import StringIO

from kinto_attachment import utils

HEARTBEAT_CONTENT = '{"test": "write"}'
HEARTBEAT_FILENAME = 'heartbeat.json'


def post_attachment_view(request, file_field, randomize=True,
                         multiple_attachments=False):
    settings = request.registry.settings
    keep_old_files = asbool(settings.get('attachment.keep_old_files', False))
    if multiple_attachments or not keep_old_files:
        # Remove potential existing attachment.
        utils.delete_attachment(request)

    # Store file locally.
    contents = request.POST.getall(file_field)
    attachments = []
    for content in contents:
        attachment = utils.save_file(content, request, randomize=randomize)
        attachments.append(attachment)
    # Update related record.
    record = {k: v for k, v in request.POST.items() if k != file_field}
    for k, v in record.items():
        record[k] = json.loads(v)

    if not multiple_attachments:
        attachments = attachments[0]

    record.setdefault('data', {})[file_field] = attachments
    utils.patch_record(record, request)

    # Return attachment data (with location header)
    request.response.headers['Location'] = utils.record_uri(request,
                                                            prefix=True)
    return attachments


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
