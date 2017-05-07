from lxml import etree


xml_parser = etree.XMLParser(remove_blank_text=True)


def parse(text: str) -> etree._Element:
    return etree.fromstring(text.strip(), parser=xml_parser)


def equal_elements(element, other_element):
    assert etree.QName(element) == etree.QName(other_element), \
        f'{etree.QName(element)} != {etree.QName(other_element)}'
    assert element.attrib == other_element.attrib
    assert element.text == other_element.text, f'{element.text} != {other_element.text}'
    assert element.tail == other_element.tail
    assert len(element) == len(other_element)
    assert all(equal_elements(x, y) for x, y in zip(element, other_element))
    return True
