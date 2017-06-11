from lxml import etree

from inxs import lib, Transformation


strip_surrounding_content = Transformation(
    lib.resolve_xpath_to_element('left', 'right'),
    name='strip_surrounding_content', result_object='tree'
)


def test_config_is_immutable():
    doc = etree.fromstring("<root><a/><b/></root>")
    tree = etree.ElementTree()
    tree._setroot(doc)
    left = tree.getpath(doc.find('a'))
    right = tree.getpath(doc.find('b'))
    strip_surrounding_content(doc, left=left, right=right)
    strip_surrounding_content(doc, left=left, right=right)
