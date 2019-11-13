from kinto_http import cli_utils

DEFAULT_SERVER = "http://localhost:8888/v1"


def delete_attachments(client, records):
    for record in records:
        record_uri = client.get_endpoint('record', id=record['id'])
        client.session.request(method='delete',
                               endpoint=record_uri + '/attachment')

        record = client.get_record(id=record['id'])["data"]
        assert record["attachment"] is None


def main():
    parser = cli_utils.add_parser_options(
        description='Delete files from Kinto',
        default_server=DEFAULT_SERVER)

    args = parser.parse_args()

    client = cli_utils.create_client_from_args(args)
    existing = client.get_records()
    delete_attachments(client, existing)


if __name__ == '__main__':
    main()
