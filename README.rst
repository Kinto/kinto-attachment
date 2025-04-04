================
Kinto Attachment
================

.. image:: https://github.com/Kinto/kinto-attachment/actions/workflows/test.yml/badge.svg
        :target: https://github.com/Kinto/kinto-attachment/actions

.. image:: https://img.shields.io/pypi/v/kinto-attachment.svg
        :target: https://pypi.python.org/pypi/kinto-attachment

Attach files to `Kinto records <http://kinto.readthedocs.io>`_.


Install
=======

::

    pip install kinto-attachment


Setup
=====

In the Kinto project settings

.. code-block:: ini

    kinto.includes = kinto_attachment
    kinto.attachment.base_url = http://cdn.service.org/files/


Local File storage
------------------

Store files locally:

.. code-block:: ini

    kinto.attachment.base_path = /tmp


S3 File Storage
---------------

Store on Amazon S3:

.. code-block:: ini

    kinto.attachment.aws.access_key = <AWS access key>
    kinto.attachment.aws.secret_key = <AWS secret key>
    kinto.attachment.aws.bucket_name = <bucket name>
    kinto.attachment.aws.acl = <AWS ACL permissions|public-read>


.. note::

    ``access_key`` and ``secret_key`` may be omitted when using AWS Identity
    and Access Management (IAM).

See `Pyramid Storage <https://pythonhosted.org/pyramid_storage/>`_.


Google Cloud Storage
--------------------

.. code-block:: ini

    kinto.attachment.gcloud.credentials = <Path to the Service Accounts credentials JSON file>
    kinto.attachment.gcloud.bucket_name = <bucket name>
    kinto.attachment.gcloud.acl = publicRead

See `Google Cloud ACL permissions <https://cloud.google.com/storage/docs/access-control/making-data-public>`_


The ``folder`` option
---------------------

With this option, the files will be stored in sub-folders.

Use the ``{bucket_id}`` and ``{collection_id}`` placeholders to organize the files
by bucket or collection.

.. code-block:: ini

    kinto.attachment.folder = {bucket_id}/{collection_id}

Or only for a particular bucket:

.. code-block:: ini

    kinto.attachment.resources.blog.folder = blog-assets

Or a specific collection:

.. code-block:: ini

    kinto.attachment.resources.blog.articles.folder = articles-images


The ``keep_old_files`` option
-----------------------------

When set to ``true``, the files won't be deleted from disk/S3 when the associated record
is deleted or when the attachment replaced.

.. code-block:: ini

    kinto.attachment.keep_old_files = true

Or only for a particular bucket:

.. code-block:: ini

    kinto.attachment.resources.blog.keep_old_files = false

Or a specific collection:

.. code-block:: ini

    kinto.attachment.resources.blog.articles.keep_old_files = true

The ``randomize`` option
------------------------

If you want uploaded files to be stored with a random name (default: True):

.. code-block:: ini

    kinto.attachment.randomize = true

Or only for a particular bucket:

.. code-block:: ini

    kinto.attachment.resources.blog.randomize = true

Or a specific collection:

.. code-block:: ini

    kinto.attachment.resources.blog.articles.randomize = true

The ``extensions`` option
-------------------------

