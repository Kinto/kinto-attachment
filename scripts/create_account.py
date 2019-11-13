import pprint

from kinto_http import cli_utils

DEFAULT_SERVER = "http://localhost:8888/v1"


def main():
    parser = cli_utils.add_parser_options(
        description='Create account on Kinto',
        default_server=DEFAULT_SERVER)

    args = parser.parse_args()

    user, password = args.auth

    client = cli_utils.create_client_from_args(args)
    root_url = client.get_endpoint('root')
    account_url = root_url + "/accounts/" + user
    resp, _ = client.session.request(method='PUT', endpoint=account_url, payload={
        "data": {"password": password}
    })
    pprint.pprint(resp)


if __name__ == '__main__':
    main()
