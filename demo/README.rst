========
Run Demo
========

Online demo
-----------

The demo server at Mozilla runs with *kinto-attachment* enabled.

An hosted version of this folder is hosted on [Github pages](http://kinto.github.io/kinto-attachment)
and can be used to play with the file feature.


Run the demo locally
--------------------

* Follow `the instructions in Kinto documentation <http://kinto.readthedocs.io>`_
to get a local instance running.

* Follow the instructions of this plugin to install and set the appropriate settings
  in ``config.ini``

We will serve the files locally, using these settings in config:

::

    kinto.attachment.base_path = /tmp
    kinto.attachment.base_url = http://localhost:7777

In a separate terminal, run a simple server to serve the uploaded files:

::

    cd /tmp/
    python -m SimpleHTTPServer 7777

Now start Kinto

::

    kinto --ini config.ini start

It should run on http://localhost:8888

Edit `demo/index.js` to set the `server` variable to `http://localhost:8888/v1`.

In a separate terminal, run a simple server to server the JavaScript demo app:

::

    cd demo/
    python -m SimpleHTTPServer 9999

* Navigate to http://localhost:9999 and post files!
* The links on uploaded files are served on http://localhost:7777
