# TODO annotate Callable types with signature and return values
# https://docs.python.org/3.6/library/typing.html?highlight=namedtuple#callable
# TODO delete unneeded symbols in setup functions' locals

import logging
import pkg_resources
from collections import ChainMap
from copy import deepcopy
from functools import lru_cache
from os import getenv
from types import SimpleNamespace
from typing import (
    AnyStr, Callable, Dict, Iterator, List, Mapping, Pattern, Sequence, Union,
)
from typing import Any as AnyType

import cssselect
import dependency_injection
from delb import is_tag_node, TagNode, Document

from inxs.constants import (
    REF_IDENTIFYING_ATTRIBUTE,
    TRAVERSE_BOTTOM_TO_TOP,
    TRAVERSE_DEPTH_FIRST,
    TRAVERSE_LEFT_TO_RIGHT,
    TRAVERSE_RIGHT_TO_LEFT,
    TRAVERSE_ROOT_ONLY,
    TRAVERSE_TOP_TO_BOTTOM,
    TRAVERSE_WIDTH_FIRST,
)


# config


__version__ = pkg_resources.get_distribution('inxs').version

HANDLER_CACHES_SIZE = getenv('INXS_HANDLER_CACHE_SIZE', None)
if HANDLER_CACHES_SIZE is not None:
    HANDLER_CACHES_SIZE = int(HANDLER_CACHES_SIZE)


# logging


logger = logging.getLogger(__name__)
""" Module logger, configure as you need. """
dbg = logger.debug
nfo = logger.info


# exceptions


class InxsException(Exception):
    """ Base class for inxs exceptions. """


class FlowControl(InxsException):
    """ Base class for exception that control the evaluation of handlers. """

    def __init__(self):
        super().__init__()
        dbg(f'{self.__class__.__name__} is evoked.')


class AbortRule(FlowControl):
    """ Can be raised to abort the evaluation of all the currently processed
        :class:`inxs.Rule` 's remaining tests and handlers. No further nodes will
        be considered for that rule. This is similar to Python's builtin ``break`` in
        iterations. """


class AbortTransformation(FlowControl):
    """ Can be raised to cancel the remaining :term:`transformation steps`. """


class SkipToNextNode(FlowControl):
    """ Can be raised to abort handling of the current node. This is similar to
        Python's builtin ``continue`` in iterations.
    """


# types

AttributesConditionType = Union[
    Dict[Union[str, Pattern], Union[str, Pattern, None]], Callable]
ConditionType = Union[Callable, AnyStr, AttributesConditionType]
StepType = Union['Rule', Callable, Sequence['StepType']]


# helpers

def _condition_factory(condition: ConditionType) -> Callable:
    """ Generates test functions for conditions provided as string or mapping. """
    if isinstance(condition, str):
        if condition == '/':
            return _is_root_condition
        elif condition == '*':
            return _is_any_node_condition
        elif '://' in condition:
            # assumes URI
            dbg(f'Adding {condition} as namespace condition.')
            return HasNamespace(condition)
        elif condition.isalpha():
            # assumes tag
            dbg(f"Adding {condition} as tag's local name condition.")
            return HasLocalname(condition)
        try:  # it may be a css selctor
            _condition = _css_selector_translator(condition)
        except cssselect.SelectorError:
            pass
        else:
            dbg(
                f'Translated css selector {condition}` to XPath expression '
                f'{_condition}.'
            )
            condition = _condition
        # assumes XPath
        dbg(f'Adding {condition} as XPath condition.')
        return MatchesXPath(condition)
    elif isinstance(condition, Mapping):
        dbg(f'Adding {condition} as attribute condition.')
        return MatchesAttributes(condition)
    else:
        return condition


class _CSSToXPathTranslator(cssselect.GenericTranslator):
    def selector_to_xpath(self, *args, **kwargs):
        result = super().selector_to_xpath(*args, **kwargs)
        if result.startswith('descendant-or-self::'):
            # though this should be equivalent, the abbreviated form proved
            # to work in cases where the full wouldn't
            result = result.replace('descendant-or-self::', '//', 1)
        return result


_css_selector_translator = _CSSToXPathTranslator().css_to_xpath


