"""
This module contains common functions that can be used for either :class:`~inxs.Rule`
s' tests, as handler functions or simple transformation steps.

Community contributions are highly appreciated, but it's hard to layout hard criteria
for what belongs here and what not. In doubt open a pull request with your proposal
as far as it proved functional to you, it doesn't need to be polished at that point.
"""

# TODO indicate use area in function's docstrings; and whether they return something
# TODO delete unneeded symbols in setup functions' locals


import logging
import re
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from delb import (
    TagNode,
    TextNode,
    is_tag_node,
    altered_default_filters,
    is_text_node,
    tag,
)

from inxs import dot_lookup, Ref, singleton_handler, Transformation
from inxs.utils import is_Ref, resolve_Ref_values_in_mapping

# helpers


logger = logging.getLogger(__name__)
dbg = logger.debug
nfo = logger.info

__all__ = []


def export(func):
    __all__.append(func.__name__)
    return func


# the actual lib


@export
@singleton_handler
def add_html_classes(*classes, target=Ref("node")):
    """ Adds the string tokens passed as positional arguments to the
        ``classes`` attribute of a node specified by ``target``.
        An argument can also be a sequence of strings or a :func:`~inxs.Ref` that
        yields on of the two.
        Per default that is a :func:`~inxs.Ref` to the matching node of a rule.
    """

    def add_items(_set, value):
        if isinstance(value, str):
            _set.add(value)
        elif isinstance(value, Sequence):
            _set.update(value)
        else:
            raise RuntimeError

    def processor(transformation):
        if not classes:
            return

        # TODO input type specialized handlers
        _classes = set()
        for cls in classes:
            if not cls:
                continue
            if is_Ref(cls):
                add_items(_classes, cls(transformation))
            else:
                add_items(_classes, cls)

        node = target(transformation)
        value = node.attributes.get("class", "").strip()
        _classes.update(x.strip() for x in value.split() if x)
        node.attributes["class"] = " ".join(sorted(_classes))

    return processor


@export
@singleton_handler
def append(name, symbol=Ref("previous_result"), copy_node=False):
    """ Appends the object referenced by ``symbol`` (default: the result of the previous
        :term:`handler function`) to the object available as ``name`` in the
        :attr:`Transformation._available_symbols`. If the object is a
        :class:`delb.TagNode` instance and ``copy_node`` is ``True``, a copy
        that includes all descendant nodes is appended to the target.
    """

    def handler(previous_result, transformation):
        obj = symbol(transformation)
        if isinstance(obj, TagNode) and copy_node:
            obj = obj.clone(deep=True)

        if "." in name:
            namespace, path = name.split(".", maxsplit=1)
            target = transformation._available_symbols[namespace]
            target = dot_lookup(target, path)
        else:
            target = transformation._available_symbols[name]

        if isinstance(target, TagNode):
            target.append_child(obj)
        else:
            target.append(obj)

        return previous_result

    return handler


@export
def cleanup_namespaces(root: TagNode, previous_result: Any) -> Any:
    """ Cleanup the namespaces of the tree. This should always be used at the
        end of a transformation when nodes' namespaces have been changed. """
    root.document.cleanup_namespaces()
    return previous_result


@export
def clear_attributes(node: TagNode, previous_result: Any) -> Any:
    """ Deletes all attributes of an node. """
    node.attributes.clear()
    return previous_result


@export
@singleton_handler
def concatenate(*parts):
    """ Concatenate the given parts which may be lists or strings as well as callables
        returning such. """

    def handler(transformation) -> str:
        result = ""
        for part in parts:
            if callable(part):
                _part = part(transformation)
            elif isinstance(part, (str, List)):
                _part = part
            else:
                raise RuntimeError(f"Unhandled type: {type(part)}")
            result += _part
        return result

    return handler


@export
@singleton_handler
def debug_dump_document(name="tree"):
    """ Dumps all contents of the node referenced by ``name`` from the
        :attr:`inxs.Transformation._available_symbols` to the log at info level. """

    def handler(transformation):
        node = transformation._available_symbols.get(name)
        if node is None:
            nfo(f"No symbol named '{name}' found.")
        elif not isinstance(node, TagNode):
            nfo(f"Symbol '{name}' is not a TagNode.")
        else:
            nfo(str(node))
        return transformation.states.previous_result

    return handler


@export
@singleton_handler
def debug_message(msg):
    """ Logs the provided message at info level. """

    def handler(previous_result):
        nfo(msg)
        return previous_result

    return handler


@export
@singleton_handler
def debug_symbols(*names):
    """ Logs the representation strings of the objects referenced by ``names`` in
        :attr:`inxs.Transformation._available_symbols` at info level. """

    def handler(transformation):
        for name in names:
            nfo(f"symbol {name}: {transformation._available_symbols[name]!r}")
        return transformation.states.previous_result

    return handler


