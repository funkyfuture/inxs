from inxs import \
    (TRAVERSE_DEPTH_FIRST, TRAVERSE_BOTTOM_TO_TOP, TRAVERSE_LEFT_TO_RIGHT,
     lib, Not, Rule, Transformation)
from inxs.xml_utils import remove_element


__all__ = []


def _prepend_tail(element):
    if not element.tail:
        return
    previous = element.getprevious()
    if previous is None:
        element.getparent().text += element.tail
    else:
        previous.tail += element.tail


remove_empty_elements = Transformation(
    Rule(Not(lib.has_children, lib.has_text, lib.has_attributes, '/'),
         (_prepend_tail, remove_element)),
    name='remove_empty_elements',
    traversal_order=TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_BOTTOM_TO_TOP
)
__all__.append('remove_empty_elements')
