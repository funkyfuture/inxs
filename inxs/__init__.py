from copy import deepcopy
from functools import lru_cache
import logging
from types import SimpleNamespace
from typing import Callable, Dict, Iterator, Mapping, Pattern, Sequence, Union
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
""" Module logger, configure as you need. """
dbg = logger.debug
nfo = logger.info


# exceptions


class InxsException(Exception):
    """ Base class for inxs exceptions. """
    pass


class FlowControl(InxsException):
    """ Base class for exception that control the evaluation of handlers. """
    def __init__(self):
        super().__init__()
        dbg('{} is evoked.'.format(self.__class__.__name__))


class AbortRule(FlowControl):
    """ Can be raised to abort the evaluation of the currently processed rule's remaining
        tests and handlers.
    """
    pass


class AbortTransformation(FlowControl):
    """ Can be raised to cancel the remaining :term:`transformation steps`. """


# helpers

AttributesConditionType = Dict[Union[str, Pattern], Union[str, Pattern, None]]


def _condition_factory(condition: Union[str, AttributesConditionType, Callable]) -> Callable:
    """ Generates test functions for conditions provided as string or mapping. """
    if isinstance(condition, str):
        if condition == '/':
            return _is_root_condition
        elif condition == '*':
            return _is_any_element_condition
        elif ':' in condition and '::' not in condition:
            # assumes URI
            dbg('Adding {} as namespace condition.'.format(condition))
            return HasNamespace(condition)
        elif condition.isalpha():
            # assumes tag
            dbg("Adding {} as tag's local name condition.".format(condition))
            return HasLocalname(condition)
        else:
            # assumes XPath
            dbg('Adding {} as XPath condition.'.format(condition))
            return MatchesXPath(condition)
    elif isinstance(condition, Mapping):
        dbg('Adding {} as attribute condition.'.format(condition))
        return MatchesAttributes(condition)
    else:
        return condition


def _is_any_element_condition(_, __):
    return True


def _is_flow_control(obj: AnyType) -> bool:
    try:
        return issubclass(obj, FlowControl)
    except TypeError:
        return False


def _is_root_condition(element, transformation):
    return element is transformation.root


# rules definition


def Any(*conditions: Sequence[Callable]) -> Callable:
    """ Returns a callable that evaluates the provided test functions and returns ``True`` if any
        of them returned that.
    """
    conditions = tuple(_condition_factory(x) for x in conditions)

    def evaluator(element: etree._Element, transformation: Transformation) -> bool:
        return any(x(element, transformation) for x in conditions)
    return evaluator


def OneOf(*conditions: Sequence[Callable]) -> Callable:
    """ Returns a callable that evaluates the provided test functions and returns ``True`` if
        exactly one of them returned that.
    """
    conditions = tuple(_condition_factory(x) for x in conditions)

    def evaluator(element: etree._Element, transformation: Transformation) -> bool:
        return [x(element, transformation) for x in conditions].count(True) == 1
    return evaluator


def Not(*conditions: Sequence[Callable]) -> Callable:
    """ Returns a callable that evaluates the provided test functions and returns ``True`` if none
        of them returned that.
    """
    conditions = tuple(_condition_factory(x) for x in conditions)

    def evaluator(element: etree._Element, transformation: Transformation) -> bool:
        return not any(x(element, transformation) for x in conditions)
    return evaluator


def HasNamespace(namespace: str) -> Callable:
    """ Returns a callable that tests an element for the given namespace. """
    def evaluator(element: etree._Element, _) -> bool:
        return etree.QName(element).namespace == namespace
    return evaluator


def HasLocalname(tag: str) -> Callable:
    """ Returns a callable that tests an element for the given local tag name. """
    def evaluator(element: etree._Element, _) -> bool:
        return etree.QName(element).localname == tag
    return evaluator


