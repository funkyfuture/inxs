from lxml import etree


def is_root_element(element: etree._Element) -> bool:
    return element is element.getroottree().getroot()


def remove_element(element: etree._Element):
    element.getparent().remove(element)
