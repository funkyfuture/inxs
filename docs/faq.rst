Frequently Asked Questions
==========================

Why, oh, why?
-------------

TODO


Am I cognitively fit to use ``inxs``?
-------------------------------------

If you're comfortable with Python and delb_, you propably are. Just give it a try to solve a
smaller problem. If you don't get a grip on something that may be due to the immature
documentation.

If you aren't, you should be willing to get acquainted with both. In this case it is recommended
to test your understanding and assumptions without ``inxs`` as well. bpython_ and Jupyter_ are
great playgrounds.

.. _bpython: https://bpython-interpreter.org/
.. _delb: https://pypi.org/project/delb/
.. _Jupyter: https://jupyter.org/


Can I get help?
---------------

In case you carefully studied the documentation, just open an issue on the `issue tracker`_.
Mind that you can't get supported to solve your actual problem, but rather to understand and use
``inxs`` as a tool to do so.

.. _issue tracker: https://github.com/funkyfuture/inxs/issues


Can I produce HTML output with ``inxs``?
----------------------------------------

One thing you may do is to rather produce XHTML, but that is lacking modern HTML features you may
want to use. Here's a trick to produce actual HTML:

- produce an XML tree without namespace declarations using the HTML tag set
- serialize the result into a string
- mangle that through pytidylib_

.. _pytidylib: https://pypi.org/project/pytidylib/
