from lxml import etree


def is_root_element(element: etree._Element) -> bool:
    return element is element.getroottree().getroot()


def remove_element(element: etree._Element, keep_children=False):
    if keep_children:
        for child in element:
            element.addprevious(child)
    element.getparent().remove(element)
