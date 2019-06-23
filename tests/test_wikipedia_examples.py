from operator import itemgetter

from delb import Document, TagNode, first, new_tag_node, tag

from inxs import lib, Rule, Transformation

from tests import equal_subtree

wp_document = Document(
    """
<persons>
  <person username="JS1">
    <name>John</name>
    <family-name>Smith</family-name>
  </person>
  <person username="MI1">
    <name>Morka</name>
    <family-name>Ismincius</family-name>
  </person>
</persons>
"""
)


def test_wikipedia_example_1():
    expected = Document(
        """
        <root>
          <name username="JS1">John</name>
          <name username="MI1">Morka</name>
        </root>
    """
    )

    def extract_person(node: TagNode):
        return node.attributes["username"], first(node.css_select("name")).full_text

    def append_person(previous_result, result: TagNode):
        result.append_child(
            result.new_tag_node(
                "name",
                attributes={"username": previous_result[0]},
                children=[previous_result[1]],
            )
        )

    transformation = Transformation(
        Rule("person", (extract_person, append_person)),
        result_object="context.result",
        context={"result": new_tag_node("root")},
    )

    # that's four lines less LOC than the XSLT implementation

    assert equal_subtree(transformation(wp_document.root), expected.root)


def test_wikipedia_example_2():
    expected = Document(
        """
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head> <title>Testing XML Example</title> </head>
          <body>
            <h1>Persons</h1>
            <ul>
              <li>Ismincius, Morka</li>
              <li>Smith, John</li>
            </ul>
          </body>
        </html>
    """
    )

    def generate_skeleton(context):
        context.html = new_tag_node(
            "html",
            namespace="http://www.w3.org/1999/xhtml",
            children=(
                tag("head", tag("title", "Testing XML Example")),
                tag("body", (tag("h1", "Persons"), tag("ul"))),
            ),
        )

    def extract_person(node: TagNode, persons):
        persons.append(
            (
                first(node.css_select("name")).full_text,
                first(node.css_select("family-name")).full_text,
            )
        )

    def list_persons(previous_result, html: TagNode):
        first(html.css_select("html|body html|ul")).append_child(
            *(
                html.new_tag_node("li", children=[f"{x[1]}, {x[0]}"])
                for x in previous_result
            )
        )

    transformation = Transformation(
        generate_skeleton,
        Rule("person", extract_person),
        lib.sort("persons", itemgetter(1)),
        list_persons,
        result_object="context.html",
        context={"persons": []},
    )

    # that's four lines more LOC than the XSLT implementation

    assert equal_subtree(transformation(wp_document.root), expected.root)