def dot_lookup(obj: AnyType, name: str):
    """ Looks up the attribute ``name`` from ``obj`` considering nested attributes
        that are separated by a ``.`` """
    for _name in name.split('.'):
        obj = getattr(obj, _name)
    return obj


def _flatten_sequence(seq: Sequence):
    result: List = []
    for item in seq:
        if isinstance(item, Sequence) and not isinstance(item, str):
            result.extend(_flatten_sequence(item))
        else:
            result.append(item)
    return tuple(result)


def _is_any_node_condition(_, __):
    return True


def _is_flow_control(obj: AnyType) -> bool:
    try:
        return issubclass(obj, FlowControl)
    except TypeError:
        return False


def _is_root_condition(node: TagNode, transformation: 'Transformation'):
    return node.parent is None


singleton_handler = lru_cache(HANDLER_CACHES_SIZE)


# traverser


def traverse_df_ltr_btt(root: TagNode) -> Iterator[TagNode]:
    def yield_children(node):
        for child in tuple(node.child_nodes(is_tag_node)):
            yield from yield_children(child)
        yield node

    yield from yield_children(root)


def traverse_df_ltr_ttb(root: TagNode) -> Iterator[TagNode]:
    yield root
    yield from root.child_nodes(is_tag_node, recurse=True)


def traverse_root(root: TagNode) -> Iterator[TagNode]:
    yield root


# rules definition


def Any(*conditions: Sequence[ConditionType]) -> Callable:
    """ Returns a callable that evaluates the provided test functions and returns
        ``True`` if any of them returned that.
    """
    conditions = tuple(_condition_factory(x) for x in _flatten_sequence(conditions))

    def evaluator(node: TagNode, transformation: Transformation) -> bool:
        return any(x(node, transformation) for x in conditions)

    return evaluator


def OneOf(*conditions: Sequence[ConditionType]) -> Callable:
    """ Returns a callable that evaluates the provided test functions and returns
        ``True`` if exactly one of them returned that. """
    conditions = tuple(_condition_factory(x) for x in _flatten_sequence(conditions))

    def evaluator(node: TagNode, transformation: Transformation) -> bool:
        return [x(node, transformation) for x in conditions].count(True) == 1

    return evaluator


def Not(*conditions: Sequence[ConditionType]) -> Callable:
    """ Returns a callable that evaluates the provided test functions and returns
        ``True`` if any of them returned ``False``.
    """
    conditions = tuple(_condition_factory(x) for x in _flatten_sequence(conditions))

    def evaluator(node: TagNode, transformation: Transformation) -> bool:
        return not any(x(node, transformation) for x in conditions)

    return evaluator


@singleton_handler
def HasNamespace(namespace: AnyStr) -> Callable:
    """ Returns a callable that tests an node for the given tag namespace. """

    def evaluator(node: TagNode, _) -> bool:
        return node.namespace == namespace

    return evaluator


@singleton_handler
def HasLocalname(name: AnyStr) -> Callable:
    """ Returns a callable that tests an node for the given local tag name. """

    def evaluator(node: TagNode, _) -> bool:
        return node.local_name == name

    return evaluator


@singleton_handler
def MatchesXPath(xpath: Union[str, Callable]) -> Callable:
    """ Returns a callable that tests an node for the given XPath expression (whether
        the evaluation result on the :term:`transformation root` contains it).
        If the ``xpath`` argument is a callable, it will be called with the current
        transformation as argument to obtain the expression. """

    def callable_evaluator(node: TagNode,
                           transformation: Transformation) -> bool:
        _xpath = xpath(transformation)
        dbg(f"Resolved XPath from callable: '{_xpath}'")
        return node in transformation.root.xpath(_xpath)

    def string_evaluator(node: TagNode,
                         transformation: Transformation) -> bool:
        return node in transformation.root.xpath(xpath)

    return callable_evaluator if callable(xpath) else string_evaluator


