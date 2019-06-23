Usage
=====

``inxs`` is designed to allow Pythonistas and other cultivated folks to write sparse and readable
transformations that take delb_ objects as input. Most likely they will return the same, but
there's no limitation into what the data can be mangled.
It does so by providing a framework that traverses an XML tree, tests tag nodes, pulls and
manipulates data in a series of steps. It supports the combination of reusable and generalized
logical units of expressions and actions. Therefore there's also a library with functions to deploy
and a module with contributed transformations.

.. _delb: https://pypi.org/project/delb/

Though ``inxs`` should be usable for any problem that XSLT could solve, it is not modeled to
address XSLT users to get a quick grip on it. Anyone who enjoys XSLT should continue to do so.
So far the framework performs with acceptable speed with uses on text documents from the
humanities.

Let's break its usage down with the second example from the ``README``:

.. code-block:: python
   :linenos:

    transformation = Transformation(
        generate_skeleton,
        Rule('person', extract_person),
        lib.sort('persons', itemgetter(1)),
        list_persons,
        result_object='context.html', context={'persons': []})

A transformation is set up by instantiating a :class:`inxs.Transformation` (line 1) with a series
of :term:`transformation steps` (lines 2-5) passed as positional :term:`argument` s and two
:term:`configuration` values (line 6) provided as keyword arguments.

The first step (line 2) is a function that creates a skeleton for the resulting HTML markup and
stores it in the ``context`` namespace:

.. code-block:: python

    def generate_skeleton(context):
        context.html = new_tag_node(
            "html", namespace='http://www.w3.org/1999/xhtml',
            children=(
                tag("head",
                    tag("title", "Testing XML Example")),
                tag("body", (
                    tag("h1", "Persons"),
                    tag("ul")
                )),
            )
        )

When a transformation calls a handler function it does so by applying dependency injection as may
be known from pytest's fixtures_. The passed arguments are resolved from
:attr:`inxs.Transformation._available_symbols` where any object that has previously been added to
the ``context`` namespace is available as well as the ``context`` itself.

.. _fixtures: https://docs.pytest.org/en/latest/fixture.html

Line 3 defines something that is used more often in real world uses than here. A :class:`inxs.Rule`
that tests the :term:`transformation root` and its descendants for defined properties. In the
example all nodes with a ``person`` tag will be passed to the associated
:term:`handler function`:

.. code-block:: python

    def extract_person(node: TagNode, persons):
        persons.append(
            (first(node.css_select("name")).full_text,
             first(node.css_select("family-name")).full_text)
        )

`delb`'s API is used to fetch child nodes of the matching nodes, extract their text and appends
them in a tuple to a list that was defined in the ``context`` argument of the configuration values
(line 7).

Rules can also test anything outside the scope of a node, the utilized functions however aren't
'dependency injected' to avoid overhead. They are called with ``node`` and ``transformation`` as
arguments and take it from there. See :func:`inxs.If` for an example.

The last two steps (line 4 and 5) eventually sort (:func:`inxs.lib.sort` with
:func:`operator.itemgetter`) and append the data to the HTML tree that was prepared by the step in
line 2:

.. code-block:: python

    def list_persons(previous_result, html: TagNode):
        first(html.css_select("html|body html|ul")).append_child(
            *(html.new_tag_node("li", children=[f'{x[1]}, {x[0]}'])
              for x in previous_result)
        )

The argument ``previous_result`` is resolved to the object that the previous function returned,
again the ``delb`` API and Python's :term:`f-string` s are used to generate the result.

As the transformation was configured with ``context.html`` as result object, the transformation
returns the object referenced as ``html`` (see handler function in line 2) from the context. If the
transformation hasn't explicitly configured a result object, (per default a copy of) the
:term:`transformation root` is returned. Any other data is discarded.

The initialized transformation can now be called with a :class:`delb.Document` or
:class:`delb.TagNode` instance as :term:`transformation root`:

    >>> result = transformation(document)  # doctest: +SKIP

A :term:`transformation root` can be any node within a document, leaving siblings and ancestors
untouched. A transformation works on a copy of the document's tree unless the configuration
contains a key ``copy`` set to ``False`` or the transformation is called with such keyword
argument.

Transformations can also be used as simple steps - then invoked with the
:term:`transformation root` - or as rule handlers - then invoked with each matching node.
Per default these do not operate on copies, to do so :func:`inxs.lib.f` can be employed:

.. code-block:: python

    # as a simple step
    f(sub_transformation, 'root', copy=True)
    # as a rule handler
    f(sub_transformation, 'node', copy=True)

Any transformation step, condition or handler can be grouped into :term:`sequence` s to encourage
code recycling - But don't take that as a permission to barbarously patching fragments of existing
solutions together that you might feel are similar to your problem. It's taken care that the
items are retained as when a transformation was initialized if groups were :term:`mutable` types.

Now that the authoritarian part is reached, be advised that using expressive and unambiguous names
is essential when designing transformations and their components. As a rule of thumb, a simple
transformation step should fit into one line, rules into two, maybe up to four. If it gets
confusing to read, use variables, grouping (more reusability) or dedicated functions (more
performance) - again, mind the names!
Reciting the `Zen of Python`_ on a daily basis makes you a beautiful person. Yes, even more.

.. _Zen of Python: https://zen-of-python.info/

To get a grip on implementing own condition test functions and :term:`handler function` s, it's
advised to study the :mod:`inxs.lib` module.

And now, space for some spots-on-.. sections.


.. _traversal_strategies:

Traversal strategies
--------------------

