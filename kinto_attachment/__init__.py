import pkg_resources
from pyramid.settings import asbool
from kinto_attachment.views import attachments_ping

#: Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version


def includeme(config):
    # Process settings to remove storage wording.
    settings = config.get_settings()

    storage_settings = {}
    for k, v in settings.items():
        if k.startswith('attachment.'):
            k = k.replace('attachment.', 'storage.')
            storage_settings[k] = v

    # Force some pyramid_storage settings.
    storage_settings['storage.name'] = 'attachment'
    storage_settings.setdefault('storage.extensions', 'any')
    config.add_settings(storage_settings)

    # It may be useful to define an additional base_url setting.
    # (see workaround about relative base_url in README)
    extra_base_url = settings.get('attachment.extra.base_url',
                                  settings.get('attachment.base_url'))
    gzipped = asbool(settings.get('attachment.gzipped', False))
    # # Expose capability.
    config.add_api_capability("attachments",
                              version=__version__,
                              description="Add file attachments to records",
                              url="https://github.com/Kinto/kinto-attachment/",
                              gzipped=gzipped,
                              base_url=extra_base_url)

    # Register heartbeat to check attachments storage.
    config.registry.heartbeats['attachments'] = attachments_ping

    # Enable attachment backend.
    if 'storage.base_path' in storage_settings:
        config.include('pyramid_storage.local')
    else:
        config.include('pyramid_storage.s3')

    config.scan('kinto_attachment.views')
    config.scan('kinto_attachment.listeners')
