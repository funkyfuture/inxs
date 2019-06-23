import operator
import re

from delb import Document, first, is_text_node, is_tag_node
from pytest import mark

from inxs import (
    Any, If, lib, MatchesAttributes, MatchesXPath, Not, OneOf, Rule, Transformation
)


def test_Any():
    document = Document('<root><a/><b/></root>')
    transformation = Transformation(
        Rule(Any('a', 'b'), lib.set_text('x'))
    )
    result = transformation(document).root
    assert not result._data_node._exists
    assert all(x.content == 'x' for x in result.child_nodes(is_text_node))


def test_any_element():
    document = Document('<root><a/><b/></root>')
    transformation = Transformation(
        Rule('*', lib.set_text('x'))
    )
    for node in transformation(document).root.child_nodes():
        assert node[0] == 'x'


@mark.parametrize('constraint', ({'b': 'x'}, {'b': re.compile('^x$')},
                                 MatchesAttributes(lambda x: {'b': 'x'})))
def test_attributes(constraint):
    document = Document('<root><a b="x"/><a b="y"/></root>')
    transformation = Transformation(
        Rule(constraint, lib.set_text('x'))
    )
    result = transformation(document).root
    assert not result._data_node._exists
    assert result[0].full_text == 'x', str(result)
    assert not len(result[1])


@mark.parametrize('constraint,expected',
                  (({re.compile('default-'): None}, ['item1', 'item2']),
                   ({re.compile('default-'): 'x'}, ['item1']),
                   ({re.compile('default-'): re.compile('x|y')}, ['item1', 'item2']),
                   ({re.compile('-type$'): None}, []),
                   ({'nix': 'da'}, [])))
def test_attributes_re_key(constraint, expected):
    document = Document('<root><item1 default-source="x"/>'
                        '<item2 default-value="y"/><item3/></root>')
    transformation = Transformation(
        Rule(constraint, (lib.get_localname, lib.append('result'))),
        context={'result': []}, result_object='context.result'
    )
    assert transformation(document) == expected


def test_common_conditions():
    document = Document(
        '<root><a href="foo"/><a id="bar"/><a href="peng"/></root>')
    transformation = Transformation(
        Rule('*', (lib.get_attribute('href'), lib.append('references'))),
        common_rule_conditions={'href': None},
        context={'references': []}, result_object='context.references'
    )
    assert transformation(document) == ['foo', 'peng']


@mark.parametrize('selector,expected', (('table > head', 'Table Header'),
                                        ('table + cb', 'X'),
                                        ('table ~ row', '#')))
def test_css_selector(selector, expected):
    document = Document(
        '<section xmlns="foo"><table><head>Table Header</head></table>'
        '<cb type="start">X</cb><row>#</row></section>'
    )
    transformation = Transformation(
        Rule(selector, (lib.get_text, lib.put_variable('result'))),
        result_object='context.result'
    )
    assert transformation(document) == expected


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
    result = transformation(Document('<root/>'))
    assert hasattr(result, 'a')
    assert hasattr(result, 'b')


def test_is_root_condition():
    transformation = Transformation(
        Rule(('a', '/'), lib.append('basket')),
        result_object='context.basket', context={'basket': []}
    )
    result = transformation(Document('<a><a/></a>'))
    assert len(result) == 1


def test_OneOf():
    document = Document('<root x="x"><a x="x"/><b x="x"/></root>')
    transformation = Transformation(
        Rule(OneOf('a', 'b', {'x': 'x'}), lib.set_text('x'))
    )
    result = transformation(document).root
    assert result[0] == 'x'

    assert all(x.full_text == "" for x in result.child_nodes(is_tag_node))


@mark.parametrize('xpath', ('//a', MatchesXPath(lambda x: '//a')))
def test_xpath(xpath):
    document = Document('<root><a/><b/></root>')
    transformation = Transformation(
        Rule(xpath, lib.set_text('x'))
    )
    result = transformation(document).root
    assert not result._data_node._exists
    assert first(result.css_select("a")).full_text == "x"
    assert first(result.css_select("b")).full_text == ""
