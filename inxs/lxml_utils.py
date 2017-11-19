""" Some helper functions for ``lxml`` objects. """
from copy import deepcopy

from lxml import etree


def find(element, path):
    """ A helper function around a :attr:`lxml.etree._Element.find` that passes the element's
        namespace mapping.
    """
    return element.find(path, namespaces=element.nsmap)


def is_root_element(element: etree._Element) -> bool:
    """ Tests whether the given element is the root of the tree object.
        Not to be mixed up with the root element of a possible sub-document a transformation may
        be called with.
    """
    return element is element.getroottree().getroot()


def merge_nodes(src: etree._Element, dst: etree._Element):
    """ Merges the node ``src`` including their subelements to ``dst``. The
        Nodes are considered as equal - and thus merged - if their fully qualified names are
        identical.
        Different matching and merging strategies will be added as needed.
    """
    def child_with_qname(element: etree._Element, qname: etree.QName):
        for child in element.iterchildren(qname.text):
            if etree.QName(child).text == qname.text:
                return child

    merged_elements = set()

    for child in dst.iterchildren():
        twin = child_with_qname(src, etree.QName(child))
        if twin is not None:
            merge_nodes(twin, child)
            merged_elements.add(twin)

    for child in src.iterchildren():
        if child in merged_elements:
            continue
        dst.append(deepcopy(child))


def remove_elements(*elements: etree.ElementBase, keep_children=False, preserve_text=False) -> None:
    """ Removes the given elements from its tree. Unless ``keep_children`` is passed as ``True``,
        its children vanish with it into void. If ``preserve_text`` is ``True``, the text and tail
        of a deleted element will be preserved either in its left sibling's tail or its parent's
        text.
    """
    for element in elements:
        if preserve_text:
            previous = element.getprevious()
            if previous is None:
                parent = element.getparent()
                if parent.text is None:
                    parent.text = ''
                if element.text:
                    parent.text += element.text
                if element.tail:
                    parent.text += element.tail
            else:
                if previous.tail is None:
                    previous.tail = ''
                if element.text:
                    previous.tail += element.text
                if element.tail:
                    previous.tail += element.tail

        if keep_children:
            for child in element:
                element.addprevious(child)
        element.getparent().remove(element)


def subelement(element, *args, text=None, **kwargs):
    """ A convenience wrapper around :func:`lxml.etree.SubElement` that takes an additional
        keyword argument ``text`` to set the created element's text. """
    result = etree.SubElement(element, *args, **kwargs)
    result.text = text
    return result
