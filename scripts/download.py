import argparse
import gzip
import hashlib
import os

try:
    import requests
except ImportError:
    raise RuntimeError("requests is required")


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()


def fetch_records(session, url, since=None):
    if since:
        url = url + "?_since=%s" % since
    response = session.get(url)
    response.raise_for_status()
    return response.json()['data']


def download_files(session, url, records, folder, chunk_size=1024):
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
        resp = session.get(attachment['location'], stream=True)
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
    parser = argparse.ArgumentParser(description='Download files from Kinto')
    parser.add_argument('--url', dest='url', action='store',
                        help='Collection URL', required=True)
    parser.add_argument('--auth', dest='auth', action='store',
                        help='Credentials')
    parser.add_argument('--folder', dest='folder', action='store',
                        default='.', help='Destination folder')
    args = parser.parse_args()

    session = requests.Session()
    if args.auth:
        session.auth = tuple(args.auth.split(':'))

    url = args.url
    if url.endswith('/'):
        url = url[:-1]
    if not url.endswith('records'):
        url += '/records'

    # See if timestamp was saved from last run.
    last_sync = None
    timestamp = os.path.join(args.folder, '.last_sync')
    if os.path.exists(args.folder):
        if os.path.exists(timestamp):
            last_sync = open(timestamp, 'r').read()
    else:
        os.makedirs(args.folder)

    # Retrieve the collection of records.
    existing = fetch_records(session, url=url, since=last_sync)
    if existing:
        download_files(session, url, existing, args.folder)
        # Save the highest timestamp for next runs.
        with open(timestamp, 'w') as f:
            f.write("%s" % existing[0]['last_modified'])


if __name__ == '__main__':
    main()
