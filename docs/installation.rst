.. highlight:: shell

Installation
============

.. _prerequisites:

Prerequisites
-------------

At least Python 3.5 and ``pip`` must be installed. As ``inxs`` is depending on a
`proposed feature`_ for ``lxml``, its binary wheels can't be used for installation and a patched version
must be built locally::

    # On Debian and derived systems like Ubuntu:
    $ sudo apt-get install build-essential libxml2-dev libxslt-dev zlib1g-dev
    # On Alpine Linux:
    $ apk add build-base libxml2-dev libxslt-dev zlib-dev

    $ pip install cython
    $ pip install https://github.com/funkyfuture/lxml/tarball/smart_xpath#egg=lxml


*Windows* users should download and extract the sources_ and follow these `build instructions`_.


.. _build instructions: http://lxml.de/build.html#static-linking-on-windows
.. _proposed feature: https://github.com/lxml/lxml/pull/236
.. _sources: https://github.com/funkyfuture/lxml/archive/smart_xpath.zip


From the cheeseshop
-------------------

To install inxs, run this command in your terminal::

    $ pip install inxs

This is the preferred method to install inxs, as it will always install the most recent stable release.

If you don't have pip_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From the sources
----------------

The sources for inxs can be downloaded from the `Github repo`_.

You can either clone the public repository::

    $ git clone git://github.com/funkyfuture/inxs

Or download the `tarball`_::

    $ curl  -OL https://github.com/funkyfuture/inxs/tarball/master

Once you have a copy of the source, you can install it with::

    $ python setup.py install

Or install an editable instance::

    $ python setup.py develop


.. _Github repo: https://github.com/funkyfuture/inxs
.. _tarball: https://github.com/funkyfuture/inxs/tarball/master
