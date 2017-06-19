import operator

from lxml import etree

from inxs import *
from inxs import lib


def test_aborts():
    def put_foo(context):
        context.foo = 'foo'

    transformation = Transformation(
        AbortTransformation,
        put_foo,
        result_object='context'
    )
    result = transformation(etree.Element('root'))
    assert getattr(result, 'foo', None) is None


strip_surrounding_content = Transformation(
    lib.resolve_xpath_to_element('left', 'right'),
    name='strip_surrounding_content', result_object='tree'
)


def test_config_is_immutable():
    doc = etree.fromstring("<root><a/><b/></root>")
    tree = etree.ElementTree()
    tree._setroot(doc)
    left = tree.getpath(doc.find('a'))
    right = tree.getpath(doc.find('b'))
    strip_surrounding_content(doc, left=left, right=right)
    strip_surrounding_content(doc, left=left, right=right)


def test_subtransformation():
    subtransformation = Transformation(
        Rule('*', lib.set_localname('pablo'))
    )
    transformation = Transformation(
        lib.f(id, 'root'), lib.put_variable('source_id'),
        subtransformation,
        lib.f(id, 'root'), lib.put_variable('result_id'),
        lib.debug_symbols('source_id', 'result_id'),
        Rule(Not(If(Ref('source_id'), operator.eq, Ref('result_id'))),
             (lib.debug_message('NO!'), lib.debug_symbols('root'),
                 lib.set_localname('neruda'), AbortRule))
    )
    doc = etree.fromstring('<augustus />')
    assert etree.QName(doc).text == 'augustus'

    result = transformation(doc)
    assert result.tag == 'pablo'
