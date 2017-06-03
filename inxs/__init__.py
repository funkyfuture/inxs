from copy import deepcopy
from functools import lru_cache
from types import SimpleNamespace
from typing import Callable, Iterator, Mapping, Pattern, Sequence, Union
from typing import Any as AnyType

import dependency_injection
from lxml import etree


# constants

__version__ = '0.1a0'

TRAVERSE_DEPTH_FIRST = True << 0
TRAVERSE_WIDTH_FIRST = False << 0
TRAVERSE_LEFT_TO_RIGHT = True << 1
TRAVERSE_RIGHT_TO_LEFT = False << 1
TRAVERSE_TOP_TO_BOTTOM = True << 2
TRAVERSE_BOTTOM_TO_TOP = False << 2


# exceptions


class InxsException(Exception):
    pass


class FlowControl(InxsException):  # FIXME rather like StopIteration
    pass


class AbortRule(FlowControl):
    """ Can be raised to abort the evaluation of remaining rule handlers. """
    pass


class AbortTransformation(FlowControl):
    """ Can be raised to abort a transformation. """


# helpers


def dict_from_namespace(ns):
    return {x: getattr(ns, x) for x in dir(ns) if not x.startswith('_')}


# rules definition


def Any(*conditions: Sequence):
    def evaluator(element, *_):
        return any(x(element) for x in conditions)
    return evaluator


def OneOf(*conditions: Sequence):
    def evaluator(element, *_):
        return [(x(element) for x in conditions)].count(True) == 1
    return evaluator


def Not(*conditions: Sequence):
    def evaluator(element, *_):
        return not any(x(element) for x in conditions)
    return evaluator


def HasNamespace(namespace: str):
    def evaluator(element, *_):
        return etree.QName(element).namespace == namespace
    return evaluator


def HasTag(tag: str):
    def evaluator(element, *_):
        return etree.QName(element).localname == tag
    return evaluator


def MatchesXPath(xpath: str):
    def evaluator(element, transformation):
        return element in transformation.states.xpath_evaluator(xpath)
    return evaluator


def MatchesAttributes(constraints: Mapping):
    def match_value(value, constraint):
        if isinstance(constraint, str):
            return value == constraint
        elif isinstance(constraint, Pattern):
            return constraint.match(value)

    def evaluator(element, *_):
        attributes = element.attrib
        for key_constraint, value_constraint in constraints.items():
            if isinstance(key_constraint, str):
                if not match_value(attributes[key_constraint], value_constraint):
                    return False
            elif isinstance(key_constraint, Pattern):
                for key in (x for x in attributes if key_constraint.match(x)):
                    if not match_value(attributes[key], value_constraint):
                        return False
        return True

    return evaluator


# TODO If (to test stuff from the namespaces)


class Rule:
    __slots__ = ('name', 'conditions', 'handlers', 'traversal_order')

    def __init__(self, conditions, handlers, name: str = None,
                 traversal_order: int = None) -> None:
        self.name = name
        self.conditions = ()
        if not isinstance(conditions, Sequence):
            conditions = (conditions,)
        for condition in conditions:
            if isinstance(condition, str):
                if ':' in condition and '::' not in condition:
                    # assumes URI
                    self.conditions += (HasNamespace(condition),)
                elif condition.isalpha():
                    # assumes tag
                    self.conditions += (HasTag(condition),)
                else:
                    # assumes XPath
                    self.conditions += (MatchesXPath(condition),)
            elif isinstance(condition, Mapping):
                self.conditions += (MatchesAttributes(condition),)
            else:
                self.conditions += (condition,)
        if not isinstance(handlers, Sequence):
            handlers = (handlers,)
        self.handlers = handlers
        self.traversal_order = traversal_order


# transformation


def _traverse_df_ltr_ttb(root) -> Iterator[etree._Element]:
    yield from root.iter()


