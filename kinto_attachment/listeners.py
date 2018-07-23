from kinto.core.events import ResourceChanged, ACTIONS
from kinto.core.errors import http_error
from pyramid.events import subscriber
from pyramid.exceptions import HTTPBadRequest
from pyramid.settings import asbool

from . import utils


# XXX: Use AfterResourceChanged when implemented.
@subscriber(ResourceChanged,
            for_resources=('record', 'collection', 'bucket'),
            for_actions=(ACTIONS.DELETE,))
def on_delete_record(event):
    """When a resource record is deleted, delete all related attachments.
    When a bucket or collection is deleted, it removes the attachments of
    every underlying records.
    """
    keep_old_files = asbool(utils.setting_value(event.request, 'keep_old_files', default=False))
    if keep_old_files:
        return

    # Retrieve attachments for these records using links.
    resource_name = event.payload['resource_name']
    filter_field = '%s_uri' % resource_name
    uri = event.payload['uri']
    utils.delete_attachment(event.request, link_field=filter_field, uri=uri)


@subscriber(ResourceChanged,
            for_resources=('record',),
            for_actions=(ACTIONS.UPDATE,))
def on_update_record(event):
    if getattr(event.request, '_attachment_auto_save', False):
        # Record attributes are being by the plugin itself.
        return

    # A user is changing the record, make sure attachment metadata is not
    # altered manually.
    for change in event.impacted_records:
        attachment_before = change['old'].get('attachment')
        attachment_after = change['new'].get('attachment')
        if attachment_before and attachment_after:
            if attachment_before != attachment_after:
                error_msg = "Attachment metadata cannot be modified."
                raise http_error(HTTPBadRequest(), message=error_msg)
