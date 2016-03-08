import gzip
import hashlib
import os

import requests
from kinto_client import cli_utils


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()


def download_files(client, records, folder, chunk_size=1024):
    for record in records:
        if 'attachment' not in record:
            continue

        attachment = record['attachment']

        # Check if file was Gzipped during upload (see `upload.py`)
        is_gzip = 'original' in record
        if is_gzip:
            filename = record['original']['filename']
            remote_hash = record['original']['hash']
        else:
            filename = attachment['filename']
            remote_hash = attachment['hash']

        destination = os.path.join(folder, filename)

        # Compare local hash with remote and skip if equal.
        if os.path.exists(destination):
            local_hash = sha256(open(destination, 'rb').read())
            if local_hash == remote_hash:
                print('Skip "%s". Up-to-date.' % filename)
                continue

        # Download remote attachment by chunk.
        resp = requests.get(attachment['location'], stream=True)
        resp.raise_for_status()
        tmp_file = destination + '.tmp'
        with open(tmp_file, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        # Decompress the file if necessary.
        if is_gzip:
            with open(destination, 'wb') as f:
                data = open(tmp_file, 'rb').read()
                f.write(gzip.decompress(data))
        else:
            os.rename(tmp_file, destination)

        print('Downloaded "%s"' % filename)


def main():
    parser = cli_utils.add_parser_options(
        description='Download files from Kinto')
    parser.add_argument('-f', '--folder', help='Folder to download files in.',
                        type=str, default=".")
    args = parser.parse_args()

    client = cli_utils.create_client_from_args(args)

    # See if timestamp was saved from last run.
    last_sync = None
    timestamp_file = os.path.join(args.folder, '.last_sync')
    if os.path.exists(args.folder):
        if os.path.exists(timestamp_file):
            last_sync = open(timestamp_file, 'r').read()
    else:
        os.makedirs(args.folder)

    # Retrieve the collection of records.
    existing = client.get_records(_since=last_sync, _sort="-last_modified")

    if existing:
        download_files(client, existing, args.folder)

        timestamp = max([r['last_modified'] for r in existing])
        # Save the highest timestamp for next runs.
        with open(timestamp_file, 'w') as f:
            f.write("%s" % timestamp)


if __name__ == '__main__':
    main()