If you want to upload files which are not in the default allowed extensions (see `Pyramid extensions groups <https://pythonhosted.org/pyramid_storage/#configuration>`_ (default: ``default``):

.. code-block:: ini

    kinto.attachment.extensions = default+video


The ``mimetypes`` option
------------------------

By default, the mimetype is guessed from the filename using Python standard mimetypes module.

If you want to add or override mimetypes, use the following setting and the associated syntax:

.. code-block:: ini

    kinto.attachment.mimetypes = .ftl:application/vnd.fluent;.db:application/vnd.sqlite3


Default bucket
--------------

In order to upload files on the ``default`` bucket, the built-in default bucket
plugin should be enabled before the ``kinto_attachment`` plugin.

In the configuration, this means adding it explicitly to includes:

.. code-block:: ini

    kinto.includes = kinto.plugins.default_bucket
                     kinto_attachment

Production
----------

* Make sure the ``base_url`` can be reached (and points to ``base_path`` if
  files are stored locally)
* Adjust the max size for uploaded files (e.g. ``client_max_body_size 10m;`` for NGinx)

For example, with NGinx

::

    server {
        listen 80;

        location /v1 {
            ...
        }

        location /files {
            root /var/www/kinto;
        }
    }


API
===

**POST /{record-url}/attachment**

It will create the underlying record if it does not exist.

Required

- ``attachment``: a single multipart-encoded file

Optional

- ``data``: attributes to set on record (serialized JSON)
- ``permissions``: permissions to set on record (serialized JSON)


**DELETE /{record-url}/attachment**

Deletes the attachement from the record.


Attributes
----------

When a file is attached, the related record is given an ``attachment`` attribute
with the following fields:

- ``filename``: the original filename
- ``hash``: a SHA-256 hex digest
- ``location``: the URL of the attachment
- ``mimetype``: the `media type <https://en.wikipedia.org/wiki/Media_type>`_ of
  the file
- ``size``: size in bytes

.. code-block:: json

    {
        "data": {
            "attachment": {
                "filename": "IMG_20150219_174559.jpg",
                "hash": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                "location": "http://cdn.service.org/files/ffa9c7b9-7561-406b-b7f9-e00ac94644ff.jpg",
                "mimetype": "image/jpeg",
                "size": 1481798
            },
            "id": "c2ce1975-0e52-4b2f-a5db-80166aeca688",
            "last_modified": 1447834938251,
            "theme": "orange",
            "type": "wallpaper"
        },
        "permissions": {
            "write": ["basicauth:6de355038fd943a2dc91405063b91018bb5dd97a08d1beb95713d23c2909748f"]
        }
    }


Usage
=====

Using HTTPie
------------

.. code-block:: bash

    http --form POST http://localhost:8888/v1/buckets/website/collections/assets/records/c2ce1975-0e52-4b2f-a5db-80166aeca689/attachment \
        data='{"type": "wallpaper", "theme": "orange"}' \
        attachment"@~/Pictures/background.jpg" \
        --auth alice:passwd

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Content-Length: 209
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 18 Nov 2015 08:22:18 GMT
    Etag: "1447834938251"
    Last-Modified: Wed, 18 Nov 2015 08:22:18 GMT
    Location: http://localhost:8888/v1/buckets/website/collections/font/assets/c2ce1975-0e52-4b2f-a5db-80166aeca689
    Server: waitress

    {
        "filename": "IMG_20150219_174559.jpg",
        "hash": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        "location": "http://cdn.service.org/files/ffa9c7b9-7561-406b-b7f9-e00ac94644ff.jpg",
        "mimetype": "image/jpeg",
        "size": 1481798
    }

In order to force a specific file attachment mimetype:

.. code-block:: bash

    http -f POST $URL attachment"~/files/data.bin;type=application/pdf"


Using cURL
----------

.. code-block:: bash

    curl -X POST ${SERVER}/buckets/${BUCKET}/collections/${COLLECTION}/records/${RECORD_ID}/attachment \
         -H 'Content-Type:multipart/form-data' \
         -F attachment="@$FILEPATH;type=application/x-protobuf" \
         -F 'data={"name": "Mac Fly", "age": 42}' \
         -H "Authorization: $STAGE_AUTH"


Using Python requests
---------------------

.. code-block:: python

    auth = ("alice", "passwd")
    attributes = {"type": "wallpaper", "theme": "orange"}
    perms = {"read": ["system.Everyone"]}

    files = [("attachment", ("background.jpg", open("Pictures/background.jpg", "rb"), "image/jpeg"))]

    payload = {"data": json.dumps(attributes), "permissions": json.dumps(perms)}
    response = requests.post(SERVER_URL + endpoint, data=payload, files=files, auth=auth)

    response.raise_for_status()


Using JavaScript
----------------

.. code-block:: javascript

    var headers = {Authorization: "Basic " + btoa("alice:passwd")};
    var attributes = {"type": "wallpaper", "theme": "orange"};
    var perms = {"read": ["system.Everyone"]};

    // File object from input field
    var filefield = form.elements.attachment.files[0];
    // If necessary, force the file content-type:
    var file = new Blob([filefield], { type: "application/pdf" });

    // Build form data
    var payload = new FormData();
    // Multipart attachment
    payload.append('attachment', file, "background.jpg");
    // Record attributes and permissions JSON encoded
    payload.append('data', JSON.stringify(attributes));
    payload.append('permissions', JSON.stringify(perms));

    // Post form using GlobalFetch API
    var url = `${server}/buckets/${bucket}/collections/${collection}/records/${record}/attachment`;
    fetch(url, {method: "POST", body: payload, headers: headers})
      .then(function (result) {
        console.log(result);
      });


Scripts
=======

Two scripts are provided in this repository.

They rely on the ``kinto-client`` Python package, which can be installed in a
virtualenv:

::

    $ virtualenv env --python=python3
    $ source env/bin/activate
    $ pip install kinto-client

Or globally on your system (**not recommended**):

::

    $ sudo pip install kinto-client


Upload files
------------

``upload.py`` takes a list of files and posts them on the specified server,
bucket and collection::

    $ python3 scripts/upload.py --server=$SERVER --bucket=$BUCKET --collection=$COLLECTION --auth "token:mysecret" README.rst pictures/*

See ``python3 scripts/upload.py --help`` for more details about options.


Download files
--------------

``download.py`` downloads the attachments from the specified server, bucket and
collection and store them on disk::

    $ python3 scripts/download.py --server=$SERVER --bucket=$BUCKET --collection=$COLLECTION --auth "token:mysecret"

If the record has an ``original`` attribute, the script decompresses the attachment
after downloading it.

Files are stored in the current folder by default.
See ``python3 scripts/download.py --help`` for more details about options.


Known limitations
=================

* No support for chunk upload (#10)
* Files are not removed when server is purged with ``POST /v1/__flush__``

Relative URL in records (workaround)
------------------------------------

Currently the full URL is returned in records. This is very convenient for API consumers
which can access the attached file just using the value in the ``location`` attribute.

However, the way it is implemented has a limitation: the full URL is stored in each record
directly. This is annoying because changing the ``base_url`` setting
won't actually change the ``location`` attributes on existing records.

As workaround, it is possible to set the ``kinto.attachment.base_url`` to an empty
value. The ``location`` attribute in records will now contain a *relative* URL.

Using another setting ``kinto.attachment.extra.base_url``, it is possible to advertise
the base URL that can be preprended by clients to obtain the full attachment URL.
If specified, it is going to be exposed in the capabilities of the root URL endpoint.


Run tests
=========

Run a fake Amazon S3 server in a separate terminal::

    make run-moto

Run the tests suite::

    make tests


Releasing
=========

1. Create a release on Github on https://github.com/Kinto/kinto-attachment/releases/new
2. Create a new tag `X.Y.Z` (*This tag will be created from the target when you publish this release.*)
3. Generate release notes
4. Publish release


Notes
=====

* `API design discussion <https://github.com/Kinto/kinto/issues/256>`_ about mixing up ``attachment`` and record fields.
