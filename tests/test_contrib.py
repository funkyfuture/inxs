from lxml import etree

from inxs.contrib import remove_empty_elements

from tests import equal_subtree


def test_remove_empty_elements():
    document = etree.fromstring("""
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
    """.strip())
    result = remove_empty_elements(document)

    expected = etree.fromstring("""
<root>
  Hey man, oh leave me alone you know
  
  <c>Hey man, oh Henry, get off the phone, I gotta</c>
  Hey man, I gotta straighten my face
  
  <g>This mellow thighed chick
    Just put my spine out of place
    <i>Hey man, my schooldays insane</i>Hey man, my work's down the drain
  </g>
</root>
    """.strip())  # noqa: W293
    assert equal_subtree(result, expected)
