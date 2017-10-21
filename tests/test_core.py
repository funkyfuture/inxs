import operator
from types import SimpleNamespace

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


def test_dotted_Ref():
    transformation = SimpleNamespace(
        _available_symbols={'root': SimpleNamespace(item='check')})
    assert Ref('root.item')(transformation) == 'check'


def test_grouped_steps():
    def append_to_list(value):
        def appender(list):
            list.append(value)
        return appender

    stpgrp_c = (append_to_list(3), append_to_list(4))
    stpgrp_b = (append_to_list(2), stpgrp_c, append_to_list(5))
    stpgrp_a = (append_to_list(1))

    transformation = Transformation(
        append_to_list(0),
        stpgrp_a,
        stpgrp_b,
        context={'list': []}, result_object='context.list'
    )
    result = transformation(etree.Element('root'))
    for exp, val in enumerate(result):
        assert exp == val


def test_SkipToNextElement():
    def more_complicated_test(element):
        # well, supposedly
        if 'x' not in element.attrib:
            raise SkipToNextElement
        if int(element.attrib['x']) % 2:
            raise SkipToNextElement
        return element.tag

    transformation = Transformation(
        Rule('*', (more_complicated_test, lib.append('evens'))),
        context={'evens': []}, result_object='context.evens'
    )
    doc = etree.fromstring('<root><a x="1"/><b x="2"/><c x="3"/><d x="4"/></root>')
    assert transformation(doc) == ['b', 'd']


def test_subtransformation():
    subtransformation = Transformation(
        Rule('*', lib.set_localname('pablo'))
    )
    transformation = Transformation(
        lib.f(id, Ref('root')), lib.put_variable('source_id'),
        subtransformation,
        lib.f(id, Ref('root')), lib.put_variable('result_id'),
        lib.debug_symbols('source_id', 'result_id'),
        Rule(Not(If(Ref('source_id'), operator.eq, Ref('result_id'))),
             (lib.debug_message('NO!'), lib.debug_symbols('root'),
                 lib.set_localname('neruda'), AbortRule))
    )
    doc = etree.fromstring('<augustus />')
    assert etree.QName(doc).text == 'augustus'

    result = transformation(doc)
    assert result.tag == 'pablo'
