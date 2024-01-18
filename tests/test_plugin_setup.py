import pytest
import unittest

from pyramid import testing
from pyramid.exceptions import ConfigurationError
from pyramid_storage.interfaces import IFileStorage
from pyramid_storage.s3 import S3FileStorage
from pyramid_storage.gcloud import GoogleCloudStorage
from kinto import main as kinto_main
from kinto_attachment import __version__, includeme

from . import BaseWebTestLocal


class HelloViewTest(BaseWebTestLocal, unittest.TestCase):
    def test_capability_is_exposed(self):
        resp = self.app.get("/")
        capabilities = resp.json["capabilities"]
        self.assertIn("attachments", capabilities)
        expected = {
            "version": __version__,
            "description": "Add file attachments to records",
            "url": "https://github.com/Kinto/kinto-attachment/",
            "base_url": "https://files.server.com/root/",
        }
        self.assertEqual(expected, capabilities["attachments"])


class IncludeMeTest(unittest.TestCase):
    def includeme(self, settings):
        config = testing.setUp(settings=settings)
        kinto_main(None, config=config)
        includeme(config)
        return config

    def test_includeme_understand_authorized_resources_settings(self):
        config = self.includeme(settings={
            "attachment.base_path": "/tmp",
            "attachment.resources.fennec.gzipped": "true",
            "attachment.resources.fingerprinting.fonts.randomize": "true",
        })
        assert isinstance(config.registry.attachment_resources, dict)
        assert '/buckets/fennec' in config.registry.attachment_resources
        assert '/buckets/fingerprinting/collections/fonts' in config.registry.attachment_resources

    def test_includeme_raises_error_for_malformed_resource_settings(self):
        with pytest.raises(ConfigurationError) as excinfo:
            self.includeme(settings={"attachment.resources.fen.nec.fonts.gzipped": "true"})
        assert str(excinfo.value) == (
            'Configuration rule malformed: `attachment.resources.fen.nec.fonts.gzipped`')

    def test_includeme_raises_error_if_wrong_resource_settings_is_defined(self):
        with pytest.raises(ConfigurationError) as excinfo:
            self.includeme(settings={"attachment.resources.fennec.base_path": "foobar"})
        assert str(excinfo.value) == ('`base_path` is not a supported setting name. '
                                      'Read `attachment.resources.fennec.base_path`')

    def test_base_url_is_added_a_trailing_slash(self):
        config = self.includeme(settings={
            "attachment.base_path": "/tmp",
            "attachment.base_url": "http://cdn.com",
        })
        assert config.registry.api_capabilities["attachments"]["base_url"] == "http://cdn.com/"

    def test_gcloud_is_used_if_credentials_setting_is_used(self):
        config = self.includeme(settings={
            "attachment.gcloud.credentials": "/path/to/credentials.json",
            "attachment.gcloud.bucket_name": "foo",
        })
        assert isinstance(config.registry.queryUtility(IFileStorage), GoogleCloudStorage)

    def test_s3_is_used_if_base_path_setting_is_not_used(self):
        config = self.includeme(settings={
            "attachment.aws.access_key": "abc",
            "attachment.aws.bucket_name": "foo",
        })
        assert isinstance(config.registry.queryUtility(IFileStorage), S3FileStorage)
