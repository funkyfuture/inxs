from delb import Document, TextNode

from inxs.contrib import remove_empty_nodes

from tests import equal_subtree


def test_remove_empty_elements():
    document = Document(
        """
    <root>
      <a/>Hey man, oh leave me alone you know
      <b/>
      <c>Hey man, oh Henry, get off the phone, I gotta</c>
      <d/>Hey man, I gotta straighten my face
      <e><f1/><f2/><f3/></e>
      <g>This mellow thighed chick
        <h/>Just put my spine out of place
        <i>Hey man, my schooldays insane</i><j/>Hey man, my work's down the drain
      </g>
    </root>
    """.strip()
    )
    result = remove_empty_nodes(document)
    result.merge_text_nodes()

    expected = Document(
        """
    <root>Hey man, oh leave me alone you know

      <c>Hey man, oh Henry, get off the phone, I gotta</c>
      Hey man, I gotta straighten my face

      <g>This mellow thighed chick
        Just put my spine out of place
        <i>Hey man, my schooldays insane</i>Hey man, my work's down the drain
      </g>
    </root>
    """.strip()
    )  # noqa: W293
    assert isinstance(expected.root.last_child, TextNode)
    assert not expected.root.last_child.strip()
    expected.root.last_child.detach()

    assert not result.css_select("d")
    assert not result.css_select("e")

    assert equal_subtree(result.root, expected.root)
