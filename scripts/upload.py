import argparse
import gzip
import json
import hashlib
import mimetypes
import os
import pprint
import uuid

try:
    import requests
except ImportError:
    raise RuntimeError("requests is required")


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()


def fetch_records(session, url):
    response = session.get(url)
    response.raise_for_status()
    return response.json()['data']


def files_to_upload(records, files):
    records_by_id = {r['id']: r for r in records if 'attachment' in r}
    to_upload = []
    for filepath in files:
        filename = os.path.basename(filepath)

        identifier = hashlib.md5(filename.encode('utf-8')).hexdigest()
        record_id = str(uuid.UUID(identifier))

        record = records_by_id.pop(record_id, None)
        if record:
            local_hash = sha256(open(filepath, 'rb').read())

            # If file was uploaded gzipped, compare with hash of uncompressed file.
            remote_hash = record.get('original', {}).get('hash')
            if not remote_hash:
                remote_hash = record['attachment']['hash']

            # If hash has changed, upload !
            if local_hash != remote_hash:
                print("File '%s' has changed." % filename)
                to_upload.append((filepath, record))
            else:
                print("File '%s' is up-to-date." % filename)
        else:
            record = {'id': record_id}
            to_upload.append((filepath, record))

    # XXX: add option to delete records when files are missing locally
    for id, record in records_by_id.items():
        print("Ignore remote file '%s'." % record['attachment']['filename'])

    return to_upload


def upload_files(session, url, files, compress):
    permissions = {}  # XXX not set yet

    for filepath, record in files:
        mimetype, _ = mimetypes.guess_type(filepath)
        filename = os.path.basename(filepath)
        filecontent = open(filepath, "rb").read()
        if not compress:
            attributes = {}
        else:
            attributes = {
                'original': {
                    'filename': filename,
                    'hash': sha256(filecontent),
                    'mimetype': mimetype,
                    'size': len(filecontent)
                }
            }
            filename += '.gz'
            filecontent = gzip.compress(filecontent)
            mimetype = 'application/x-gzip'

        attachment_uri = '%s/%s/attachment' % (url, record['id'])
        multipart = [("attachment", (filename, filecontent, mimetype))]
        payload = {'data': json.dumps(attributes), 'permissions': json.dumps(permissions)}
        response = session.post(attachment_uri, data=payload, files=multipart)
        response.raise_for_status()
        pprint.pprint(response.json())


def main():
    parser = argparse.ArgumentParser(description='Upload files to Kinto')
    parser.add_argument('--url', dest='url', action='store',
                        help='Collection URL', required=True)
    parser.add_argument('--auth', dest='auth', action='store',
                        help='Credentials')
    parser.add_argument('--gzip', dest='gzip', action='store_true',
                        help='Gzip files before upload')
    parser.add_argument('files', metavar='FILE', action='store',
                        nargs='+')
    args = parser.parse_args()

    session = requests.Session()
    if args.auth:
        session.auth = tuple(args.auth.split(':'))

    url = args.url
    if url.endswith('/'):
        url = url[:-1]
    if not url.endswith('records'):
        url += '/records'

    existing = fetch_records(session, url=url)
    to_upload = files_to_upload(existing, args.files)
    upload_files(session, url, to_upload, compress=args.gzip)


if __name__ == '__main__':
    main()
