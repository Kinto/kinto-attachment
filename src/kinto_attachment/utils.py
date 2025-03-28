import cgi
import hashlib
import json
import os

from kinto.authorization import RouteFactory
from kinto.core import utils as core_utils
from kinto.core.errors import raise_invalid
from kinto.core.storage import Filter
from kinto.views.records import Record
from pyramid import httpexceptions
from pyramid_storage.exceptions import FileNotAllowed


FILE_LINKS = "__attachments__"

RECORD_PATH = "/buckets/{bucket_id}/collections/{collection_id}/records/{id}"

DEFAULT_MIMETYPES = {
    ".pem": "application/x-pem-file",
    ".geojson": "application/geojson",
}


class AttachmentRouteFactory(RouteFactory):
    def __init__(self, request):
        """
        This class is the `context` object being passed to the
        :class:`kinto.core.authorization.AuthorizationPolicy`.

        Attachment is not a Kinto resource.

        The required permission is:
        * ``write`` if the related record exists;
        * ``record:create`` on the related collection otherwise.
        """
        super(AttachmentRouteFactory, self).__init__(request)
        self.resource_name = "record"
        try:
            request.current_resource_name = "record"
            request.validated.setdefault("header", {})
            request.validated.setdefault("querystring", {})
            resource = Record(request, context=self)
            resource.object_id = request.matchdict["id"]
            existing = resource.get()
        except httpexceptions.HTTPNotFound:
            existing = None

        if existing:
            # Request write permission on the existing record.
            self.permission_object_id = record_uri(request)
            self.required_permission = "write"
        else:
            # Request create record permission on the parent collection.
            self.permission_object_id = collection_uri(request)
            self.required_permission = "create"
        # Set the current object in context, since it is used in the
        # authorization policy to distinguish operations on plural endpoints
        # from individual objects. See Kinto/kinto#918
        self.current_object = existing


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()


def _object_uri(request, resource_name, matchdict, prefix):
    uri = core_utils.instance_uri(request, resource_name=resource_name, **matchdict)
    if prefix:
        uri = f"/{request.registry.route_prefix}{uri}"
    return uri


def bucket_uri(request, prefix=False):
    matchdict = dict(request.matchdict)
    matchdict["id"] = matchdict["bucket_id"]
    return _object_uri(request, "bucket", matchdict, prefix)


def collection_uri(request, prefix=False):
    matchdict = dict(request.matchdict)
    matchdict["id"] = matchdict["collection_id"]
    return _object_uri(request, "collection", matchdict, prefix)


def record_uri(request, prefix=False):
    return _object_uri(request, "record", request.matchdict, prefix)


def patch_record(record, request):
    # XXX: add util clone_request()
    backup_pattern = request.matched_route.pattern
    backup_body = request.body
    backup_validated = request.validated

    # Instantiate record resource with current request.
    context = RouteFactory(request)
    context.resource_name = "record"
    context.get_permission_object_id = lambda r, i: record_uri(r)
    record_pattern = request.matched_route.pattern.replace("/attachment", "")
    request.matched_route.pattern = record_pattern

    # Simulate update of fields.
    request.validated = dict(body=record, **backup_validated)

    request.body = json.dumps(record).encode("utf-8")
    resource = Record(request, context=context)
    resource.object_id = request.matchdict["id"]
    setattr(request, "_attachment_auto_save", True)  # Flag in update listener.

    try:
        saved = resource.patch()
    except httpexceptions.HTTPNotFound:
        saved = resource.put()

    request.matched_route.pattern = backup_pattern
    request.body = backup_body
    request.validated = backup_validated
    return saved


def delete_attachment(request, link_field=None, uri=None, keep_old_files=False):
    """Delete existing file and link."""
    if link_field is None:
        link_field = "record_uri"
    if uri is None:
        uri = record_uri(request)

    storage = request.registry.storage
    filters = [Filter(link_field, uri, core_utils.COMPARISON.EQ)]

    # Remove file.
    if not keep_old_files:
        file_links = storage.list_all("", FILE_LINKS, filters=filters)
        for link in file_links:
            request.attachment.delete(link["location"])

    # Remove link.
    storage.delete_all("", FILE_LINKS, filters=filters, with_deleted=False)


def save_file(request, content, folder=None, keep_link=True, replace=False):
    randomize = setting_value(request, "randomize", default=True)

    overriden_mimetypes = {**DEFAULT_MIMETYPES}
    conf_mimetypes = setting_value(request, "mimetypes", default="")
    if conf_mimetypes:
        overriden_mimetypes.update(dict([v.split(":") for v in conf_mimetypes.split(";")]))

    # Read file to compute hash.
    if not isinstance(content, cgi.FieldStorage):
        error_msg = "Filename is required."
        raise_invalid(request, location="body", description=error_msg)

    # Posted file attributes.
    content.file.seek(0)
    filecontent = content.file.read()
    filehash = sha256(filecontent)
    size = len(filecontent)
    filename = content.filename

    _, extension = os.path.splitext(filename)
    mimetype = overriden_mimetypes.get(extension, content.type)

    save_options = {
        "folder": folder,
        "randomize": randomize,
        "replace": replace,
        "headers": {"Content-Type": mimetype},
    }

    try:
        location = request.attachment.save(content, **save_options)
    except FileNotAllowed:
        error_msg = "File extension is not allowed."
        raise_invalid(request, location="body", description=error_msg)

    # File metadata.
    fullurl = request.attachment.url(location)
    attachment = {
        "filename": filename,
        "location": fullurl,
        "hash": filehash,
        "mimetype": mimetype,
        "size": size,
    }

    if keep_link:
        # Store link between record and attachment (for later deletion).
        request.registry.storage.create(
            "",
            FILE_LINKS,
            {
                "location": location,  # store relative location.
                "bucket_uri": bucket_uri(request),
                "collection_uri": collection_uri(request),
                "record_uri": record_uri(request),
            },
        )

    return attachment


def setting_value(request, name, default):
    value = request.registry.settings.get("attachment.{}".format(name), default)
    if "bucket_id" in request.matchdict:
        uri = "/buckets/{bucket_id}".format(**request.matchdict)
        if uri in request.registry.attachment_resources:
            value = request.registry.attachment_resources[uri].get(name, value)
        if "collection_id" in request.matchdict:
            uri = "/buckets/{bucket_id}/collections/{collection_id}".format(**request.matchdict)
            if uri in request.registry.attachment_resources:
                value = request.registry.attachment_resources[uri].get(name, value)
    return value
