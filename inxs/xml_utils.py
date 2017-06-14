""" Some helper functions for ``lxml`` objects. """

from lxml import etree


def is_root_element(element: etree._Element) -> bool:
    """ Tests whether the given element is the root of the tree object.
        Not to be mixed up with the root element of a possible sub-document a transformation may
        be called with.
    """
    return element is element.getroottree().getroot()


def remove_element(element: etree._Element, keep_children=False) -> None:
    """ Removes the given element from its tree. Unless ``keep_children`` is passed as ``True``,
        its children vanish with it into void.
    """
    if keep_children:
        for child in element:
            element.addprevious(child)
    element.getparent().remove(element)
