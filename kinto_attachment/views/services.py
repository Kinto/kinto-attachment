from kinto.core import Service
from kinto.core.authorization import DYNAMIC as DYNAMIC_PERMISSION

from kinto_attachment import utils
from . import post_attachment_view, delete_attachment_view

SINGLE_FILE_FIELD = 'attachment'

attachment = Service(name='attachment',
                     description='Attach a file to a record',
                     path=utils.RECORD_PATH + '/attachment',
                     cors_enabled=True,
                     cors_origins='*',
                     factory=utils.AttachmentRouteFactory)


@attachment.post(permission=DYNAMIC_PERMISSION)
def attachment_post(request):
    return post_attachment_view(request, SINGLE_FILE_FIELD)


@attachment.delete(permission=DYNAMIC_PERMISSION)
def attachment_delete(request):
    return delete_attachment_view(request, SINGLE_FILE_FIELD)
