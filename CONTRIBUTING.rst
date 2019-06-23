.. highlight:: shell

Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/funkyfuture/inxs/issues.

If you are reporting a bug, please include:

* Your Python interpreter and `inxs`' version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to fix it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

`inxs` could always use more documentation, whether as part of the
official `inxs` docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/funkyfuture/inxs/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `inxs` for local development.

1. Install the needed :ref:`prerequisites`
2. `Fork`_ the `inxs` repo on GitHub.
3. Clone your fork locally::

    $ git clone git@github.com:your_name_here/inxs.git

4. Install your local copy into a virtualenv. Assuming you have `pew`_ installed, this is how you set up your fork for local development::

    $ cd inxs/
    $ pew new -a $(pwd) inxs
    $ pip install -r requirements-dev.txt
    $ python setup.py develop

5. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

6. When you're done making changes, format the code with black_ and check that your
   changes pass all QA tests::

    $ make black
    $ tox

7. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

8. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated.
3. The pull request should work for Python 3.6. Check
   https://travis-ci.org/funkyfuture/inxs/pull_requests
   and make sure that the tests pass for all supported Python versions.


.. _black: https://pypi.org/project/black/
.. _fork: https://github.com/funkyfuture/inxs#fork-destination-box
.. _pew: https://pypi.org/project/pew/
