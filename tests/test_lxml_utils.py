from lxml import etree

from inxs import lxml_utils


def test_remove_element_text_preservation():
    fragment = etree.fromstring(
        '<root><hi>Published in</hi> <docDate><hi>February</hi> 1848</docDate>.</root>'
    )
    doc_date = lxml_utils.find(fragment, 'docDate')
    lxml_utils.remove_elements(doc_date, keep_children=True, preserve_text=True)
    result = etree.tostring(fragment).decode()
    assert result == '<root><hi>Published in</hi> <hi>February</hi> 1848.</root>', result
