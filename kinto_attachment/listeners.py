from kinto.core.events import ResourceChanged, ACTIONS
from pyramid.events import subscriber

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
    # Retrieve attachments for these records using links.
    resource_name = event.payload['resource_name']
    filter_field = '%s_uri' % resource_name
    uri = event.payload['uri']
    utils.delete_attachment(event.request, link_field=filter_field, uri=uri)