def MatchesAttributes(constraints: AttributesConditionType) -> Callable:
    """ Returns a callable that tests an node's attributes for constrains defined
        in a :term:`mapping`.
        All constraints must be matched to resolve as true. Expected keys and values
        can be provided as string or compiled regular expression object from the
        :mod:`re` module.
        A ``None`` as value constraint evaluates as true if the key is in the
        attributes regardless its value. It also implies that at least one attribute
        must match the key's constraint if this one is a regular expression object.
        Alternatively a callable can be passed that returns such mappings during the
        transformation. """

    def callable_evaluator(node: TagNode, transformation: Transformation):
        _constraints = constraints(transformation)
        dbg(
            f"Resolved attributes' constraints from callable: '{_constraints}'"
        )
        return MatchesAttributes(_constraints)(node, transformation)

    if callable(constraints):
        return callable_evaluator

    key_only_constraints = [k for k, v in constraints.items() if v is None]
    key_string_constraints = {k: v for k, v in constraints.items()
                              if isinstance(k, str) and v is not None}
    key_re_constraints = {k: v for k, v in constraints.items()
                          if isinstance(k, Pattern) and v is not None}

    def evaluator(node: TagNode, _) -> bool:
        attributes = node.attributes

        if constraints and not attributes:
            return False

        # check the presence of keys
        for key_constraint in key_only_constraints:
            if isinstance(key_constraint, str) and key_constraint not in attributes:
                return False
            elif isinstance(key_constraint, Pattern) and \
                    not any(key_constraint.match(key) for key in attributes.keys()):
                return False

        value_string_constraints, value_re_constraints = {}, {}

        # check attributes' keys with string constraints
        for key_constraint, value_constraint in key_string_constraints.items():
            if key_constraint not in attributes:
                return False
            if isinstance(value_constraint, str):
                value_string_constraints[key_constraint] = value_constraint
            elif isinstance(value_constraint, Pattern):
                value_re_constraints[key_constraint] = value_constraint

        # check attributes' keys with regular expression constraints
        for key_constraint, value_constraint in key_re_constraints.items():
            for attribute in (x for x in attributes if key_constraint.match(x)):
                if isinstance(value_constraint, str):
                    value_string_constraints[attribute] = value_constraint
                elif isinstance(value_constraint, Pattern):
                    value_re_constraints[attribute] = value_constraint

        # check attributes' values
        for key, constraint in value_string_constraints.items():
            if attributes[key] != constraint:
                return False
        for key, constraint in value_re_constraints.items():
            if not constraint.match(attributes[key]):
                return False

        return True

    return evaluator


@singleton_handler
def Ref(name: str) -> Callable:
    """ Returns a callable that can be used for value resolution in a condition test or
        :term:`handler function` that supports such. The value will be looked up
        during the processing of a transformation in
        :attr:`Transformation._available_symbols` by the given ``name``. This allows
        to reference dynamic values in :term:`transformation steps` and :class:`Rule` s.
    """

    def simple_resolver(transformation: Transformation) -> AnyType:
        dbg('Resolving {name}.')
        return transformation._available_symbols[name]

    setattr(simple_resolver, REF_IDENTIFYING_ATTRIBUTE, None)

    def dot_resolver(transformation: Transformation) -> AnyType:
        dbg(f'Resolving {name}.')
        token = name.split('.')
        obj = transformation._available_symbols[token[0]]
        for _name in token[1:]:
            obj = getattr(obj, _name)
        return obj

    setattr(dot_resolver, REF_IDENTIFYING_ATTRIBUTE, None)

    return dot_resolver if '.' in name else simple_resolver


def If(x: AnyType, operator: Callable, y: AnyType) -> Callable:
    """ Returns a callable that can be used as condition test in a :class:`Rule`.
        The arguments ``x`` and ``y`` can be given as callables that will be used to
        get the ``operator``'s input values during execution.
        Before you implement your own operators, mind that there are a lot available
        within Python's ``__builtins__`` and the standard library, in particular the
        :mod:`operator` module.

        Examples:

        >>> If(Ref('previous_result'), operator.is_not, None)  # doctest: +SKIP
    """

    # TODO allow single arguments
    # TODO? allow primitive expressions for stdlib.operator's members
    def evaluator(_, transformation: Transformation) -> AnyType:
        if callable(x):
            _x = x(**dependency_injection.resolve_dependencies(
                x, transformation._available_symbols).as_kwargs)
            dbg(f"x resolved to '{_x}'")
        else:
            _x = x
        if callable(y):
            _y = y(**dependency_injection.resolve_dependencies(
                y, transformation._available_symbols).as_kwargs)
            dbg(f"y resolved to '{_y}'")
        else:
            _y = y
        return operator(_x, _y)

    return evaluator


