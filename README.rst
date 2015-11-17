================
Kinto Attachment
================

.. image:: https://img.shields.io/travis/Kinto/kinto-attachment.svg
        :target: https://travis-ci.org/Kinto/kinto-attachment

.. image:: https://img.shields.io/pypi/v/kinto-attachment.svg
        :target: https://pypi.python.org/pypi/kinto-attachment

.. image:: https://coveralls.io/repos/Kinto/kinto-attachment/badge.svg?branch=master
        :target: https://coveralls.io/r/Kinto/kinto-attachment

**proof-of-concept**: Attach files to `Kinto records <http://kinto.readthedocs.org>`_.


Install
-------

::

    pip install kinto-attachment


Setup
-----

In the Kinto project settings

::

    kinto.includes = kinto_attachment
    kinto.attachment.base_url = http://cdn.service.org/files/

Store files locally:

::

    kinto.attachment.base_path = /tmp

Store on Amazon S3:

::

    kinto.attachment.aws.access_key = <AWS access key>
    kinto.attachment.aws.secret_key = <AWS secret key>
    kinto.attachment.aws.bucket = <bucket name>
    kinto.attachment.aws.acl = <AWS ACL permissions|public-read>


See `Pyramid Storage <https://pythonhosted.org/pyramid_storage/>`_.


Usage
-----

Using HTTPie:

::

    http --auth alice: --form POST http://localhost:8888/v1/buckets/website/collections/assets/records/c2ce1975-0e52-4b2f-a5db-80166aeca689/attachment data='{"type": "wallpaper", "theme": "orange"}' "attachment@~/Pictures/background.jpg"

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
        "filename": "IMG_20150219_174559-17.jpg",
        "hash": "hPME6i9avCf/LFaznYr+sHtwQEX7mXYHSu+vgtygpM8=",
        "location": "http://cdn.service.org/files/background.jpg",
        "mimetype": "text/plain",
        "size": 1481798
    }


The related record was given an `attachment` field:

::

    http --auth alice: GET http://localhost:8888/v1/buckets/website/collections/font/records/c2ce1975-0e52-4b2f-a5db-80166aeca689

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Content-Length, Expires, Alert, Retry-After, Last-Modified, ETag, Pragma, Cache-Control, Backoff
    Cache-Control: no-cache
    Content-Length: 360
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 18 Nov 2015 08:24:15 GMT
    Etag: "1447834938251"
    Last-Modified: Wed, 18 Nov 2015 08:22:18 GMT
    Server: waitress

    {
        "data": {
            "attachment": {
                "filename": "IMG_20150219_174559-17.jpg",
                "hash": "hPME6i9avCf/LFaznYr+sHtwQEX7mXYHSu+vgtygpM8=",
                "location": "http://cdn.service.org/files/IMG_20150219_174559-17.jpg",
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



TODO
----

* Support chunk upload
* Use ``moto_server`` instead of mocking
* Simple fonctionnal test with real Kinto on TravisCI
* Handle default bucket
* Validate API
* Check record permissions


Notes
-----

* `API design discussion <https://github.com/Kinto/kinto/issues/256>`_ about mixing up ``attachment`` and record fields.