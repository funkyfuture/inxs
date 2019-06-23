from delb import TextNode, Document
from lxml import etree

xml_parser = etree.XMLParser(remove_blank_text=True)


def equal_documents(path_x, path_y):
    x = Document(path_x)
    y = Document(path_y)
    return equal_subtree(x.root, y.root)


def equal_subtree(node, other_node):
    """ Roughly regarding TextNode's whitespaces. """

    if isinstance(node, TextNode):
        assert node.strip() == other_node.strip()
    else:
        assert node == other_node, f"{node} != {other_node}"
        assert len(node) == len(other_node)

    for child, other_child in zip(node.child_nodes(), other_node.child_nodes()):
        equal_subtree(child, other_child)

    return True
