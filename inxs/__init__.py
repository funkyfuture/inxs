from copy import deepcopy
from functools import lru_cache
import logging
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
TRAVERSE_ROOT_ONLY = True << 3


# logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log = logger.debug


# exceptions


class InxsException(Exception):
    pass


class FlowControl(InxsException):
    def __init__(self):
        super().__init__()
        log(f'{self.__class__.__name__} is evoked.')


class AbortRule(FlowControl):
    """ Can be raised to abort the evaluation of remaining rule handlers. """
    pass


class AbortTransformation(FlowControl):
    """ Can be raised to abort a transformation. """


def is_flow_control(obj: AnyType) -> bool:
    try:
        return issubclass(obj, FlowControl)
    except TypeError:
        return False


# helpers


def _is_root_condition(element, transformation):
    return element is transformation.root


def _condition_factory(condition):
    if isinstance(condition, str):
        if condition == '/':
            return _is_root_condition
        elif ':' in condition and '::' not in condition:
            # assumes URI
            log(f'Adding {condition} as namespace condition.')
            return HasNamespace(condition)
        elif condition.isalpha():
            # assumes tag
            log(f"Adding {condition} as tag's local name condition.")
            return HasTag(condition)
        else:
            # assumes XPath
            log(f'Adding {condition} as XPath condition.')
            return MatchesXPath(condition)
    elif isinstance(condition, Mapping):
        log(f'Adding {condition} as attribute condition.')
        return MatchesAttributes(condition)
    else:
        return condition


def dict_from_namespace(ns):
    return {x: getattr(ns, x) for x in dir(ns) if not x.startswith('_')}


# rules definition


def Any(*conditions: Sequence):
    conditions = tuple(_condition_factory(x) for x in conditions)

    def evaluator(element, transformation):
        return any(x(element, transformation) for x in conditions)
    return evaluator


def OneOf(*conditions: Sequence):
    conditions = tuple(_condition_factory(x) for x in conditions)

    def evaluator(element, transformation):
        return [(x(element, transformation) for x in conditions)].count(True) == 1
    return evaluator


def Not(*conditions: Sequence):
    conditions = tuple(_condition_factory(x) for x in conditions)

    def evaluator(element, transformation):
        return not any(x(element, transformation) for x in conditions)
    return evaluator


def HasNamespace(namespace: str):
    def evaluator(element, _):
        return etree.QName(element).namespace == namespace
    return evaluator


def HasTag(tag: str):
    def evaluator(element, _):
        return etree.QName(element).localname == tag
    return evaluator


def MatchesXPath(xpath: Union[str, Callable]):
    def evaluator(element, transformation):
        if callable(xpath):
            _xpath = xpath(transformation)
            log(f"Resolved XPath from callable: '{_xpath}'")
        else:
            _xpath = xpath
        return element in transformation.xpath_evaluator(_xpath)
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
                if key_constraint not in attributes:
                    return False
                if not match_value(attributes[key_constraint], value_constraint):
                    return False
            elif isinstance(key_constraint, Pattern):
                for key in (x for x in attributes if key_constraint.match(x)):
                    if not match_value(attributes[key], value_constraint):
                        return False
        return True

    return evaluator


def Ref(name) -> AnyType:
    def resolver(transformation):
        log(f'Resolving {name}.')
        return transformation._available_dependencies[name]
    return resolver


def If(x, operator, y):
    def evaluator(_, transformation):
        if callable(x):
            _x = x(**dependency_injection.resolve_dependencies(
                 x, transformation._available_dependencies).as_kwargs)
            log(f"x resolved to '{_x}'")
        else:
            _x = x
        if callable(y):
            _y = y(**dependency_injection.resolve_dependencies(
                 y, transformation._available_dependencies).as_kwargs)
            log(f"y resolved to '{_y}'")
        else:
            _y = y
        return operator(_x, _y)
    return evaluator


class Rule:
    __slots__ = ('name', 'conditions', 'handlers', 'traversal_order')

    def __init__(self, conditions, handlers, name: str = None,
                 traversal_order: Union[int, None] = None) -> None:
        self.name = name
        log(f"Initializing rule '{name}'.")
        self.conditions = ()
        if not isinstance(conditions, Sequence) or isinstance(conditions, str):
            conditions = (conditions,)
        self.conditions = tuple(_condition_factory(x) for x in conditions)
        if _is_root_condition in self.conditions:
            traversal_order = TRAVERSE_ROOT_ONLY
            self.conditions = tuple(x for x in self.conditions if x is not _is_root_condition)
        if not isinstance(handlers, Sequence):
            handlers = (handlers,)
        self.handlers = handlers
        self.traversal_order = traversal_order