class Transformation:
    __slots__ = ('name', 'rules', 'config', 'states')

    config_defaults = {
        'context': {},
        'copy': True,
        'traversal_order': TRAVERSE_DEPTH_FIRST | TRAVERSE_TOP_TO_BOTTOM | TRAVERSE_LEFT_TO_RIGHT
    }

    traversers = {
        TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_TOP_TO_BOTTOM:
            _traverse_df_ltr_ttb,
    }

    def __init__(self, *rules, name: str = None, **config) -> None:
        self.name = name
        self.rules = rules
        self.config = SimpleNamespace(**config)
        self._set_config_defaults()
        self.states = None

    def _set_config_defaults(self) -> None:
        for key, value in self.config_defaults.items():
            if not hasattr(self.config, key):
                setattr(self.config, key, value)

    def __call__(self, source: Union[etree._Element, etree._ElementTree], **context) -> AnyType:
        self._init_transformation(source, context)

        for rule in self.rules:
            self.states.current_rule = rule
            try:
                if isinstance(rule, Rule):
                    self._apply_rule(rule)
                elif callable(rule):
                    self._apply_handlers((rule,))
                else:
                    raise RuntimeError
            except AbortTransformation:
                break

        result = self._get_object_by_name(self.config.result_object)
        self._finalize_transformation()
        return result

    def _init_transformation(self, source, context) -> None:
        self.states = SimpleNamespace()
        self.states.previous_result = None

        resolved_context = deepcopy(self.config.context)
        resolved_context.update(context)
        self.states.context = SimpleNamespace(**resolved_context)

        if self.config.copy:
            source = deepcopy(source)

        if isinstance(source, etree._ElementTree):
            self.states.context.tree = source
            self.states.context.root = source.getroot()
            if getattr(self.config, 'result_object', None) is None:
                self.config.result_object = 'context.tree'
        elif isinstance(source, etree._Element):
            self.states.context.tree = source.getroottree()
            self.states.context.root = source
            if getattr(self.config, 'result_object', None) is None:
                self.config.result_object = 'context.root'

        self.states.xpath_evaluator = etree.XPathEvaluator(source, smart_prefix=True)

    def _apply_rule(self, rule) -> None:
        traverser = self._get_traverser(rule.traversal_order)
        for element in traverser(self.states.context.root):
            self.states.current_element = element
            if self._test_conditions(element, rule.conditions):
                try:
                    self._apply_handlers(rule.handlers)
                except AbortRule:
                    break

    @lru_cache(8)
    def _get_traverser(self, traversal_order: Union[int, None]) -> Callable:
        if traversal_order is None:
            traversal_order = self.config.traversal_order
        traverser = self.traversers.get(traversal_order)
        if traverser is None:
            raise NotImplemented
        return traverser

    def _test_conditions(self, element, conditions) -> bool:
        for condition in conditions:
            if not condition(element, self):
                return False
        return True

    def _apply_handlers(self, handlers) -> None:
        for handler in handlers:
            if isinstance(handler, Sequence):
                self._apply_handlers(handlers)
            kwargs = dependency_injection.resolve_dependencies(
                handler, self._available_dependencies).as_kwargs
            if isinstance(handler, Transformation):
                kwargs['source'] = kwargs['element']
                kwargs['copy'] = False  # FIXME?! that may not always be desirable
            self.states.previous_result = handler(**kwargs)

    def _finalize_transformation(self) -> None:
        self.states = None

    @property
    def _available_dependencies(self) -> Mapping:
        context = self.states.context
        result = dict_from_namespace(self.config)
        result.update(dict_from_namespace(context))
        result.update({
            'config': self.config,
            'context': context,
            'element': getattr(self.states, 'current_element', None),
            'previous_result': self.states.previous_result,
            'root': context.root,
            'transformation': self,
            'transformation_name': self.name,
            'tree': context.tree,
        })

        rule = self.states.current_rule
        if isinstance(rule, Rule):
            result['rule_name'] = rule.name
        elif callable(rule):
            result['rule_name'] = rule.__name__

        return result

    def _get_object_by_name(self, fqn) -> AnyType:
        context = self
        if fqn.startswith('context.'):
            fqn = 'states.' + fqn

        for name in fqn.split('.'):
            context = getattr(context, name)
        return context

    # aliases that are supposed to be broken when the transformation isn't processed

    @property
    def context(self):
        return self.states.context
