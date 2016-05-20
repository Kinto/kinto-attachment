#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    readme = f.read()

with codecs.open(os.path.join(here, 'CHANGELOG.rst'), encoding='utf-8') as f:
    history = f.read()

requirements = [
    'boto',
    'kinto>=1.11.0',
    'pyramid_storage>=0.1.0',
]

test_requirements = [
    'mock',
    'unittest2',
    'webtest'
]

setup(
    name='kinto-attachment',
    version='0.6.0',
    description="Attach files to Kinto records",
    long_description=readme + '\n\n' + history,
    author="Mozilla",
    author_email='kinto@mozilla.org',
    url='https://github.com/Kinto/kinto-attachment',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    license="Apache License (2.0)",
    zip_safe=False,
    keywords='kinto',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='kinto_attachment.tests',
    tests_require=test_requirements
)
