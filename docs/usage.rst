Usage
=====

``inxs`` is designed to allow Pythonistas and other cultivated folks to write sparse and readable
transformations that take lxml_ objects as input. Most likely they will return the same, but
there's no limitation into what the data can be mangled.
It does so by providing a framework that traverses an XML tree, tests elements, pulls and
manipulates data in a series of steps. It supports the combination of reusable and generalized
logical units of expressions and actions. Therefore there's also a library with functions to deploy
and a module with contributed transformations.

.. _lxml: http://lxml.de/

Though ``inxs`` should be usable for any problem that XSLT could solve, it is not modeled to
address XSLT users to get a quick grip on it. Anyone who enjoys XSLT should continue to do so.
So far the framework performs with acceptable speed with uses on text documents from the
humanities. Some optimizations will certainly be investigated, but speed is not a design aim of the
project.

Let's break its usage down with the second example from the ``README``:

.. code-block:: python
   :linenos:

    transformation = Transformation(
        lib.set_elementmaker(namespace='http://www.w3.org/1999/xhtml'),
        generate_skeleton,
        Rule(('person',), extract_person),
        lib.sorter('persons', itemgetter(1)),
        list_persons,
        result_object='context.html', context={'persons': []})

A transformation is set up by instantiating a :class:`inxs.Transformation` (line 1) with a series
of :term:`transformation steps` (lines 2-6) and two :term:`configuration` values (line 7).

The first step in line 2 uses :func:`inxs.lib.set_elementmaker` to put an ElementMaker_ instance
into the :term:`context` namespace. In this case its name will be the default ``e``, the
``namespace`` argument is passed to its initialization.

.. _ElementMaker: http://lxml.de/api/lxml.builder.ElementMaker-class.html

Now handler functions with that name can consume that as an argument. So does the one in line 3:

.. code-block:: python

    def generate_skeleton(context, e):
        context.html = e.html(
            e.head(e.title('Testing XML Example')),
            e.body(e.h1('Persons'), e.ul()))
        context.persons_list = context.html.xpath('./body/ul', smart_prefix=True)[0]

When a transformation calls a handler function it does so by applying dependency injection as may
be known from pytest's fixtures_. The passed arguments are resolved from
:attr:`inxs.Transformation._available_symbols` where any object that has previously been added to
the context are available (``e`` so far) as well as the ``context`` itself. After a bare HTML tree
is generated, the ``ul`` element within it is added to the context as ``persons_list``.

.. _fixtures: https://docs.pytest.org/en/latest/fixture.html

Line 4 defines something that is used more often in real world uses than here. A :class:`inxs.Rule`
that tests the transformation root and its descendants for defined properties. In the example all
elements with a ``person`` tag will be passed to this handler function:

.. code-block:: python

    def extract_person(element, persons):
        persons.append((element.find('name').text, element.find('family-name').text))

The `lxml.Element`_ API is used to get name and family name and append it as a tuple to a list that
was defined in the ``context`` argument of the configuration values (line 7).

.. _lxml.Element: http://lxml.de/api/lxml.etree._Element-class.html

Rules can also test anything outside the scope of an element, the utilized functions however aren't
'dependency injected' to avoid overhead. They are called with ``element`` and ``transformation`` as
arguments and take it from there. See :func:`inxs.If` for an example.

The last two steps (line 5 and 6) eventually sort (:func:`inxs.lib.sorter` with
:func:`operator.itemgetter`) and append the data to the HTML tree that was prepared in line 3:

.. code-block:: python

    def list_persons(previous_result, persons_list, e):
        persons_list.extend(e.li(f'{x[1]}, {x[0]}') for x in previous_result)

The argument ``previous_result`` is resolved to the object that the previous function returned,
again the Element API and Python's f-strings are used to generate the result.

As the transformation was configured with ``context.html`` as result object, the transformation
returns the object referenced as ``html`` (see handler function in line 3) from the context. If the
transformation hasn't explicitly configured a result object, (per default a copy of) the input tree
or element is returned. Any other data is discarded.

The initialized transformation can be called with an `lxml.ElementTree`_ or an element:

    >>> result = transformation(xml_tree)

