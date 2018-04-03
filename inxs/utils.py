import string
from functools import lru_cache
from typing import Dict

from inxs.constants import REF_IDENTIFYING_ATTRIBUTE


# TODO add unicode whitespaces
WHITESPACES_WO_SPACE = string.whitespace.replace(' ', '')

# helpers


__all__ = []


def export(func):
    __all__.append(func.__name__)
    return func


# utils


@export
def is_Ref(obj):
    return hasattr(obj, REF_IDENTIFYING_ATTRIBUTE)


@lru_cache(8)
def _make_whitespace_translation_table(chars: str) -> Dict[int, str]:
    return str.maketrans(chars, ' ' * len(chars))


@export
def reduce_whitespaces(text: str, translate_to_space: str = WHITESPACES_WO_SPACE,
                       strip: str = 'lr') -> str:
    """ Reduces the whitespaces of the provided string by replacing any of the
        defined whitespaces with a simple space (U+20) and stripping consecutive ones to
        a single one.

        :param text: The input string.
        :param translate_to_space: The characters that should are defined as whitespace.
                                   Defaults to all common whitespace characters from
                                   the ASCII set.
        :param strip: The 'sides' of the string to strip from any whitespace at all,
                      indicated by 'l' for the beginning and/or 'r' fo the and og the
                      string.
        :returns: The resulting string.
        """
    translation_table = _make_whitespace_translation_table(translate_to_space)
    result = text.translate(translation_table)
    if 'l' in strip:
        result = result.lstrip()
    if 'r' in strip:
        result = result.rstrip()
    while '  ' in result:
        result = result.replace('  ', ' ')
    return result


@export
def resolve_Ref_values_in_mapping(mapping, transformation):
    result = mapping.__class__()
    for key, value in mapping.items():
        if is_Ref(value):
            result[key] = value(transformation)
        else:
            result[key] = value
    return result