class Rule:
    """ Instances of this class can be used as conditional :term:`transformation
        steps` that are evaluated against all traversed nodes.

        :param conditions: All given conditions must evaluate as ``True`` in order
                           for this rule to be applied.
                           Strings and mappings can be provided as shortcuts, see
                           :ref:`rule_condition_shortcuts` for details.
                           The condition test functions are always called with the
                           currently evaluated ``node`` and the :class:`Transformation`
                           instance as arguments.
                           There are helper functions for grouping conditions logically:
                           :func:`Any`, :func:`Not` and :func:`OneOf`.
        :type conditions: A single callable, string or mapping, or a :term:`sequence`
                          of such.
        :param handlers: These handlers will be called if the conditions matched.
                         They can take any argument whose name is available in
                         :attr:`Transformation._available_symbols`.
        :type handlers: A single callable or a :term:`sequence` of such.
        :param name: The optional rule's name.
        :type name: String.
        :param traversal_order: An optional traversal order that overrides the
                                transformation's default
                                :attr:`Transformation.config.traversal_order`, see
                                :ref:`traversal_strategies` for details.
        :type traversal_order: Integer.
    """
    __slots__ = ('name', 'conditions', 'handlers', 'traversal_order')

    def __init__(self, conditions: Union[ConditionType, Sequence[ConditionType]],
                 handlers: Union[Callable, Sequence[Callable]],
                 name: str = None, traversal_order: int = None) -> None:

        self.name: str = name
        dbg(f"Initializing rule '{name}'.")

        if not isinstance(conditions, Sequence) or isinstance(conditions, str):
            conditions = (conditions,)
        conditions = _flatten_sequence(conditions)
        self.conditions = tuple(_condition_factory(x) for x in conditions)
        if _is_root_condition in self.conditions:
            traversal_order = TRAVERSE_ROOT_ONLY
            self.conditions = tuple(
                x for x in self.conditions if x is not _is_root_condition)

        if not isinstance(handlers, Sequence):
            handlers = (handlers,)
        self.handlers = _flatten_sequence(handlers)
        self.traversal_order = traversal_order