When given a tree, the transformation root will be the tree's root element. A passed element
doesn't need to be the document's root, leaving siblings and ancestors untouched.

.. _lxml.ElementTree: http://lxml.de/api/lxml.etree._ElementTree-class.html

Transformations can also be used as simple steps - then invoked with the transformation root - or
as rule handlers (then invoked with each matching element). At the moment such sub-transformations
aren't operating on copies, but this is quiet implicit and is going to be changed in some way.

Any transformation step, condition or handler can be grouped into sequences to encourage code
recycling - But don't take that as a permission to barbarously patching fragments of existin
solutions together that you might feel are similar to your problem.

Now that the authoritarian part is reached, be advised that using expressive and unambiguous names
is essential when designing transformations and their components. As a rule of thumb, a simple
transformation step should fit into one line, rules into two, maybe up to four. If it gets
confusing to read, use variables, grouping (more reusability) or dedicated functions (more
performance) - again, mind the names!
Reciting the `Zen of Python`_ on a daily basis makes you a beautiful person. Yes, even more.

.. _Zen of Python: https://zen-of-python.info/

To get a grip on implementing own conditions and handlers, it's advised to study the
:mod:`inxs.lib` module.

And now, space for some spots-on-.. sections.


.. _traversal_strategies:

Traversal strategies
--------------------

When a rule is evaluated, the documnént (sub-)tree is traversed in a specified order. There are
three aspects that can be combined to define that order and are available as constants that are to
be or'ed bitwise:

- ``inxs.TRAVERSE_DEPTH_FIRST`` / ``inxs.TRAVERSE_WIDTH_FIRST``
- ``inxs.TRAVERSE_LEFT_TO_RIGHT`` / ``inxs.TRAVERSE_RIGHT_TO_LEFT``
- ``inxs.TRAVERSE_TOP_TO_BOTTOM`` / ``inxs.TRAVERSE_BOTTOM_TO_TOP``

Rules can be initiated with such value as ``traversal_order`` argument and override the
transformation's one (that one defaults to
``TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_TOP_TO_BOTTOM``). Not all strategies are
are implemented yet.

``inxs.TRAVERSE_ROOT_ONLY`` sets a strategy that only considers the transformation root. It is also
set implicitly for rules that contain a ``'/'`` as condition (see :ref:`rule_condition_shortcuts`).


.. _rule_condition_shortcuts:

Rule condition shortcuts
------------------------

Strings can be used to specify certain rule conditions:

- ``/`` selects only the transformation root
- any string that contains a colon (but not more that one consecutively) selects elements with
  a namespace that matches the string
- strings that contain only letters select elements whose local name matches the string
- all other strings will select all elements that an XPath evaluation of that string returns

Another shortcut is to pass a dictionary to test an element's attributes, see
:func:`inxs.MatchesAttributes` for details.

Speaking of conditions, see :func:`inxs.Any`, :func:`inxs.OneOf` and :func:`inxs.Not` to overcome
the logical and evaluation of all tests.


Debugging / Logging
-------------------

There are functions in the :mod:`inxs.lib` module to log information about a transformation's state
at info level. There's a ``logger`` object in that module too that needs to be set up with a
handler and a log level in order to get the output (see :mod:`logging`). ``inxs`` itself produces
very noisy messages at debug level.

Due to its rather sparse and dynamic design, the exception tracebacks that are produced aren't
very helpful as they contain no information about the context of an exception. To tackle one of
those, a minimal non-working example is preferred to debug.


Glossary
--------

.. glossary::

   context
      The context of a transformation is a :class:`types.SimpleNamespace` instance and intended to
      hold any mutable values during a transformation. It is initialized from the values stored in
      the :term:`configuration`'s ``context`` value and the overriding keywords provided when
      calling a :class:`inxs.Transformation` instance. Essentially everything can be put onto the
      context, but these names are reserved:
      ``root`` points to the element that the currently processed transformation was called with.
      Or in case it was called with a tree, it points to its root element.
      ``tree`` always points to the tree object of the currently processed document.