@export
def f(func, *args, **kwargs):
    """ Wraps the callable ``func`` which will be called as ``func(*args, **kwargs)``,
        the function and any argument can be given as :func:`inxs.Ref`. """

    def wrapper(transformation):
        if is_Ref(func):
            _func = func(transformation)
        else:
            _func = func
        _args = ()
        for arg in args:
            if is_Ref(arg):
                _args += (arg(transformation),)
            else:
                _args += (arg,)

        _kwargs = resolve_Ref_values_in_mapping(kwargs, transformation)

        return _func(*_args, **_kwargs)

    return wrapper


@export
@singleton_handler
def get_attribute(name):
    """ Gets the value of the node's attribute named ``name``. """

    def evaluator(node: TagNode):
        return node.attributes.get(name)

    return evaluator


@export
def get_localname(node):
    """ Gets the node's local tag name. """
    return node.local_name


@export
def get_text(node: TagNode):
    """ Returns the content of the matched node's descendants of :class:`delb.TextNode`
        type.
    """
    return node.full_text


@export
@singleton_handler
def get_variable(name):
    """ Gets the object referenced as ``name`` from the :term:`context`. It is then
        available as symbol ``previous_result``. """

    def handler(context):
        return dot_lookup(context, name)

    return handler


@export
def has_attributes(node: TagNode, _):
    """ Returns ``True`` if the node has attributes. """
    return bool(node.attributes)


@export
def has_children(node: TagNode, _):
    """ Returns ``True`` if the node has descendants. """
    return node.first_child is not None


@export
@singleton_handler
def has_matching_text(pattern: str):
    """ Returns ``True`` if the text contained by the node and its descendants has a
        matches the provided ``pattern``. """
    pattern = re.compile(pattern)

    def evaluator(node: TagNode, _):
        return pattern.match(node.full_text)

    return evaluator


@export
def has_text(node: TagNode, _):
    """ Returns ``True`` if the node has any :class:`delb.TextNode`. """
    with altered_default_filters(is_text_node):
        for _ in node.child_nodes(recurse=True):
            return True
    return False


@export
@singleton_handler
def insert_fontawesome_icon(name: str, position: str, spin: bool = False):
    """ Inserts the html markup for an icon from the fontawesome set with the given
        ``name`` at ``position`` of which only ``after`` is implemented atm.

        It employs semantics for Font Awesome 5. """

    def after_handler(node: TagNode):
        classes = f"fas fa-{name}"
        if spin:
            classes += " fa-spin"
        node.add_next(tag("i", {"class": classes}))

    return {"after": after_handler}[position]


@export
@singleton_handler
def join_to_string(separator: str = " ", symbol="previous_result"):
    """ Joins the object referenced by ``symbol`` around the given
        ``separator`` and returns it. """

    def handler(transformation):
        return separator.join(transformation._available_symbols[symbol])

    return handler


@export
def lowercase(previous_result):
    """ Processes ``previous_result`` to be all lower case. """
    return previous_result.lower()


@export
def make_node(**node_args):
    """ Creates a new tag node in the root node's context, takes the arguments of
        :meth:`delb.TagNode.new_tag_node` that must be provided as keyword arguments.
        The node is then available as symbol ``previous_result``.
    """

    def handler(root, transformation):
        _node_args = resolve_Ref_values_in_mapping(node_args, transformation)
        return root.new_tag_node(**_node_args)

    return handler


@export
@singleton_handler
def pop_attribute(name: str):
    """ Pops the node's attribute named ``name``. """

    def handler(node: TagNode) -> str:
        return node.attributes.pop(name)

    return handler


@export
@singleton_handler
def pop_attributes(*names: str, ignore_missing=False):
    """ Pops all attributes with name from ``names`` and returns a mapping with names
        and values. When ``ignore_missing`` is ``True`` ``KeyError`` exceptions pass
        silently. """
    handlers = {x: pop_attribute(x) for x in names}
    del names

    def handler(node: TagNode) -> Dict[str, str]:
        result = {}
        for name, _handler in handlers.items():
            try:
                result[name] = _handler(node)
            except KeyError:
                if not ignore_missing:
                    raise
        return result

    return handler


@export
def prefix_attributes(prefix: str, *attributes: str):
    """ Prefixes the ``attributes`` with ``prefix``. """
    return rename_attributes({x: prefix + x for x in attributes})


@export
@singleton_handler
def put_variable(name, value=Ref("previous_result")):
    """ Puts ``value``as ``name`` to the :term:`context` namespace, by default the
        value is determined by a :func:`inxs.Ref` to ``previous_result``. """

    def ref_handler(transformation):
        setattr(transformation.context, name, value(transformation))
        return transformation.states.previous_result

    def ref_handler_dot_lookup(transformation):
        setattr(dot_lookup(transformation.context, name), value(transformation))
        return transformation.states.previous_result

    def simple_handler(transformation):
        setattr(transformation.context, name, value)
        return transformation.states.previous_result

    def simple_handler_dot_lookup(transformation):
        setattr(dot_lookup(transformation.context, name), value)
        return transformation.states.previous_result

    if is_Ref(value):
        if "." in name:
            return ref_handler_dot_lookup
        return ref_handler
    elif "." in name:
        return simple_handler_dot_lookup
    else:
        return simple_handler


