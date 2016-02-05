#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.rst') as history_file:
    history = history_file.read()

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
    version='0.3.0.dev0',
    description="Attach files to Kinto records",
    long_description=readme + '\n\n' + history,
    author="Mozilla",
    author_email='kinto@mozilla.org',
    url='https://github.com/Kinto/kinto-attachment',
    packages=[
        'kinto_attachment',
    ],
    package_dir={'kinto_attachment':
                 'kinto_attachment'},
    include_package_data=True,
    install_requires=requirements,
    license="Apache License (2.0)",
    zip_safe=False,
    keywords='kinto',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
