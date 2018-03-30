import string
from functools import lru_cache
from typing import Dict

# TODO add unicode whitespaces
WHITESPACES_WO_SPACE = string.whitespace.replace(' ', '')


@lru_cache(8)
def _make_whitespace_translation_table(chars: str) -> Dict[int, str]:
    return str.maketrans(chars, ' ' * len(chars))


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