# transformation


def _traverse_df_ltr_btt(root) -> Iterator[etree._Element]:
    def yield_children(element):
        for child in element:
            yield from yield_children(child)
        yield element
    yield from yield_children(root)


def _traverse_df_ltr_ttb(root) -> Iterator[etree._Element]:
    yield from root.iter()


def _traverse_root(root) -> Iterator[etree._Element]:
    yield root
    raise StopIteration


class Transformation:
    __slots__ = ('name', 'description', 'config', 'rules', 'states')

    config_defaults = {
        'context': {},
        'copy': True,
        'traversal_order': TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_TOP_TO_BOTTOM
    }

    traversers = {
        TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_BOTTOM_TO_TOP:
            _traverse_df_ltr_btt,
        TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_TOP_TO_BOTTOM:
            _traverse_df_ltr_ttb,
        TRAVERSE_ROOT_ONLY: _traverse_root
    }

    def __init__(self, *rules, name: str = None, **config) -> None:
        self.name = name
        log(f"Initializing transformation instance '{name}'.")
        self.rules = rules
        self.config = SimpleNamespace(**config)
        self._set_config_defaults()
        for name in self.config.context:
            assert name[0].isalpha()
        self.states = None

    def _set_config_defaults(self) -> None:
        for key, value in self.config_defaults.items():
            if not hasattr(self.config, key):
                log(f"Using default value '{value}' for config key '{key}'.")
                setattr(self.config, key, value)

    def __call__(self, source: Union[etree._Element, etree._ElementTree], **context) -> AnyType:
        self._init_transformation(source, context)

        for rule in self.rules:
            _rule_name = rule.name if isinstance(rule, Rule) else rule.__name__
            log(f"Processing rule '{_rule_name}'.")

            self.states.current_rule = rule
            try:
                if isinstance(rule, Rule):
                    self._apply_rule(rule)
                elif callable(rule):
                    self._apply_handlers((rule,))
                else:
                    raise RuntimeError
            except AbortTransformation:
                log("Aborting due to 'AbortTransformation'.")
                break

        result = self._get_object_by_name(self.config.result_object)
        self._finalize_transformation()
        return result

    def _init_transformation(self, source, context) -> None:
        log(f'Initializing processing.')
        self.states = SimpleNamespace()
        self.states.previous_result = None

        resolved_context = deepcopy(self.config.context)
        resolved_context.update(context)
        log(f'Initial context:\n{resolved_context}')
        self.states.context = SimpleNamespace(**resolved_context)

        if self.config.copy:
            log('Cloning source document.')
            source = deepcopy(source)

        if isinstance(source, etree._ElementTree):
            self.states.context.tree = source
            self.states.context.root = source.getroot()
            if getattr(self.config, 'result_object', None) is None:
                log("Setting result_object to 'context.tree'.")
                self.config.result_object = 'context.tree'
        elif isinstance(source, etree._Element):
            self.states.context.tree = source.getroottree()
            self.states.context.root = source
            if getattr(self.config, 'result_object', None) is None:
                log("Setting result_object to 'context.root'.")
                self.config.result_object = 'context.root'

        self.states.xpath_evaluator = etree.XPathEvaluator(source, smart_prefix=True)

    def _apply_rule(self, rule) -> None:
        traverser = self._get_traverser(rule.traversal_order)
        log(f'Using traverser: {traverser}')
        for element in traverser(self.states.context.root):
            log(f'Evaluating {element}.')
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
            raise NotImplementedError
        return traverser

    def _test_conditions(self, element, conditions) -> bool:
        # there's no dependency injection here because its overhead
        # shall be avoided during testing conditions
        for condition in conditions:
            log(f"Testing condition '{condition}'.")
            if not condition(element, self):
                log('The condition did not apply.')
                return False
            log('The condition applied.')
        return True

    def _apply_handlers(self, handlers) -> None:
        log('Applying handlers.')
        for handler in handlers:
            if is_flow_control(handler):
                raise handler
            if isinstance(handler, Sequence):
                self._apply_handlers(handlers)
            kwargs = dependency_injection.resolve_dependencies(
                handler, self._available_dependencies).as_kwargs
            if isinstance(handler, Transformation):
                kwargs['source'] = self.states.current_element
                kwargs['copy'] = False  # FIXME?! that may not always be desirable
            log(f"Applying handler {handler}.")
            self.states.previous_result = handler(**kwargs)

    def _finalize_transformation(self) -> None:
        log('Finalizing preocessing.')
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

    @property
    def tree(self):
        return self.states.context.tree

    @property
    def xpath_evaluator(self):
        return self.states.xpath_evaluator
