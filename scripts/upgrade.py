import sys
from kinto_client import cli_utils


DEFAULT_SERVER = "https://kinto-ota.dev.mozaws.net/v1/"


def _print(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()


def upgrade(client):
    _print('Scanning collection...\n')
    count = 0

    for record in client.get_records():
        _print('.')

        attachment = record.get('attachment')
        if attachment is None:
            continue

        original = attachment.get('original')
        old_original = record.get('original')

        if original is None and old_original is not None:
            record['attachment']['original'] = old_original
            del record['original']
            client.update_record(record)
            count += 1

    _print('\nChanged %d records\n' % count)


def main():
    parser = cli_utils.add_parser_options(
        description='Upgrade the attachment structure',
        default_server=DEFAULT_SERVER)
    args = parser.parse_args()
    client = cli_utils.create_client_from_args(args)
    upgrade(client)


if __name__ == '__main__':
    main()
