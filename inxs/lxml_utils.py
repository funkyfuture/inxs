""" Some helper functions for ``lxml`` objects. """
from copy import deepcopy
from typing import Iterator

from lxml import etree

from inxs import utils


def extract_text(element: etree._Element, include_tail=False,
                 reduce_whitespaces=True) -> str:
    """ Returns all text that is contained in the given ``element`` including its
        descendants. The element's tail is appended when ``include_tail`` is provided as
        ``True``, a boolean also toggles whether :func:`~inxs.utils.reduce_whitespaces`
        shall be applied on the result.
    """
    result = ''
    result += element.text or ''
    for child in element:
        result += extract_text(child, include_tail=True, reduce_whitespaces=False)
    if include_tail:
        result += element.tail or ''
    return utils.reduce_whitespaces(result) if reduce_whitespaces else result


def find(element, path):
    """ A helper function around a :attr:`lxml.etree._Element.find` that passes the
        element's namespace mapping.
    """
    return element.find(path, namespaces=element.nsmap)


def is_root_element(element: etree._Element) -> bool:
    """ Tests whether the given element is the root of the tree object.
        Not to be mixed up with the :term:`transformation root`.
    """
    return element is element.getroottree().getroot()


def merge_nodes(src: etree._Element, dst: etree._Element):
    """ Merges the node ``src`` including their subelements to ``dst``. The nodes are
        considered as equal - and thus merged - if their fully qualified names are
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


def remove_elements(*elements: etree.ElementBase, keep_children=False,
                    preserve_text=False,
                    preserve_tail=False) -> None:
    """ Removes the given elements from its tree. Unless ``keep_children`` is passed
        as ``True``, its children vanish with it into void. If ``preserve_text`` is
        ``True``, the text and tail of a deleted element will be preserved either in its
        left sibling's tail or its parent's text.
    """
    for element in elements:
        if preserve_text and element.text:
            previous = element.getprevious()
            if previous is None:

                parent = element.getparent()
                if parent.text is None:
                    parent.text = ''
                parent.text += element.text
            else:
                if previous.tail is None:
                    previous.tail = element.text
                else:
                    previous.tail += element.text

        if preserve_tail and element.tail:
            if keep_children and len(element):
                if element[-1].tail:
                    element[-1].tail += element.tail
                else:
                    element[-1].tail = element.tail
            else:
                previous = element.getprevious()
                if previous is None:
                    parent = element.getparent()
                    if parent.text is None:
                        parent.text = ''
                    parent.text += element.tail
                else:
                    if len(element):
                        if element[-1].tail is None:
                            element[-1].tail = element.tail
                        else:
                            element[-1].tail += element.tail
                    else:
                        if previous.tail is None:
                            previous.tail = ''
                        previous.tail += element.tail

        if keep_children:
            for child in element:
                element.addprevious(child)
        element.getparent().remove(element)


def subelement(element, *args, text=None, **kwargs):
    """ A convenience wrapper around :func:`lxml.etree.SubElement` that takes an
        additional keyword argument ``text`` to set the created element's text. """
    result = etree.SubElement(element, *args, **kwargs)
    result.text = text
    return result


def traverse_df_ltr_btt(root: etree._Element) -> Iterator[etree._Element]:
    def yield_children(element):
        for child in element:
            yield from yield_children(child)
        yield element

    yield from yield_children(root)


def traverse_df_ltr_ttb(root: etree._Element) -> Iterator[etree._Element]:
    yield from root.iter()


def traverse_root(root: etree._Element) -> Iterator[etree._Element]:
    yield root
