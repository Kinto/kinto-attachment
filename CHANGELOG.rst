Changelog
=========

0.6.0 (2016-05-19)
------------------

- Update to ``kinto.core`` for compatibility with Kinto 3.0. This
  release is no longer compatible with Kinto < 3.0, please upgrade!


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
