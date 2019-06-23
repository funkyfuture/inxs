from itertools import product
from types import SimpleNamespace

from delb import Document, new_tag_node, register_namespace
from pytest import mark, raises

from inxs import lib, Ref, Rule, Transformation


def test_add_html_classes():
    doc = Document('<html><body/></html>')

    transformation = Transformation(
        Rule('body', lib.add_html_classes('transformed')),
    )
    result = transformation(doc).root
    assert result[0].attributes['class'] == 'transformed'

    doc = Document('<html><body class="loaded" /></html>')
    result = transformation(doc).root
    assert all(x in result[0].attributes['class'] for x in
               ('transformed', 'loaded'))

    transformation = Transformation(
        Rule('body', lib.add_html_classes('transformed', 'and_something_else')),
    )
    result = transformation(doc).root
    assert all(x in result[0].attributes['class'] for x in
               ('and_something_else', 'loaded', 'transformed'))

    transformation = Transformation(
        Rule('body', lib.add_html_classes(Ref('html_classes'))),
        context={'html_classes': ['transformed', 'and_something_else']}
    )
    result = transformation(doc).root
    assert all(x in result[0].attributes['class'] for x in
               ('and_something_else', 'loaded', 'transformed'))


def test_clear_attributes():
    element = new_tag_node('root', attributes={'foo': 'bar'})
    lib.clear_attributes(element, None)
    assert element.attributes == {}


def test_concatenate():
    transformation = SimpleNamespace(_available_symbols={'foo': 'bar'})
    assert lib.concatenate('foo', Ref('foo'))(transformation) == 'foobar'


def test_get_variable():
    assert lib.get_variable('foo')(SimpleNamespace(foo='bar')) == 'bar'


def test_has_matching_text():
    node = Document('<song>Desmond Dekker  -  Shanty Town</song>').root

    assert lib.has_matching_text('.*  -  .*')(node, None)
    assert not lib.has_matching_text('.*007.*')(node, None)


def test_insert_fa_icon():
    document = Document("<root><a/></root>")
    handler = lib.insert_fontawesome_icon("arrow-left", "after", spin=True)
    handler(document.root[0])

    assert str(document) == '<root><a/><i class="fas fa-arrow-left fa-spin"/></root>'


def test_join_to_string():
    transformation = SimpleNamespace(
        _available_symbols={'previous_result': ['la', 'la', 'la']}
    )
    assert lib.join_to_string(' ')(transformation) == 'la la la'


def test_make_element():
    root = new_tag_node("root")
    handler = lib.make_node(local_name='foo', namespace='http://bar.org')
    transformation = SimpleNamespace(states=SimpleNamespace(root=root))
    assert handler(root, transformation).qualified_name == '{http://bar.org}foo'


def test_pop_attribute():
    node = new_tag_node('x', attributes={'y': 'z'})
    handler = lib.pop_attribute('y')
    result = handler(node)
    assert result == 'z'
    assert 'y' not in node.attributes


def test_pop_attributes():
    node = new_tag_node('x', attributes={'x': '0', 'y': '1'})
    assert lib.pop_attributes('x', 'y')(node) == {'x': '0', 'y': '1'}

    node = new_tag_node('x', attributes={'x': '0'})
    assert lib.pop_attributes('x', 'y', ignore_missing=True)(node) == {'x': '0'}

    node = new_tag_node('x', {'x': '0'})
    with raises(KeyError):
        lib.pop_attributes('x', 'y')(node)


@mark.parametrize('keep_children,preserve_text,clear_ref',
                  tuple(product((True, False), repeat=3)))
def test_remove_elements(keep_children, preserve_text, clear_ref):
    root = Document("<root><a>foo<b/></a></root>").root
    trash_bin = [root.first_child]

    transformation = SimpleNamespace(_available_symbols={'trashbin': trash_bin},
                                     states=SimpleNamespace(previous_result=None))
    lib.remove_nodes('trashbin', keep_children=keep_children,
                     preserve_text=preserve_text,
                     clear_ref=clear_ref)(transformation)

    assert not root.css_select('a')
    assert keep_children == bool(root.css_select('b'))
    assert preserve_text == (root.full_text == "foo")
    assert clear_ref == (not bool(trash_bin)), (clear_ref, trash_bin)


def test_rename_attributes():
    element = new_tag_node('x', attributes={'x': '0', 'y': '1'})
    lib.rename_attributes({'x': 'a', 'y': 'b'})(element)
    assert element.attributes == {'a': '0', 'b': '1'}


def test_set_attribute():
    element = new_tag_node('x')
    lib.set_attribute('y', 'z')(element, None)
    assert element.attributes == {'y': 'z'}


def test_set_text():
    node = new_tag_node("pre")
    transformation = Transformation(
        lib.put_variable('x', 'Hello world.'),
        Rule('/', lib.set_text(Ref('x')))
    )
    assert str(transformation(node)) == '<pre>Hello world.</pre>'


@mark.parametrize('namespace,expected',
                  ((None, 'rosa'), ('spartakus', '{spartakus}rosa'))
                  )
def test_set_localname(namespace, expected):
    node = new_tag_node('karl', namespace=namespace)

    lib.set_localname('rosa')(node, None)
    assert node.qualified_name == expected


def test_strip_attributes():
    element = new_tag_node('root', attributes={'a': 'a', 'b': 'b'})
    lib.remove_attributes('b')(element, None)
    assert element.attributes == {'a': 'a'}


def test_strip_namespace():
    namespace = 'http://www.example.org/ns/'
    register_namespace("x", namespace)
    root = new_tag_node("div", namespace=namespace)

    transformation = Transformation(
        Rule(namespace, lib.remove_namespace)
    )
    result = transformation(root)
    assert result.qualified_name == 'div'
