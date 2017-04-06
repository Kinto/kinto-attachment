Changelog
=========

2.0.1 (2017-04-06)
------------------

**Bug fixes**

- Set request parameters before instantiating a record resource. (#127)


2.0.0 (2017-03-03)
------------------

**Breaking changes**

- Remove Python 2.7 support and upgrade to Python 3.5. (#125)


1.1.2 (2017-02-01)
------------------

**Bug fixes**

- Fix invalid request when attaching a file on non UUID record id (fixes #122)


1.1.1 (2017-02-01)
------------------

**Bug fixes**

- Fixes compatibility with Kinto 5.3 (fixes #120)


1.1.0 (2016-12-16)
------------------

- Expose the gzipped settings value in the capability (#117)


1.0.1 (2016-11-04)
------------------

**Bug fixes**

- Make kinto-attachment compatible with both cornice 1.x and 2.x (#115)


1.0.0 (2016-09-07)
------------------

**Breaking change**

- Remove the ``base_url`` from the public settings because the
  accurate value is in the capability.

**Protocol**

- Add the plugin version in the capability.


0.8.0 (2016-07-18)
------------------

**New features**

- Prevent ``attachment`` attributes to be modified manually (fixes #83)

**Bug fixes**

- Fix crash when the file is not uploaded using ``attachment`` field name (fixes #57)
- Fix crash when the multipart content-type is invalid.
- Prevent crash when filename is not provided (fixes #81)
- Update the call to the Record resource to use named attributes. (#97)
- Show detailed error when data is not posted with multipart content-type.
- Fix crash when submitted data is not valid JSON (fixes #104)

**Internal changes**

- Remove hard-coded CORS setup (fixes #59)


0.7.0 (2016-06-10)
------------------

- Add the gzip option to automatically gzip files on upload (#85)
- Run functional test on latest kinto release as well as kinto master (#86)


0.6.0 (2016-05-19)
------------------

**Breaking changes**

- Update to ``kinto.core`` for compatibility with Kinto 3.0. This
  release is no longer compatible with Kinto < 3.0, please upgrade!

**New features**

- Add a ``kinto.attachment.extra.base_url`` settings to be exposed publicly. (#73)


0.5.1 (2016-04-14)
------------------

**Bug fixes**

- Fix MANIFEST.in rules


0.5.0 (2016-04-14)
------------------

**New features**

- Add ability to disable filename randomization using a ``?randomize=false`` querystring (#62)
- Add a ``--keep-filenames`` option in ``upload.py`` script to disable randomization (#63)

**Bug fixes**

- Fix a setting name for S3 bucket in README (#68)
- Do nothing in heartbeat if server is readonly (fixes #69)

**Internal changes**

- Big refactor of views (#61)


0.4.0 (2016-03-09)
------------------

**New features**

- Previous files can be kept if the setting ``kinto.keep_old_files`` is set
  to ``true``. This can be useful when clients try to download files from a
  collection of records that is not up-to-date.
- Add heartbeat entry for attachments backend (#41)

**Bug fixes**

- Now compatible with the default bucket (#42)
- Now compatible with Python 3 (#44)

**Internal changes**

- Upload/Download scripts now use ``kinto.py`` (#38)


0.3.0 (2016-02-05)
------------------

**New feature**

- Expose the API capability ``attachments`` in the root URL (#35)

**Internal changes**

- Upgrade tests for Kinto 1.11.0 (#36)


0.2.0 (2015-12-21)
------------------

**New feature**

- Setting to store files into folders by bucket or collection (fixes #22)

**Bug fixes**

- Remove existing file when attachment is replaced (fixes #28)

**Documentation**

- The demo is now fully online, since the Mozilla demo server has this plugin
  installed.
- Add some minimal information for production


0.1.0 (2015-12-02)
------------------

* Initial working proof-of-concept.
