import json
import hashlib
import mimetypes
import os
import pprint
import uuid

from kinto_http import cli_utils
from kinto_http.exceptions import KintoException

DEFAULT_SERVER = "http://localhost:8888/v1"


def sha256(content):
    m = hashlib.sha256()
    m.update(content)
    return m.hexdigest()


def files_to_upload(records, files, force=False):
    records_by_id = {r['id']: r for r in records if 'attachment' in r}
    existing_files = {r['attachment']['filename']: r for r in records if 'attachment' in r}
    existing_original_files = {r['attachment']['original']['filename']: r
                               for r in records
                               if 'attachment' in r and 'original' in r['attachment']}
    to_upload = []
    for filepath in files:
        filename = os.path.basename(filepath)

        record = None
        if filename in existing_files.keys():
            record = existing_files[filename]
        elif filename in existing_original_files.keys():
            record = existing_original_files[filename]

        if record:
            records_by_id.pop(record['id'], None)
            local_hash = sha256(open(filepath, 'rb').read())

            # If file was uploaded gzipped, compare with hash of
            # uncompressed file.
            remote_hash = record.get('original', {}).get('hash')
            if not remote_hash:
                remote_hash = record['attachment']['hash']

            # If hash has changed, upload !
            if local_hash != remote_hash or force:
                print("File '%s' has changed." % filename)
                to_upload.append((filepath, record))
            else:
                print("File '%s' is up-to-date." % filename)
        else:
            identifier = hashlib.md5(filename.encode('utf-8')).hexdigest()
            record_id = str(uuid.UUID(identifier))
            record = {'id': record_id}
            to_upload.append((filepath, record))

    # XXX: add option to delete records when files are missing locally
    for id, record in records_by_id.items():
        print("Ignore remote file '%s'." % record['attachment']['filename'])

    return to_upload


def upload_files(client, files):
    permissions = {}  # XXX: Permissions are inherited from collection.

    for filepath, record in files:
        mimetype, _ = mimetypes.guess_type(filepath)
        filename = os.path.basename(filepath)
        filecontent = open(filepath, "rb").read()
        record_uri = client.get_endpoint('record', id=record['id'])
        attachment_uri = '%s/attachment' % record_uri
        multipart = [("attachment", (filename, filecontent, mimetype))]
        try:
            body, _ = client.session.request(method='post',
                                             endpoint=attachment_uri,
                                             permissions=json.dumps(permissions),
                                             files=multipart)
        except KintoException as e:
            print(filepath, "error during upload.", e)
        else:
            pprint.pprint(body)


def main():
    parser = cli_utils.add_parser_options(
        description='Upload files to Kinto',
        default_server=DEFAULT_SERVER)

    parser.add_argument('--force', dest='force', action='store_true',
                        help='Force upload even if the hash matches')
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
    to_upload = files_to_upload(existing, args.files, force=args.force)
    upload_files(client, to_upload)


if __name__ == '__main__':
    main()
