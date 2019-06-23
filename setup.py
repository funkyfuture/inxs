#!/usr/bin/env python

from setuptools import setup
from sys import version_info


if version_info < (3, 6):
    raise RuntimeError("Requires Python 3.6 or later.")

VERSION = '0.2b1'

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()


setup(
    name='inxs',
    version=VERSION,
    description="A framework for XML transformations without boilerplate.",
    long_description=readme + '\n\n' + history,
    author="Frank Sachsenheim",
    author_email='funkyfuture@riseup.net',
    url='https://github.com/funkyfuture/inxs',
    packages=['inxs'],
    package_dir={'inxs': 'inxs'},
    include_package_data=True,
    install_requires=('delb', 'dependency_injection'),
    license="AGPLv3+",
    zip_safe=False,
    entry_points={'console_scripts': ['inxs = inxs.cli:main']},
    keywords='inxs xml processing transformation framework xslt not-xslt',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3 '
        'or later (AGPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Text Processing :: Markup :: XML'
    ],
    test_suite='tests',
    tests_require=['pytest', 'pytest-runner']  # TODO full test cmd config
)