def MatchesXPath(xpath: Union[str, Callable]) -> Callable:
    """ Returns a callable that tests an element for the given XPath expression. If the ``xpath``
        argument is a callable, it will be called with the current transformation as argument to
        obtain the expression.
    """
    def callable_evaluator(element: etree._Element, transformation: Transformation) -> bool:
        _xpath = xpath(transformation)
        dbg("Resolved XPath from callable: '{}'".format(_xpath))
        return element in transformation.xpath_evaluator(_xpath)

    def string_evaluator(element: etree._Element, transformation: Transformation) -> bool:
        return element in transformation.xpath_evaluator(xpath)

    return callable_evaluator if callable(xpath) else string_evaluator


def MatchesAttributes(constraints: AttributesConditionType) -> Callable:
    """ Returns a callable that tests an element's attributes  for constrains defined in a
        dictionary.
        All constraints must be matched to resolve as true. Expected keys and values can be
        provided as string or compiled regular expression object from the :mod:`re` module.
        A ``None`` as value constraint evaluates as true if the key is in the attributes regardless
        its value. It also implies that at least one attribute must match the key's constraint if
        this is a regular expression object.
    """
    # TODO optimize w/ dedicated functions
    def match_value(value: str, constraint: Union[str, Pattern]) -> bool:
        if isinstance(constraint, str):
            return value == constraint
        elif isinstance(constraint, Pattern):
            return constraint.match(value)

    def evaluator(element: etree._Element, _) -> bool:
        attributes = element.attrib
        for key_constraint, value_constraint in constraints.items():
            if isinstance(key_constraint, str):
                if key_constraint not in attributes:
                    return False
                if value_constraint is None:
                    continue
                if not match_value(attributes[key_constraint], value_constraint):
                    return False
            elif isinstance(key_constraint, Pattern):
                matched_keys = [x for x in attributes if key_constraint.match(x)]
                if value_constraint is None and not matched_keys:
                    return False
                for key in matched_keys:
                    if not match_value(attributes[key], value_constraint):
                        return False
        return True

    return evaluator


def Ref(name: str) -> Callable:
    """ Returns a callable that can be used for value resolution in a function that supports that.
        The value will be looked up during the processing of a transformation in
        :attr:`Transformation._available_symbols`
        by the given ``name``.
        This allows to reference dynamic values in :term:`transformation steps` and rules.
    """
    def resolver(transformation) -> AnyType:
        dbg('Resolving {}.'.format(name))
        return transformation._available_symbols[name]
    return resolver


def If(x: AnyType, operator: Callable, y: AnyType) -> Callable:
    """ Returns a callable that can be used as condition test in a :class:`Rule`.
        The arguments ``x`` and ``y`` can be given as callables that will be used to get the
        ``operator``'s input values during execution.
        Before you implement your own operators, mind that there are a lot available within
        Python's ``__builtins__`` and the standard library, in particular the :mod:`operator`
        module.

        Examples:

        >>> If(Ref('previous_result'), operator.is_not, None)

    """
    # TODO allow single arguments
    def evaluator(_, transformation: Transformation) -> AnyType:
        if callable(x):
            _x = x(**dependency_injection.resolve_dependencies(
                 x, transformation._available_symbols).as_kwargs)
            dbg("x resolved to '{}'".format(_x))
        else:
            _x = x
        if callable(y):
            _y = y(**dependency_injection.resolve_dependencies(
                 y, transformation._available_symbols).as_kwargs)
            dbg("y resolved to '{_y}'".format(_y))
        else:
            _y = y
        return operator(_x, _y)
    return evaluator


class Rule:
    """ Instances of this class can be used as conditional :term:`transformation steps` that are
        evaluated against all traversed elements.

        :param conditions: All given conditions must evaluate as ``True`` in order for this
                           rule to apply.
                           Strings and mappings can be provided as shortcuts, see
                           :ref:`rule_condition_shortcuts` for details.
                           The conditions are always called with the currently evaluated
                           ``element`` and the :class:`Transformation` instance as arguments.
                           There are helper functions for grouping conditions: :func:`Any`,
                           :func:`Not` and :func:`OneOf`.
        :type conditions: A single callable, string or mapping, or a sequence of such.
        :param handlers: These handlers will be called if the conditions matched. They can take
                         any argument whose name is available in
                         :attr:`Transformation._available_symbols`.
        :type handlers: A single callable or a sequence of such.
        :param name: The optional rule's name.
        :type name: String.
        :param traversal_order: An optional traversal order that overrides the transformation's
                                default :attr:`Transformation.config.traversal_order`, see
                                :ref:`traversal_strategies` for details.
        :type traversal_order: Integer.
    """
    __slots__ = ('name', 'conditions', 'handlers', 'traversal_order')

    def __init__(self, conditions, handlers, name: str = None,
                 traversal_order: Union[int, None] = None):

        # TODO concatenate subgroups of conditions and handlers, same w/ steps
        # to remove instance checks during processing

        self.name = name
        dbg("Initializing rule '{}'.".format(name))
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


