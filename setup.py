#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from subprocess import check_call
from sys import stderr, stdout, version_info


if version_info < (3, 5):
    raise RuntimeError("Requires Python 3.5 or later.")


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()


try:
    import cython  # noqa: F401
except ImportError:
    check_call(['pip', 'install', 'cython'], stdout=stdout, stderr=stderr)


setup(
    name='inxs',
    version='0.1b0',
    description="A framework for XML transformations without boilerplate.",
    long_description=readme + '\n\n' + history,
    author="Frank Sachsenheim",
    author_email='funkyfuture@riseup.net',
    url='https://github.com/funkyfuture/inxs',
    packages=['inxs'],
    package_dir={'inxs': 'inxs'},
    include_package_data=True,
    install_requires=['dependency_injection', 'lxml'],
    dependency_links=['https://github.com/funkyfuture/lxml/tarball/smart_xpath#egg=lxml'],
    license="ISC license",
    zip_safe=False,
    keywords='inxs xml processing transformation framework xslt not-xslt',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Text Processing :: Markup :: XML'
    ],
    test_suite='tests',
    tests_require=['pytest']
)
