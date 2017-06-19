import operator
import re

from lxml import etree

from inxs import *
from inxs import lib


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


def test_Any():
    document = etree.fromstring('<root><a/><b/></root>')
    transformation = Transformation(
        Rule(Any('a', 'b'), lib.set_text('x'))
    )
    result = transformation(document)
    assert result.text is None
    assert all(x.text == 'x' for x in result)


def test_any_element():
    document = etree.fromstring('<root><a/><b/></root>')
    transformation = Transformation(
        Rule('*', lib.set_text('x'))
    )
    for element in transformation(document):
        assert element.text == 'x'


def test_attributes():
    document = etree.fromstring('<root><a b="x"/><a b="y"/></root>')
    transformation = Transformation(
        Rule({'b': 'x'}, lib.set_text('x'))
    )
    result = transformation(document)
    assert result.text is None
    assert result[0].text == 'x'
    assert result[1].text is None


def test_attributes_re_key():
    document = etree.fromstring('<root><item1 default-source="x"/>'
                                '<item2 default-value="y"/><item3/></root>')
    transformation = Transformation(
        Rule({re.compile('default-'): None},
             (lib.debug_symbols('element'),  # FIXME
                 lib.get_localname, lib.append_to_list('result'))),
        context={'result': []}, result_object='context.result'
    )
    assert transformation(document) == ['item1', 'item2']


def test_If():
    def return_zero():
        return 0

    def return_one():
        return 1

    transformation = Transformation(
        Rule(If(0, operator.eq, 0), lib.put_variable('a')),
        Rule(Not(If(return_zero, operator.eq, return_one)), lib.put_variable('b')),
        result_object='context'
    )
    result = transformation(etree.Element('root'))
    assert hasattr(result, 'a')
    assert hasattr(result, 'b')


def test_is_root_condition():
    transformation = Transformation(
        Rule(('a', '/'), lib.append_to_list('basket')),
        result_object='context.basket', context={'basket': []}
    )
    result = transformation(etree.fromstring('<a><a/></a>'))
    assert len(result) == 1


def test_OneOf():
    document = etree.fromstring('<root x="x"><a x="x"/><b x="x"/></root>')
    transformation = Transformation(
        Rule(OneOf('a', 'b', {'x': 'x'}), lib.set_text('x'))
    )
    result = transformation(document)
    assert result.text == 'x'
    assert all(x.text is None for x in result)


def test_xpath():
    document = etree.fromstring('<root><a/><b/></root>')
    transformation = Transformation(
        Rule('//a', lib.set_text('x'))
    )
    result = transformation(document)
    assert result.text is None
    assert result.find('a').text == 'x'
    assert result.find('b').text is None
