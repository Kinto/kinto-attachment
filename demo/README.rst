========
Run Demo
========

Run Kinto locally
-----------------

* Follow `the instructions in Kinto documentation <http://kinto.readthedocs.org>`_
to get a local instance running.

* Follow the instructions of this plugin to install and set the appropriate settings
  in ``config.ini``

Now start Kinto

::

    kinto --ini config.ini start

It should run on http://localhost:8888


Prepare demo objects
--------------------

This demo posts records in the ``fennec-ota`` bucket. The target *collection*
can be chosen in the form from ``font``, ``locale`` and ``hyphenation`` values.
The form will use ``user:pass`` as a basic authentication string.

Create those expected objects in your local *Kinto*:

::

    http PUT http://localhost:8888/v1/buckets/fennec-ota --auth="user:pass" --verbose
    http PUT http://localhost:8888/v1/buckets/fennec-ota/collections/font --auth="user:pass" --verbose
    http PUT http://localhost:8888/v1/buckets/fennec-ota/collections/locale --auth="user:pass" --verbose
    http PUT http://localhost:8888/v1/buckets/fennec-ota/collections/hyphenation --auth="user:pass" --verbose


Run the demo
------------

* Run locally:

::

    cd demo/
    python -m SimpleHTTPServer 9999

* Navigate to http://localhost:9999 and post files!