When a rule is evaluated, the document (sub-)tree is traversed in a specified order. There are
three aspects that must be combined to define that order and are available as constants that are to
be or'ed bitwise:

- ``inxs.TRAVERSE_DEPTH_FIRST`` / ``inxs.TRAVERSE_WIDTH_FIRST``
- ``inxs.TRAVERSE_LEFT_TO_RIGHT`` / ``inxs.TRAVERSE_RIGHT_TO_LEFT``
- ``inxs.TRAVERSE_TOP_TO_BOTTOM`` / ``inxs.TRAVERSE_BOTTOM_TO_TOP``

Rules can be initiated with such value as ``traversal_order`` argument and override the
transformation's one (that one defaults to ``…_DEPTH_FIRST | …_LEFT_TO_RIGHT | …_TOP_TO_BOTTOM``).
Not all strategies are are implemented yet.

``inxs.TRAVERSE_ROOT_ONLY`` sets a strategy that only considers the :term:`transformation root`. It
is also set implicitly for rules that contain a ``'/'`` as condition (see
:ref:`rule_condition_shortcuts`).


.. _rule_condition_shortcuts:

Rule condition shortcuts
------------------------

Strings can be used to specify certain rule conditions:

- ``/`` selects only the :term:`transformation root`
- ``*`` selects all nodes - should only be used if there are no other conditions
- any string that contains ``://`` selects nodes with a namespace that matches the string
- strings that contain only letters select nodes whose *local* name matches the string
- if a string can be translated to an XPath expression with cssselect_ and thus can be considered a
  valid css selector, the result is used like the following; mind that you can use
  `namespace prefixes`_ if you know the prefixes, otherwise this is not an option to match a
  node from a namespace that's not the :term:`transformation root`'s default
- all other strings will select all nodes that an XPath evaluation of that string on the
  :term:`transformation root` returns

Another shortcut is to pass a dictionary to test an node's attributes, see
:func:`inxs.MatchesAttributes` for details.

Speaking of conditions, see :func:`inxs.Any`, :func:`inxs.OneOf` and :func:`inxs.Not` to overcome
the logical ``and`` evaluation of all tests.

.. _cssselect: https://cssselect.readthedocs.io
.. _namespace prefixes: https://cssselect.readthedocs.io/#namespaces


Global configuration
--------------------

``inxs`` caches and reuses evaluator and handler functions with identical arguments where possible.
By default these caches are not limited in size and they might eventually grow larger than the
memory that was saved in big, long-running applications that create a lot of short-living
transformations. To limit the size of each of these last-recently-used-caches, the environment
variable :envvar:`HANDLER_CACHES_SIZE` can be set. The value should be a power of two.


Caveats
-------

Modifications during iteration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to iteration over mutable types in Python, adding, moving or deleting nodes to the
tree breaks the iteration of a rule over nodes. Thus such modifications must be applied in a
simple transformation step; e.g. to remove all ``<br>`` nodes from a document:

.. code-block:: python

    def collect_trash(node, trashbin):
        trashbin.append(node)

    transformation = Transformation(
        Rule('br', collect_trash),
        lib.remove_nodes('trashbin'),
        context={'trashbin': []})


Debugging / Logging
-------------------

There are functions in the :mod:`inxs.lib` module to log information about a transformation's state
at info level. There's a ``logger`` object in that module too that needs to be set up with a
handler and a log level in order to get the output (see :mod:`logging`). ``inxs`` itself produces
very noisy messages at debug level.

:func:`inxs.lib.debug_dump_document`, :func:`inxs.lib.debug_message` and
:func:`inxs.lib.debug_symbols` can be used as :term:`handler function`.
:func:`inxs.lib.dbg` and :func:`inxs.lib.nfo` can be used within test and handler functions.

Due to its rather sparse and dynamic design, the exception tracebacks that are produced aren't
very helpful as they contain no information about the context of an exception. To tackle one of
those, a minimal non-working example is preferred to debug.


Glossary
--------

.. glossary::

   configuration
      The configuration of a transformation is a :class:`types.SimpleNamespace` object that is
      bound as its ``config`` property and is populated by passing
      :term:`keywords arguments <argument>` to its initialization.
      It is intended to be an :term:`immutable` container for key-value-pairs that persist through
      transformation's executions. Mind that it's immutability isn't completely enforced,
      manipulating it or its members might result in unexpected behaviour. It can be referred to in
      :term:`handler function`'s signatures as ``config``, the same is true for its member unless
      overridden in :attr:`inxs.Transformation._available_symbols`. See
      :class:`inxs.Transformation` for details on reserved names in the configuration namespace.

   context
      The context of a transformation is a :class:`types.SimpleNamespace` instance and intended to
      hold any :term:`mutable` values during a transformation. It is initialized from the values
      stored in the :term:`configuration`'s ``context`` value and the overriding keywords provided
      when calling a :class:`inxs.Transformation` instance.

   handler function
      Handler :term:`functions <function>` can be employed as simple :term:`transformation steps`
      or as conditionally executed ``handlers`` of a :class:`inxs.Rule`. Any of their signature's
      :term:`argument` s must be available in :attr:`inxs.Transformation._available_symbols` upon
      the time the function gets called.

   transformation root
      This is the node that a transformation instance is called with. Any traverser will return
      neither its ancestors nor its siblings.

   transformation steps
      Transformation steps are :term:`handler functions <handler function>` or :class:`inxs.Rule`
      s that define the actions taken when a transformation is processed. The steps are stored as
      a linear graph, rudimentary branching can be achieved by using rules that call other
      transformations.
