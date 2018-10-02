import pkg_resources
from collections import defaultdict
from pyramid.exceptions import ConfigurationError
from pyramid.settings import asbool

#: Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version


def includeme(config):
    # Process settings to remove storage wording.
    settings = config.get_settings()

    storage_settings = {}
    config.registry.attachment_resources = defaultdict(dict)

    for setting_name, setting_value in settings.items():
        if setting_name.startswith('attachment.'):
            if setting_name.startswith('attachment.resources.'):
                # Resource specific config
                parts = setting_name.replace('attachment.resources.', '').split('.')
                # attachment.resources.{bid}.gzipped
                # attachment.resources.{bid}.{cid}.gzipped
                if len(parts) == 3:
                    bucket_id, collection_id, name = parts
                    resource_id = '/buckets/{}/collections/{}'.format(bucket_id, collection_id)
                elif len(parts) == 2:
                    bucket_id, name = parts
                    resource_id = '/buckets/{}'.format(bucket_id)
                else:
                    message = 'Configuration rule malformed: `{}`'.format(setting_name)
                    raise ConfigurationError(message)

                if name in ('gzipped', 'randomize', 'keep_old_files'):
                    config.registry.attachment_resources[resource_id][name] = asbool(setting_value)
                else:
                    message = '`{}` is not a supported setting name. Read `{}`'.format(
                        name, setting_name)
                    raise ConfigurationError(message)
            else:
                setting_name = setting_name.replace('attachment.', 'storage.')
                storage_settings[setting_name] = setting_value

    # Force some pyramid_storage settings.
    storage_settings['storage.name'] = 'attachment'
    storage_settings.setdefault('storage.extensions', 'default')
    config.add_settings(storage_settings)

    # It may be useful to define an additional base_url setting.
    # (see workaround about relative base_url in README)
    extra_base_url = settings.get('attachment.extra.base_url',
                                  settings.get('attachment.base_url'))

    # Expose capability.
    config.add_api_capability("attachments",
                              version=__version__,
                              description="Add file attachments to records",
                              url="https://github.com/Kinto/kinto-attachment/",
                              base_url=extra_base_url)

    # Register heartbeat to check attachments storage.
    from kinto_attachment.views import attachments_ping
    config.registry.heartbeats['attachments'] = attachments_ping

    # Enable attachment backend.
    if 'storage.base_path' in storage_settings:
        config.include('pyramid_storage.local')
    else:
        config.include('pyramid_storage.s3')

    config.scan('kinto_attachment.views')
    config.scan('kinto_attachment.listeners')