class Transformation:
    """ A transformation instance is defined by its :term:`transformation steps` and
        :term:`configuration`. It is to be called with an ``lxml`` representation of an XML tree
        or an XML element. In the latter case only this element and its children will be
        considered during traversal. Also, arbitrary keyword arguments can be provided when
        calling to populate the the transformation's :term:`context`.

        :param steps: The designated transformation steps of the instance.
        :param config: The configuration values for the instance.
    """
    __slots__ = ('config', 'steps', 'states')

    config_defaults = {
        'context': {},
        'copy': True,
        'traversal_order': TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_TOP_TO_BOTTOM
    }
    """ The default :term:`configuration` values. """

    traversers = {
        TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_BOTTOM_TO_TOP:
            _traverse_df_ltr_btt,
        TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_TOP_TO_BOTTOM:
            _traverse_df_ltr_ttb,
        TRAVERSE_ROOT_ONLY: _traverse_root
    }

    def __init__(self, *steps, **config):
        dbg("Initializing transformation instance named: '{}'.".format(config.get('name')))
        self.steps = steps
        self.config = SimpleNamespace(**config)
        self._set_config_defaults()
        self.states = None

    @property
    def name(self):
        """ The ``name`` member of the transformation's :term:`configuration`. """
        return getattr(self.config, 'name', None)

    def _set_config_defaults(self) -> None:
        for key, value in self.config_defaults.items():
            if not hasattr(self.config, key):
                dbg("Using default value '{}' for config key '{}'.".format(value, key))
                setattr(self.config, key, value)

    def __call__(self, source: Union[etree._Element, etree._ElementTree], **context) -> AnyType:
        self._init_transformation(source, context)

        for step in self.steps:
            _step_name = step.name if hasattr(step, 'name') else step.__name__
            dbg("Processing rule '{}'.".format(_step_name))

            self.states.current_step = step
            try:
                if isinstance(step, Rule):
                    self._apply_rule(step)
                elif callable(step) or isinstance(step, Sequence):
                    self._apply_handlers(step)
                else:
                    raise RuntimeError
            except AbortTransformation:
                dbg("Aborting due to 'AbortTransformation'.")
                break

        result = self._get_object_by_name(self.config.result_object)
        self._finalize_transformation()
        return result

    def _init_transformation(self, source, context) -> None:
        dbg('Initializing processing.')
        self.states = SimpleNamespace()
        self.states.previous_result = None

        resolved_context = deepcopy(self.config.context)
        resolved_context.update(context)
        dbg('Initial context:\n{}'.format(resolved_context))
        self.states.context = SimpleNamespace(**resolved_context)

        if self.config.copy:
            dbg('Cloning source document.')
            source = deepcopy(source)

        if isinstance(source, etree._ElementTree):
            self.states.context.tree = source
            self.states.context.root = source.getroot()
            if getattr(self.config, 'result_object', None) is None:
                dbg("Setting result_object to 'context.tree'.")
                self.config.result_object = 'context.tree'
                self.states.__config_result_object_is_none__ = True
            else:
                self.states.__config_result_object_is_none__ = False
        elif isinstance(source, etree._Element):
            self.states.context.tree = source.getroottree()
            self.states.context.root = source
            if getattr(self.config, 'result_object', None) is None:
                dbg("Setting result_object to 'context.root'.")
                self.config.result_object = 'context.root'
                self.states.__config_result_object_is_none__ = True
            else:
                self.states.__config_result_object_is_none__ = False
        self.states.xpath_evaluator = etree.XPathEvaluator(source, smart_prefix=True)

    def _apply_rule(self, rule) -> None:
        traverser = self._get_traverser(rule.traversal_order)
        dbg('Using traverser: {}'.format(traverser))
        try:
            for element in traverser(self.states.context.root):
                dbg('Evaluating {}.'.format(element))
                self.states.current_element = element
                if self._test_conditions(element, rule.conditions):
                    self._apply_handlers(*rule.handlers)
        except AbortRule:
            pass
        finally:
            self.states.current_element = None

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
            dbg("Testing condition '{}'.".format(condition))
            if not condition(element, self):
                dbg('The condition did not apply.')
                return False
            dbg('The condition applied.')
        return True

    def _apply_handlers(self, *handlers) -> None:
        dbg('Applying handlers.')
        for handler in handlers:
            if _is_flow_control(handler):
                raise handler
            if isinstance(handler, Sequence):
                self._apply_handlers(*handler)
            kwargs = dependency_injection.resolve_dependencies(
                handler, self._available_symbols).as_kwargs
            if isinstance(handler, Transformation):
                kwargs['source'] = self.states.current_element or self.states.context.tree
                kwargs['copy'] = False  # FIXME?! that may not always be desirable
            dbg("Applying handler {}.".format(handler))
            self.states.previous_result = handler(**kwargs)

    def _finalize_transformation(self) -> None:
        dbg('Finalizing preocessing.')
        if self.states.__config_result_object_is_none__:
            del self.config.result_object
        self.states = None

    @property
    def _available_symbols(self) -> Mapping:
        """ This mapping contains items that are used for the dependency injection of handler
            functions. These names are included:

            - All attributes of the transformation's :term:`configuration`, overridden by the
              following.
            - All attributes of the transformation's :term:`context`, overridden by the following.
            - ``element`` - The element that matched a :class:`Rule`'s conditions or ``None``.
            - ``previous_result`` - The result that was returned by the previously evaluated
              handler function.
            - ``root`` - The root element of the processed (sub-)document.
            - ``transformation`` - The calling :class:`Transformation` instance.
            - ``tree`` - The tree object of the processed document.

        """
        context = self.states.context
        symbols = deepcopy(vars(self.config))
        symbols.update(vars(context))
        symbols.update({
            'config': self.config,
            'context': context,
            'element': getattr(self.states, 'current_element', None),
            'previous_result': self.states.previous_result,
            'root': context.root,
            'transformation': self,
            'tree': context.tree,
        })
        return symbols

    def _get_object_by_name(self, fqn) -> AnyType:
        namespace = self
        for name in fqn.split('.'):
            namespace = getattr(namespace, name)
        return namespace

    # aliases that are supposed to be broken when the transformation isn't processing

    @property
    def context(self):
        """ This property can be used to access the :term:`context` while the transformation is
            processing.
        """
        return self.states.context

    @property
    def root(self):
        """ This property can be used to access the root element of the currently processed
            (sub-)document.
        """
        return self.states.context.root

    @property
    def tree(self):
        """ This property can be used to access the tree object of the currently processed
            document.
        """
        return self.states.context.tree

    @property
    def xpath_evaluator(self):
        """ During a transformation an :class:`lxml.etree.XPathEvaluator` using the processed
            (sub-)document's root element as such is bound to this property. """
        return self.states.xpath_evaluator


__all__ = [
    '__version__', 'logger',
    'TRAVERSE_BOTTOM_TO_TOP', 'TRAVERSE_DEPTH_FIRST', 'TRAVERSE_LEFT_TO_RIGHT',
    'TRAVERSE_RIGHT_TO_LEFT', 'TRAVERSE_ROOT_ONLY', 'TRAVERSE_TOP_TO_BOTTOM',
    'TRAVERSE_WIDTH_FIRST',
    AbortRule.__name__, AbortTransformation.__name__, InxsException.__name__,
    'Any', 'Not', 'OneOf',
    'HasNamespace', 'HasLocalname', 'MatchesAttributes', 'MatchesXPath',
    'If', 'Ref',
    Rule.__name__, Transformation.__name__
]
