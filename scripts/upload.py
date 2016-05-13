import gzip
import json
import hashlib
import mimetypes
import os
import pprint
import uuid

from kinto_client import cli_utils
from kinto_client.exceptions import KintoException

DEFAULT_SERVER = "http://localhost:8888/v1"


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()


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

            # If file was uploaded gzipped, compare with hash of
            # uncompressed file.
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


def upload_files(client, files, compress, randomize):
    permissions = {}  # XXX: Permissions are inherited from collection.

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

        record_uri = client.get_endpoint('record', id=record['id'])
        attachment_uri = '%s/attachment' % record_uri
        multipart = [("attachment", (filename, filecontent, mimetype))]
        params = {'randomize': randomize}
        body, _ = client.session.request(method='post',
                                         params=params,
                                         endpoint=attachment_uri,
                                         data=json.dumps(attributes),
                                         permissions=json.dumps(permissions),
                                         files=multipart)
        pprint.pprint(body)


def main():
    parser = cli_utils.add_parser_options(
        description='Upload files to Kinto',
        default_server=DEFAULT_SERVER)

    parser.add_argument('--gzip', dest='gzip', action='store_true',
                        help='Gzip files before upload')
    parser.add_argument('--keep-filenames', dest='randomize', action='store_false',
                        help='Do not randomize file IDs on the server')
    parser.add_argument('files', metavar='FILE', action='store',
                        nargs='+')
    args = parser.parse_args()

    client = cli_utils.create_client_from_args(args)

    try:
        client.create_bucket(if_not_exists=True)
        client.create_collection(if_not_exists=True)
    except KintoException:
        # Fail silently in case of 403
        pass

    existing = client.get_records()
    to_upload = files_to_upload(existing, args.files)
    upload_files(client, to_upload, compress=args.gzip,
                 randomize=args.randomize)


if __name__ == '__main__':
    main()
