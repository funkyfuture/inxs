inxs – A Python framework for XML transformations without boilerplate.
======================================================================

inxs is inexcessive.

inxs is not XSLT.

inxs is ISC-licensed.

inxs is fully documented here: https://inxs.readthedocs.io/en/latest/

.. image:: https://img.shields.io/pypi/v/inxs.svg
   :target: https://pypi.org/project/inxs
.. image:: https://img.shields.io/pypi/l/inxs.svg
   :target: https://github.com/funkyfuture/inxs/blob/master/LICENSE
.. image:: https://img.shields.io/pypi/pyversions/inxs.svg
.. image:: https://img.shields.io/travis/funkyfuture/inxs/master.svg
   :target: https://travis-ci.org/funkyfuture/inxs
.. image:: https://coveralls.io/repos/github/funkyfuture/inxs/badge.svg
   :target: https://coveralls.io/github/funkyfuture/inxs


At a glimpse
------------

Solving the `Wikipedia XSLT example #1`_:

.. code-block:: python

    def extract_person(node: TagNode):
        return node.attributes['username'], first(node.css_select("name")).full_text

    def append_person(previous_result, result: TagNode):
        result.append_child(result.new_tag_node(
            "name", attributes={"username": previous_result[0]},
            children=[previous_result[1]]
        ))

    transformation = Transformation(
        Rule('person', (extract_person, append_person)),
        result_object='context.result', context={'result': new_tag_node('root')})

    # that's four lines less LOC than the XSLT implementation

Solving the `Wikipedia XSLT example #2`_:

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

    def extract_person(node: TagNode, persons):
        persons.append(
            (first(node.css_select("name")).full_text,
             first(node.css_select("family-name")).full_text)
        )

    def list_persons(previous_result, html: TagNode):
        first(html.css_select("html|body html|ul")).append_child(
            *(html.new_tag_node("li", children=[f'{x[1]}, {x[0]}'])
              for x in previous_result)
        )

    transformation = Transformation(
        generate_skeleton,
        Rule('person', extract_person),
        lib.sort('persons', itemgetter(1)),
        list_persons,
        result_object='context.html', context={'persons': []})

    # that's four lines more LOC than the XSLT implementation

`Here`_ you can find the source repository and issue tracker of inxs.

.. _here: https://github.com/funkyfuture/inxs
.. _Wikipedia XSLT example #1: https://en.wikipedia.org/wiki/XSLT#Example_1_.28transforming_XML_to_XML.29
.. _Wikipedia XSLT example #2: https://en.wikipedia.org/wiki/XSLT#Example_2_.28transforming_XML_to_XHTML.29
