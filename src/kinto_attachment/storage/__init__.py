import os
import re
import unicodedata
import uuid

from pyramid import exceptions as pyramid_exceptions
from zope.interface import Attribute, Interface


_FILENAME_ASCII_STRIP_RE = re.compile(r"[^A-Za-z0-9_.-]")


class IFileStorage(Interface):
    base_url = Attribute("Base URL prepended to filenames to form public URLs.")

    def url(filename):
        """Return the full public URL for *filename*."""

    def exists(filename):
        """Return ``True`` if *filename* exists in the store."""

    def save(fs, folder=None, randomize=False, replace=False, headers=None):
        """Persist *fs* (a ``cgi.FieldStorage``-like object) and return the
        stored relative filename.

        :param folder: optional sub-path prepended to the filename.
        :param randomize: replace the original name with a UUID.
        :param replace: overwrite if a file with that name already exists.
        :param headers: dict of HTTP headers (used for ``Content-Type``).
        """

    def delete(filename):
        """Remove *filename* from the store."""


def register_file_storage_impl(config, impl):
    config.registry.registerUtility(impl, IFileStorage)
    config.add_request_method(_get_file_storage_impl, "attachment", True)


def _get_file_storage_impl(request):
    return request.registry.getUtility(IFileStorage)


def secure_filename(filename):
    if isinstance(filename, str):
        filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore")
        filename = filename.decode("ascii")
    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")
    filename = str(_FILENAME_ASCII_STRIP_RE.sub("", "_".join(filename.split()))).strip("._")
    return filename


def random_filename(filename):
    _, ext = os.path.splitext(filename)
    return str(uuid.uuid4()) + ext.lower()


def read_settings(settings, options, prefix=""):
    result = {}
    for name, required, default in options:
        setting = prefix + name
        try:
            result[name] = settings[setting]
        except KeyError:
            if required:
                raise pyramid_exceptions.ConfigurationError("%s is required" % setting)
            result[name] = default
    return result
