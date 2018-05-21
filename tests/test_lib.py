from itertools import product
from types import SimpleNamespace

from lxml import builder, etree
from pytest import mark, raises

from inxs import lib, Ref, Rule, Transformation
from tests import equal_subtree


def test_add_html_classes():
    doc = etree.fromstring('<html><body/></html>')

    transformation = Transformation(
        Rule('body', lib.add_html_classes('transformed')),
    )
    result = transformation(doc)
    assert result.find('body').attrib['class'] == 'transformed'

    doc = etree.fromstring('<html><body class="loaded" /></html>')
    result = transformation(doc)
    assert all(x in result.find('body').attrib['class'] for x in
               ('transformed', 'loaded'))

    transformation = Transformation(
        Rule('body', lib.add_html_classes('transformed', 'and_something_else')),
    )
    result = transformation(doc)
    assert all(x in result.find('body').attrib['class'] for x in
               ('and_something_else', 'loaded', 'transformed'))


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


def test_extract_text():
    element = etree.fromstring('<tune>Desmond Dekker  -  Shanty Town</tune>')
    assert lib.extract_text()(element) == 'Desmond Dekker - Shanty Town'


def test_get_variable():
    assert lib.get_variable('foo')(SimpleNamespace(foo='bar')) == 'bar'


def test_has_matching_text():
    element = etree.fromstring('<song>Desmond Dekker  -  Shanty Town</song>')

    assert lib.has_matching_text('.*  -  .*')(element, None)
    assert not lib.has_matching_text('.*007.*')(element, None)


def test_has_tail():
    element = etree.Element('foo', )
    assert not lib.has_tail(element, None)
    element.tail = ''
    assert not lib.has_tail(element, None)
    element.tail = 'tail'
    assert lib.has_tail(element, None)


def test_join_to_string():
    transformation = SimpleNamespace(
        _available_symbols={'previous_result': ['la', 'la', 'la']}
    )
    assert lib.join_to_string(' ')(transformation) == 'la la la'


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


def test_pop_attributes():
    element = etree.Element('x', {'x': '0', 'y': '1'})
    assert lib.pop_attributes('x', 'y')(element) == {'x': '0', 'y': '1'}

    element = etree.Element('x', {'x': '0'})
    assert lib.pop_attributes('x', 'y', ignore_missing=True)(element) == {'x': '0'}

    element = etree.Element('x', {'x': '0'})
    with raises(KeyError):
        lib.pop_attributes('x', 'y')(element)


@mark.parametrize('keep_children,preserve_text,clear_ref',
                  tuple(product((True, False), repeat=3)))
def test_remove_elements(keep_children, preserve_text, clear_ref):
    e = builder.ElementMaker()
    target = e.a('foo', e.b())
    root = e.root(target)
    trash_bin = [target]
    transformation = SimpleNamespace(_available_symbols={'trashbin': trash_bin},
                                     states=SimpleNamespace(previous_result=None))
    lib.remove_elements('trashbin', keep_children=keep_children,
                        preserve_text=preserve_text,
                        preserve_tail=True, clear_ref=clear_ref)(transformation)

    assert not root.findall('a')
    assert keep_children == bool(root.findall('b'))
    assert preserve_text == isinstance(root.text, str)
    assert clear_ref == (not bool(trash_bin)), (clear_ref, trash_bin)


def test_rename_attributes():
    element = etree.Element('x', {'x': '0', 'y': '1'})
    lib.rename_attributes({'x': 'a', 'y': 'b'})(element)
    assert element.attrib == {'a': '0', 'b': '1'}


def test_replace_text():
    element = etree.Element('x')
    element.text, element.tail = ('foo', 'bar')
    transformation = Transformation()
    transformation.states = SimpleNamespace(previous_result=0)
    lib.replace_text('foo', 'peng')(element, transformation)
    lib.replace_text('bar', 'zack', tail=True)(element, transformation)
    assert etree.tounicode(element) == '<x>peng</x>zack'


def test_set_attribute():
    element = etree.Element('x')
    lib.set_attribute('y', 'z')(element, None)
    assert element.attrib == {'y': 'z'}


def test_set_text():
    element = etree.Element('pre')
    transformation = Transformation(
        lib.put_variable('x', 'Hello world.'),
        Rule('/', lib.set_text(Ref('x')))
    )
    assert etree.tounicode(transformation(element)) == '<pre>Hello world.</pre>'


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
