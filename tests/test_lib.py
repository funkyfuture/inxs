from itertools import permutations
from types import SimpleNamespace

from lxml import builder, etree
from pytest import mark

from inxs import lib, Ref, Rule, Transformation
from tests import equal_subtree


def test_clear_attributes():
    element = etree.Element('root', {'foo': 'bar'})
    lib.clear_attributes(element, None)
    assert element.attrib == {}


def test_concatenate():
    transformation = SimpleNamespace(_available_symbols={'foo': 'bar'})
    assert lib.concatenate('foo', Ref('foo'))(transformation) == 'foobar'


@mark.parametrize('side,expected',
                  (('left', '<r><x/><rs/></r>'),
                   ('right', '<r><ls/><x/></r>')))
def test_drop_siblings(side, expected):
    doc = etree.fromstring('<r><ls/><x/><rs/></r>')
    transformation = Transformation(
        Rule('x', lib.drop_siblings(side))
    )
    result = transformation(doc)
    assert equal_subtree(result, etree.fromstring(expected))


def test_has_tail():
    element = etree.Element('foo', )
    assert not lib.has_tail(element, None)
    element.tail = ''
    assert not lib.has_tail(element, None)
    element.tail = 'tail'
    assert lib.has_tail(element, None)


@mark.parametrize('tag,namespace_s,nsmap',
                  (('foo', 'http://bar.org', {}),
                   ('bar:foo', {'bar': 'http://bar.org'}, {}),
                   ('bar:foo', None, {'bar': 'http://bar.org'})))
def test_make_element(tag, namespace_s, nsmap):
    handler = lib.make_element(tag, namespace_s)
    assert etree.QName(handler(None, nsmap)).text == '{http://bar.org}foo'


def test_merge():
    source = etree.fromstring('<root><a><bb/></a><b/></root>')
    destination = etree.fromstring('<root><a><aa/></a><b/><c/></root>')
    expected = etree.fromstring('<root><a><aa/><bb/></a><b/><c/></root>')
    transformation = Transformation(lib.merge('source'), context={'source': source})
    equal_subtree(transformation(destination), expected)


def test_pop_attribute():
    element = etree.Element('x', {'y': 'z'})
    handler = lib.pop_attribute('y')
    result = handler(element)
    assert result == 'z'
    assert 'y' not in element.attrib


@mark.parametrize('keep_children,clear_ref', permutations((True, False)))
def test_remove_elements(keep_children, clear_ref):
    e = builder.ElementMaker()
    child = e.b()
    target = e.a(child)
    root = e.root(target)
    trash_bin = [target]
    transformation = SimpleNamespace(_available_symbols={'trashbin': trash_bin},
                                     states=SimpleNamespace(previous_result=None))
    lib.remove_elements('trashbin', keep_children, clear_ref)(transformation)

    assert not root.findall('a')
    assert keep_children == bool(root.findall('b'))
    assert clear_ref == (not bool(trash_bin))


@mark.parametrize('ns,expected', ((None, 'rosa'), ('spartakus', '{spartakus}rosa')))
def test_set_localname(ns, expected):
    if ns:
        kwargs = {'namespace': ns, 'nsmap': {None: ns}}
    else:
        kwargs = {}
    element = builder.ElementMaker(**kwargs).karl()

    lib.set_localname('rosa')(element, None)
    assert etree.QName(element).text == expected


def test_strip_attributes():
    element = etree.Element('root', {'a': 'a', 'b': 'b'})
    lib.strip_attributes('b')(element, None)
    assert element.attrib == {'a': 'a'}


def test_strip_namespace():
    namespace = 'http://www.example.org/ns/'
    e = builder.ElementMaker(namespace=namespace, nsmap={'x': namespace})
    root = e.div()
    t = Transformation(
        Rule(namespace, lib.strip_namespace)
    )
    result = t(root)
    assert result.tag == 'div'
