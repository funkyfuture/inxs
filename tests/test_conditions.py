import operator
import re

from lxml import etree
from pytest import mark

from inxs import *
from inxs import lib


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


@mark.parametrize('constraint', ({'b': 'x'}, {'b': re.compile('^x$')},
                                 MatchesAttributes(lambda x: {'b': 'x'})))
def test_attributes(constraint):
    document = etree.fromstring('<root><a b="x"/><a b="y"/></root>')
    transformation = Transformation(
        Rule(constraint, lib.set_text('x'))
    )
    result = transformation(document)
    assert result.text is None
    assert result[0].text == 'x'
    assert result[1].text is None


@mark.parametrize('constraint,expected',
                  (({re.compile('default-'): None}, ['item1', 'item2']),
                   ({re.compile('default-'): 'x'}, ['item1']),
                   ({re.compile('default-'): re.compile('x|y')}, ['item1', 'item2']),
                   ({re.compile('-type$'): None}, []),
                   ({'nix': 'da'}, [])))
def test_attributes_re_key(constraint, expected):
    document = etree.fromstring('<root><item1 default-source="x"/>'
                                '<item2 default-value="y"/><item3/></root>')
    transformation = Transformation(
        Rule(constraint, (lib.get_localname, lib.append('result'))),
        context={'result': []}, result_object='context.result'
    )
    assert transformation(document) == expected


def test_common_conditions():
    document = etree.fromstring('<root><a href="foo"/><a id="bar"/><a href="peng"/></root>')
    transformation = Transformation(
        Rule('*', (lib.get_attribute('href'), lib.append('references'))),
        common_rule_conditions={'href': None},
        context={'references': []}, result_object='context.references'
    )
    assert transformation(document) == ['foo', 'peng']


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
        Rule(('a', '/'), lib.append('basket')),
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


@mark.parametrize('xpath', ('//a', MatchesXPath(lambda x: '//a')))
def test_xpath(xpath):
    document = etree.fromstring('<root><a/><b/></root>')
    transformation = Transformation(
        Rule(xpath, lib.set_text('x'))
    )
    result = transformation(document)
    assert result.text is None
    assert result.find('a').text == 'x'
    assert result.find('b').text is None
