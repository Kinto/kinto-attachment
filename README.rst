================
Kinto Attachment
================

.. image:: https://img.shields.io/travis/Kinto/kinto-attachment/master.svg
        :target: https://travis-ci.org/Kinto/kinto-attachment

.. image:: https://img.shields.io/pypi/v/kinto-attachment.svg
        :target: https://pypi.python.org/pypi/kinto-attachment

.. image:: https://coveralls.io/repos/Kinto/kinto-attachment/badge.svg?branch=master
        :target: https://coveralls.io/r/Kinto/kinto-attachment

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
    kinto.attachment.folder = {bucket_id}/{collection_id}
    kinto.attachment.keep_old_files = true

Store files locally:

.. code-block:: ini

    kinto.attachment.base_path = /tmp

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

QueryString options
-------------------

By default, the server will randomize the name of the attached files. If you
don't want this behavior and prefer to keep the original file name, you can
pass ``?randomize=false`` in the QueryString.

Attributes
----------

When a file is attached, the related record is given an ``attachment`` attribute
with the following fields:

- ``filename``: the original filename
- ``hash``: a SHA-256 digest
- ``location``: the URL of the attachment
- ``mimetype``: the `media type <https://en.wikipedia.org/wiki/Media_type>`_ of
  the file
- ``size``: size in bytes

.. code-block:: json

    {
        "data": {
            "attachment": {
                "filename": "IMG_20150219_174559.jpg",
                "hash": "hPME6i9avCf/LFaznYr+sHtwQEX7mXYHSu+vgtygpM8=",
                "location": "http://cdn.service.org/files/ffa9c7b9-7561-406b-b7f9-e00ac94644ff.jpg",
                "mimetype": "text/plain",
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

    http --auth alice:passwd --form POST http://localhost:8888/v1/buckets/website/collections/assets/records/c2ce1975-0e52-4b2f-a5db-80166aeca689/attachment data='{"type": "wallpaper", "theme": "orange"}' "attachment@~/Pictures/background.jpg"

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
        "hash": "hPME6i9avCf/LFaznYr+sHtwQEX7mXYHSu+vgtygpM8=",
        "location": "http://cdn.service.org/files/ffa9c7b9-7561-406b-b7f9-e00ac94644ff.jpg",
        "mimetype": "text/plain",
        "size": 1481798
    }


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
    var file = form.elements.attachment.files[0];

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

If the ``--gzip`` option is passed, the files are gzipped before upload.
Since the ``attachment`` attribute contains metadata of the compressed file
the original file metadata are stored in a ``original`` attribute.

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
* Absolute URL is stored in record metadata (#24)

Run tests
=========

Run a fake Amazon S3 server in a separate terminal::

    make moto

Run the tests suite::

    make tests


Notes
=====

* `API design discussion <https://github.com/Kinto/kinto/issues/256>`_ about mixing up ``attachment`` and record fields.
