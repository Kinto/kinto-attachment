from kinto_attachment.views import attachments_ping


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

    # # Expose capability.
    config.add_api_capability("attachments",
                              description="Add file attachments to records",
                              url="https://github.com/Kinto/kinto-attachment/")

    # Advertise public setting.
    config.registry.public_settings.add('attachment.base_url')

    # Register heartbeat to check attachments storage.
    config.registry.heartbeats['attachments'] = attachments_ping

    # Enable attachment backend.
    if 'storage.base_path' in storage_settings:
        config.include('pyramid_storage.local')
    else:
        config.include('pyramid_storage.s3')

    config.scan('kinto_attachment.views')
    config.scan('kinto_attachment.listeners')
