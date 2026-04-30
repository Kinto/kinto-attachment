import mimetypes
import os
import urllib
from datetime import datetime

from pyramid.exceptions import ConfigurationError
from pyramid.settings import asbool
from zope.interface import implementer

from . import (
    IFileStorage,
    random_filename,
    read_settings,
    register_file_storage_impl,
    secure_filename,
)


try:
    from google.cloud.exceptions import NotFound
    from google.cloud.storage.blob import Blob
    from google.cloud.storage.client import Client
except ImportError:  # pragma: no cover
    raise RuntimeError(
        "Could not load Google Cloud Storage bindings.\n"
        "See https://github.com/GoogleCloudPlatform/gcloud-python"
    )


def includeme(config):
    impl = GoogleCloudStorage.from_settings(config.registry.settings, prefix="storage.")
    register_file_storage_impl(config, impl)


DEFAULT_BUCKET_ACL = "projectPrivate"
DEFAULT_FILE_ACL = "publicRead"


@implementer(IFileStorage)
class GoogleCloudStorage:
    @classmethod
    def from_settings(cls, settings, prefix):
        options = (
            ("gcloud.credentials", False, None),
            ("gcloud.project", False, None),
            ("gcloud.bucket_name", True, None),
            ("gcloud.acl", False, None),
            ("base_url", False, ""),
            ("gcloud.auto_create_bucket", False, False),
            ("gcloud.auto_create_acl", False, None),
            ("gcloud.cache_control", False, None),
            ("gcloud.uniform_bucket_level_access", False, False),
        )
        kwargs = read_settings(settings, options, prefix)
        kwargs = {k.replace("gcloud.", ""): v for k, v in kwargs.items()}
        return cls(**kwargs)

    def __init__(
        self,
        credentials,
        bucket_name,
        project=None,
        acl=None,
        base_url="",
        auto_create_bucket=False,
        auto_create_acl=None,
        cache_control=None,
        uniform_bucket_level_access=False,
    ):
        if (acl or auto_create_acl) and uniform_bucket_level_access:
            raise ConfigurationError(
                '"acl" and "auto_create_acl" should remain unset '
                'when "uniform_bucket_level_access" is enabled!'
            )

        self.uniform_bucket_level_access = asbool(uniform_bucket_level_access)

        if not self.uniform_bucket_level_access:
            self.acl = acl or DEFAULT_FILE_ACL
            self.auto_create_acl = auto_create_acl or DEFAULT_BUCKET_ACL
        else:
            self.acl = acl
            self.auto_create_acl = auto_create_acl

        self.credentials = credentials
        self.project = project
        self.bucket_name = bucket_name
        self.base_url = base_url
        self.auto_create_bucket = auto_create_bucket
        self.cache_control = cache_control

        self._client = None
        self._bucket = None

    def get_connection(self):
        if self._client is None:
            if self.credentials:
                self._client = Client.from_service_account_json(
                    json_credentials_path=self.credentials
                )
            elif self.project:
                self._client = Client(project=self.project)
            else:
                self._client = Client()
        return self._client

    def get_bucket(self, bucket_name=None):
        if self._bucket is None:
            self._bucket = self._get_or_create_bucket(self.bucket_name)
        if bucket_name and bucket_name != self.bucket_name:
            return self._get_or_create_bucket(bucket_name)
        return self._bucket

    def _get_or_create_bucket(self, name):
        try:
            return self.get_connection().get_bucket(name)
        except NotFound:
            if self.auto_create_bucket:
                bucket = self.get_connection().create_bucket(name)
                if not self.uniform_bucket_level_access:
                    bucket.acl.save_predefined(self.auto_create_acl)
                return bucket
            raise RuntimeError(
                "Bucket %s does not exist. Set auto_create_bucket=True to create it." % name
            )

    def url(self, filename):
        return urllib.parse.urljoin(self.base_url, filename)

    def exists(self, name, bucket_name=None):
        if not name:
            try:
                self.get_bucket(bucket_name)
                return True
            except RuntimeError:
                return False
        return bool(self.get_bucket(bucket_name).get_blob(name))

    def delete(self, filename, bucket_name=None):
        self.get_bucket(bucket_name).delete_blob(filename)

    def save(self, fs, *args, **kwargs):
        return self.save_file(fs.file, fs.filename, *args, **kwargs)

    def save_file(
        self,
        file,
        filename,
        folder=None,
        bucket_name=None,
        randomize=False,
        filename_pattern=None,
        record_id="",
        acl=None,
        replace=False,
        headers=None,
    ):
        filename = secure_filename(os.path.basename(filename))

        if randomize:
            filename = random_filename(filename)

        if filename_pattern:
            filename = filename_pattern.format(
                datetime=datetime.now().strftime("%Y%m%d%H%M%S"),
                rid=record_id,
                filename=filename,
            )

        if folder:
            filename = folder + "/" + filename

        content_type = (headers or {}).get("Content-Type")
        if content_type is None:
            content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        blob = self.get_bucket(bucket_name).get_blob(filename)

        if blob and not replace:
            return filename

        if not blob:
            blob = Blob(filename, self.get_bucket(bucket_name))

        blob.cache_control = self.cache_control
        file.seek(0)

        upload_kwargs = {"rewind": True, "content_type": content_type}
        if not self.uniform_bucket_level_access:
            upload_kwargs["predefined_acl"] = acl or self.acl

        blob.upload_from_file(file, **upload_kwargs)

        return filename