class Once(Rule):
    """ This is a variant of :class:`Rule` that is only applied on the first match. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handlers += (AbortRule,)


# transformation


class Transformation:
    """ A transformation instance is defined by its :term:`transformation steps` and
        :term:`configuration`. It is to be called with a :class:`delb.Document` or
        :class:`delb.TagNode` instance as :term:`transformation root`, only this node
        (or the root node of a ``Document``) and its children will be considered during
        traversal.

        :param steps: The designated transformation steps of the instance are given
                      as a sequence of positional arguments.
        :param config: The configuration values for the instance are passed as keyword
                       arguments.
                       Beside the following keywords, it can be populated with any
                       key-value-pairs that will be available in
                       :attr:`inxs.Transformation._available_symbols` during a
                       transformation.
                       The defaults are defined in :attr:`~inxs.config_defaults`.

                       - ``context`` can be provided as mapping with items that are
                         added to the :term:`context` before a (sub-)document is
                         processed.
                       - ``common_rule_conditions`` can be used to define one or more
                         conditions that must match in all rule evaluations. E.g. a
                         transformation could be restricted to nodes with a
                         certain namespace without redundantly defining that per rule.
                         Can be given as a single object (e.g. a string) or as sequence.
                       - ``copy`` is a boolean that defaults to ``True`` and indicates
                         whether to process on a copy of the document's tree object.
                       - ``name`` can be used to identify a transformation.
                       - ``result_object`` sets the transformation's attribute that
                         is returned as result. Dot-notation lookup (e.g.
                         ``context.target``) is implemented. Per default the
                         :term:`transformation root` is returned.
                       - ``traversal_order`` sets the default traversal order for rule
                         evaluations and itself defaults to depth first, left to right,
                         to to bottom. See :ref:`traversal_strategies` for possible
                         values.
    """
    __slots__ = ('config', 'steps', 'states')

    config_defaults = {
        'common_rule_conditions': None,
        'context': {},
        'copy': True,
        'name': None,
        'result_object': 'root',
        'traversal_order': (
                TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_TOP_TO_BOTTOM
        )
    }
    """ The default :term:`configuration` values. Changing members on an instance
        actually affects the class unless a copy of this mapping as copied and bound
        as instance attribute. """

    traversers = {
        TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_BOTTOM_TO_TOP:
            traverse_df_ltr_btt,
        TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_TOP_TO_BOTTOM:
            traverse_df_ltr_ttb,
        TRAVERSE_ROOT_ONLY:
            traverse_root,
    }

    def __init__(self, *steps: StepType, **config: AnyType) -> None:
        dbg(f"Initializing transformation instance named: '{config.get('name')}'.")
        self.steps = _flatten_sequence(steps)
        self.config = SimpleNamespace(**config)
        self._set_config_defaults()
        self._expand_rules_conditions()
        self._validate_steps()
        self.states = None

    @property
    def name(self):
        """ The ``name`` member of the transformation's :term:`configuration`. """
        return getattr(self.config, 'name', None)

    def _expand_rules_conditions(self):
        common_rule_conditions = self.config.common_rule_conditions
        if common_rule_conditions is None:
            return

        if not isinstance(common_rule_conditions, Sequence) or \
                isinstance(common_rule_conditions, str):
            common_rule_conditions = (common_rule_conditions,)

        expanded_steps = []
        for step in self.steps:
            if isinstance(step, Rule):
                expanded_steps.append(
                    Rule(common_rule_conditions + step.conditions, step.handlers,
                         step.name, step.traversal_order))
            else:
                expanded_steps.append(step)
        self.steps = tuple(expanded_steps)

    def _set_config_defaults(self) -> None:
        for key, value in self.config_defaults.items():
            if not hasattr(self.config, key):
                dbg(f"Using default value '{value}' for config key '{key}'.")
                setattr(self.config, key, value)

    def _validate_steps(self):
        assert all(isinstance(x, (Callable, Rule)) for x in self.steps), \
            'Transformation steps must be either a `Rule` instance or a callable.'

    def __call__(self, input: Union[Document, TagNode],
                 copy: bool = None, **context: AnyType) -> AnyType:

        copy = self.config.copy if copy is None else copy
        self._init_transformation(input, copy, context)

        for step in self.steps:
            _step_name = step.name if hasattr(step, 'name') else step.__name__
            dbg(f"Processing rule '{_step_name}'.")

            self.states.current_step = step
            try:
                if isinstance(step, Rule):
                    self._apply_rule(step)
                else:
                    self._apply_handlers(step)
            except AbortTransformation:
                dbg("Aborting due to 'AbortTransformation'.")
                break

        if self.config.result_object:
            result = dot_lookup(self, self.config.result_object)

            if self.config.result_object == "root" and isinstance(input, Document):
                result = Document(result)

        else:
            result = None

        self._finalize_transformation()
        return result

    def _init_transformation(self, input: Union[Document, TagNode], copy: bool,
                             context: Dict[AnyStr, AnyType]) -> None:
        dbg('Initializing processing.')
        if not isinstance(input, (Document, TagNode)):
            raise TypeError(
                'A transformation must be called with a Document or TagNode instance, '
                f'got a {type(input)}.'
            )

        self.states = SimpleNamespace()
        self.states.current_node = None
        self.states.previous_result = None

        resolved_context = deepcopy(self.config.context)
        resolved_context.update(context)
        dbg(f'Initial context:\n{resolved_context}')
        self.states.context = SimpleNamespace(**resolved_context)

        if isinstance(input, Document):
            if copy:
                dbg('Cloning source.')
                input = input.clone()
            self.states.root = input.root
        else:
            if copy:
                dbg('Cloning source.')
                input = input.clone(deep=True)
            self.states.root = input

        static_symbols = {
            'config': self.config,
            'context': self.states.context,
            'nsmap': self.states.root.namespaces,
            'root': self.states.root,
            'transformation': self,
        }
        self.states.dynamic_symbols = {}
        self.states.symbols_chain = ChainMap(self.states.dynamic_symbols,
                                             static_symbols,
                                             self.states.context.__dict__,
                                             self.config.__dict__)

    def _apply_rule(self, rule: Rule) -> None:
        traverser = self._get_traverser(rule.traversal_order)
        dbg(f'Using traverser: {traverser}')

        for node in traverser(self.states.root):
            dbg(f'Evaluating {node}.')
            self.states.current_node = node
            try:
                if self._test_conditions(node, rule.conditions):
                    self._apply_handlers(*rule.handlers)
            except AbortRule:
                dbg('Aborting rule.')
                break
            except SkipToNextNode:
                dbg('Skipping to next node.')
                continue

        self.states.current_node = None

    @lru_cache(8)
    def _get_traverser(self, traversal_order: Union[int, None]) -> Callable:
        if traversal_order is None:
            traversal_order = self.config.traversal_order
        traverser = self.traversers.get(traversal_order)
        if traverser is None:
            raise NotImplementedError
        return traverser

    def _test_conditions(self, node: TagNode,
                         conditions: Sequence[Callable]) -> bool:
        # there's no dependency injection here because its overhead
        # shall be avoided during testing conditions
        for condition in conditions:
            dbg(f"Testing condition '{condition}'.")
            if not condition(node, self):
                dbg('The condition did not apply.')
                return False
            dbg('The condition applied.')
        return True

    def _apply_handlers(self, *handlers: Union[Callable, Exception]) -> None:
        dbg('Applying handlers.')
        for handler in handlers:
            if _is_flow_control(handler):
                raise handler
            kwargs = dependency_injection.resolve_dependencies(
                handler, self._available_symbols).as_kwargs
            if isinstance(handler, Transformation):
                kwargs['input'] = self.states.current_node or self.states.root
                kwargs['copy'] = False
            dbg(f"Applying handler {handler}.")
            self.states.previous_result = handler(**kwargs)

    def _finalize_transformation(self) -> None:
        dbg('Finalizing processing.')
        self.states = None

    @property
    def _available_symbols(self) -> Mapping:
        """ This mapping contains items that are used for the dependency injection of
            handler functions. These names are included:

            - All attributes of the transformation's :term:`configuration`,
              overridden by the following.
            - All attributes of the transformation's :term:`context`, overridden by
              the following.
            - ``config`` - The :term:`configuration` namespace object.
            - ``context`` - The :term:`context` namespace object.
            - ``node`` - The node that matched a :class:`Rule`'s conditions or
              ``None`` in case of simple :term:`transformation steps`.
            - ``previous_result`` - The result that was returned by the previously
              evaluated handler function.
            - ``root`` - The root node of the processed (sub-)document a.k.a.
              :term:`transformation root`.
            - ``transformation`` - The calling :class:`Transformation` instance.
        """
        self.states.dynamic_symbols.update({
            'node': self.states.current_node,
            'previous_result': self.states.previous_result,
        })
        return self.states.symbols_chain

    # aliases that are supposed to be broken when the transformation isn't processing

    @property
    def context(self):
        """ This property can be used to access the :term:`context` while the
            transformation is processing. """
        return self.states.context

    @property
    def root(self):
        """ This property can be used to access the root node of the currently
            processed (sub-)document. """
        return self.states.root


__all__ = [
    '__version__', 'logger',
    'TRAVERSE_BOTTOM_TO_TOP', 'TRAVERSE_DEPTH_FIRST', 'TRAVERSE_LEFT_TO_RIGHT',
    'TRAVERSE_RIGHT_TO_LEFT', 'TRAVERSE_ROOT_ONLY', 'TRAVERSE_TOP_TO_BOTTOM',
    'TRAVERSE_WIDTH_FIRST',
    AbortRule.__name__, AbortTransformation.__name__,
    SkipToNextNode.__name__, InxsException.__name__,
    'Any', 'Not', 'OneOf',
    'HasNamespace', 'HasLocalname', 'MatchesAttributes', 'MatchesXPath',
    'If', 'Ref',
    Rule.__name__, Once.__name__, Transformation.__name__
]
