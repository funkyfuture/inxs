from lxml import etree


xml_parser = etree.XMLParser(remove_blank_text=True)


def equal_documents(path_x, path_y):
    with open(path_x, 'rt') as f:
        x = etree.parse(f)
    with open(path_y, 'rt') as f:
        y = etree.parse(f)
    return equal_subtree(x.getroot(), y.getroot(), ignore_whitespaces=True)


def equal_subtree(element, other_element, ignore_whitespaces=False):
    def compare_text(text, other_text):
        if ignore_whitespaces:
            if text is None:
                text = ''
            text = text.strip()
            if other_text is None:
                other_text = ''
            other_text = other_text.strip()
        return text == other_text

    assert etree.QName(element) == etree.QName(other_element), \
        '{} != {}'.format(etree.QName(element), etree.QName(other_element))
    assert element.attrib == other_element.attrib
    assert compare_text(element.text, other_element.text), \
        '{} != {}'.format(element.text, other_element.text)
    assert compare_text(element.tail, other_element.tail), \
        '{} != {}'.format(element.tail, other_element.tail)
    assert len(element) == len(other_element), \
        '{}: {} / {}'.format(element.tag, len(element), len(other_element))
    assert all(equal_subtree(x, y, ignore_whitespaces) for x, y in zip(element, other_element))
    return True


def parse(text: str) -> etree._Element:
    return etree.fromstring(text.strip(), parser=xml_parser)
