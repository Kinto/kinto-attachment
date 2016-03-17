from cliquet import Service
from cliquet.authorization import DYNAMIC as DYNAMIC_PERMISSION

from kinto_attachment import utils
from . import post_attachment_view, delete_attachment_view

SINGLE_FILE_FIELD = 'attachment'
MULTIPLE_FILE_FIELD = 'attachments'


attachment = Service(name='attachment',
                     description='Attach a file to a record',
                     path=utils.RECORD_PATH + '/attachment',
                     cors_enabled=True,
                     cors_origins='*',
                     factory=utils.AttachmentRouteFactory)


@attachment.post(permission=DYNAMIC_PERMISSION)
def attachment_post(request):
    return post_attachment_view(request, SINGLE_FILE_FIELD, randomize=True,
                                multiple_attachments=False)


@attachment.delete(permission=DYNAMIC_PERMISSION)
def attachment_delete(request):
    return delete_attachment_view(request, SINGLE_FILE_FIELD)


attachments = Service(name='attachments',
                      description='Attach files to record',
                      path=utils.RECORD_PATH + '/attachments',
                      cors_enabled=True,
                      cors_origins='*',
                      factory=utils.AttachmentRouteFactory)


@attachments.post(permission=DYNAMIC_PERMISSION)
def attachments_post(request):
    return post_attachment_view(request, MULTIPLE_FILE_FIELD,
                                randomize=False,
                                multiple_attachments=True)


@attachments.delete(permission=DYNAMIC_PERMISSION)
def attachments_delete(request):
    return delete_attachment_view(request, MULTIPLE_FILE_FIELD)