@export
@singleton_handler
def remove_attributes(*names):
    """ Removes all attributes with the keys provided as ``names`` from the node. """

    def handler(node: TagNode, previous_result: Any) -> Any:
        for name in names:
            node.attributes.pop(name, None)
        return previous_result

    return handler


@export
def remove_namespace(node: TagNode, previous_result):
    """ Removes the namespace from the node.
        When used, :func:`cleanup_namespaces` should be applied at the end of the
        transformation. """
    node.namespace = None
    return previous_result


@export
def remove_node(node: TagNode):
    """ A very simple handler that just removes a node and its descendants from a
        tree. """
    node.detach()


@export
@singleton_handler
def remove_nodes(references, keep_children=False, preserve_text=False, clear_ref=True):
    """ Removes all nodes from their tree that are referenced in a list that is
        available as ``references``. The nodes' children are retained when
        ``keep_children`` is passed as ``True``, or only the contained text when
        ``preserve_text`` is passed as ``True``. The reference list is cleared
        afterwards if ``clear_ref`` is ``True``.
    """

    def handler(transformation):
        nodes = transformation._available_symbols[references]

        for node in nodes:

            if not keep_children:
                # retain descendants' text
                for child in tuple(node.child_nodes(is_tag_node)):
                    if preserve_text:
                        child.replace_with(child.full_text)
                    else:  # or just be quick at removal
                        child.detach()
            node.merge_text_nodes()

            if preserve_text:
                filters = ()
            else:
                filters = (is_tag_node,)

            # move remaining child nodes after the target
            children = tuple(node.child_nodes(*filters))
            if children:
                for child in children:
                    child.detach()
                node.add_next(*children)

            # remove the target
            node.detach()

        if clear_ref:
            nodes.clear()
        return transformation.states.previous_result

    return handler


@singleton_handler
def _rename_attributes(translation_map: Tuple[Tuple[str, str], ...]) -> Callable:
    def handler(node: TagNode) -> None:
        for _from, to in translation_map:
            node.attributes[to] = node.attributes.pop(_from)

    return handler


@export
def rename_attributes(translation_map: Mapping[str, str]) -> Callable:
    """ Renames the attributes of a node according to the provided
        ``translation_map`` that consists of old name keys and new name values.
    """
    return _rename_attributes(tuple((k, v) for k, v in translation_map.items()))


# FIXME test this
@export
@singleton_handler
def resolve_xpath_to_node(*names):
    """ Resolves the objects from the context namespace (which are supposed to be XPath
        expressions) referenced by ``names`` with the *one* node that the expression
        matches or ``None``. This is useful when a copied tree is processed and
        'XPath pointers' are passed to the :term:`context` when a
        :class:`inxs.Transformation` is called.
    """

    def resolver(context, transformation):
        for name in names:
            expression = getattr(context, name)
            if not expression:
                setattr(context, name, None)
                continue
            resolved_nodes = transformation.root.xpath(expression)
            if not resolved_nodes:
                setattr(context, name, None)
            elif len(resolved_nodes) == 1:
                setattr(context, name, resolved_nodes[0])
            else:
                raise RuntimeError(f"More than one node matched {expression}")
        return transformation.states.previous_result

    return resolver


@export
@singleton_handler
def set_attribute(name, value=Ref("previous_result")):
    """ Sets an attribute ``name`` with ``value``. """

    def simple_handler(node: TagNode, previous_result: Any) -> Any:
        node.attributes[name] = value
        return previous_result

    def resolving_handler(
        node: TagNode, previous_result: Any, transformation: Transformation
    ) -> Any:
        node.attributes[name] = value(transformation)
        return previous_result

    if isinstance(value, str):
        return simple_handler
    elif is_Ref(value):
        return resolving_handler


@export
@singleton_handler
def set_localname(name):
    """ Sets the node's localname to ``name``. """

    def handler(node: TagNode, previous_result: Any):
        node.local_name = name
        return previous_result

    return handler


@export
@singleton_handler
def set_text(text=Ref("previous_result")):
    """ Sets the nodes's first child node that is of :class:`delb.TextNode` type to the
        one provided as ``text``, it can also be a :func:`inxs.Ref`.
        If the first node isn't a text node, one will be inserted. """

    def ref_handler(node: TagNode, transformation: Transformation):
        _text = text(transformation)
        target = node.first_child
        if target is None or not isinstance(node, TextNode):
            node.insert_child(0, _text)
        else:
            target.content = _text
        return transformation.states.previous_result

    def static_handler(node: TagNode, previous_result):
        target = node.first_child
        if target is None or not isinstance(node, TextNode):
            node.insert_child(0, text)
        else:
            target.content = text
        return previous_result

    return ref_handler if is_Ref(text) else static_handler


@export
@singleton_handler
def sort(name: str = "previous_result", key: Callable = lambda x: x):
    """ Sorts the object referenced by ``name`` in the :term:`context` using ``key`` as
        :term:`key function`. """

    def handler(context):
        return sorted(getattr(context, name), key=key)

    return handler


@export
@singleton_handler
def text_equals(text):
    """ Tests whether the evaluated node's text contained by its descendants is equal to
        ``text``.
    """

    def evaluator(node: TagNode, _):
        return node.full_text == text

    return evaluator
