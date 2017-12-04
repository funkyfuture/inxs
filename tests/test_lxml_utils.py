from lxml import etree

from inxs import lxml_utils


def test_remove_element_text_preservation():
    fragment = etree.fromstring(
        '<root><hi>Published in</hi> <docDate>late <hi>February</hi> 1848</docDate><lb/>.</root>'
    )

    lb = lxml_utils.find(fragment, 'lb')
    lxml_utils.remove_elements(lb)
    result = etree.tounicode(fragment)
    assert result == '<root><hi>Published in</hi> <docDate>late <hi>February</hi>' \
                     ' 1848</docDate></root>', result

    doc_date = lxml_utils.find(fragment, 'docDate')
    lxml_utils.remove_elements(doc_date, keep_children=True,
                               preserve_text=True, preserve_tail=True)
    result = etree.tounicode(fragment)
    assert result == '<root><hi>Published in</hi> late <hi>February</hi> 1848</root>', result

    hi = lxml_utils.find(fragment, 'hi')
    lxml_utils.remove_elements(hi, keep_children=False, preserve_text=True, preserve_tail=True)
    result = etree.tounicode(fragment)
    assert result == '<root>Published in late <hi>February</hi> 1848</root>', result


def test_remove_element_text_preservation_part_2():
    fragment = etree.fromstring(
        '<root><a><c/></a><b/>b<d><e/>e</d>d</root>'
    )

    b = lxml_utils.find(fragment, 'b')
    lxml_utils.remove_elements(b, preserve_tail=True)
    result = etree.tounicode(fragment)
    assert result == '<root><a><c/></a>b<d><e/>e</d>d</root>', result

    d = lxml_utils.find(fragment, 'd')
    lxml_utils.remove_elements(d, keep_children=True, preserve_tail=True)
    result = etree.tounicode(fragment)
    assert result == '<root><a><c/></a>b<e/>ed</root>', result


def test_remove_element_text_preservation_part_3():
    fragment = etree.fromstring(
        '<item><name><hi>Rosa</hi></name>, about Quark.</item>'
    )
    name = lxml_utils.find(fragment, 'name')
    lxml_utils.remove_elements(name, keep_children=True, preserve_text=True, preserve_tail=True)
    assert etree.tounicode(fragment) == '<item><hi>Rosa</hi>, about Quark.</item>', etree.tounicode(fragment)
