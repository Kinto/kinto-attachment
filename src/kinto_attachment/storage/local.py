import os
import shutil

from zope.interface import implementer

from . import (
    FileStorage,
    IFileStorage,
    read_settings,
    register_file_storage_impl,
)


def includeme(config):
    impl = LocalFileStorage.from_settings(config.registry.settings, prefix="storage.")
    register_file_storage_impl(config, impl)


@implementer(IFileStorage)
class LocalFileStorage(FileStorage):
    @classmethod
    def from_settings(cls, settings, prefix):
        options = (
            ("base_path", True, None),
            ("base_url", False, ""),
        )
        kwargs = read_settings(settings, options, prefix)
        return cls(**kwargs)

    def __init__(self, base_path, base_url=""):
        self.base_path = base_path
        self.base_url = base_url

    def path(self, filename):
        return os.path.join(self.base_path, filename)

    def exists(self, filename):
        return os.path.exists(self.path(filename))

    def delete(self, filename):
        if self.exists(filename):
            os.remove(self.path(filename))
            return True
        return False

    def save_file(
        self,
        file,
        filename,
        folder=None,
        randomize=False,
        filename_pattern=None,
        record_id="",
        **kwargs,
    ):
        filename = self._prepare_filename(filename, randomize, filename_pattern, record_id)

        dest_folder = os.path.join(self.base_path, folder) if folder else self.base_path
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        filename, path = self._resolve_name(filename, dest_folder)

        file.seek(0)
        with open(path, "wb") as dest:
            shutil.copyfileobj(file, dest)

        if folder:
            filename = os.path.join(folder, filename)

        return filename

    def _resolve_name(self, name, folder):
        basename, ext = os.path.splitext(name)
        counter = 0
        while True:
            path = os.path.join(folder, name)
            if not os.path.exists(path):
                return name, path
            counter += 1
            name = "%s-%d%s" % (basename, counter, ext)
