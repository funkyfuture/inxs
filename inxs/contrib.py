""" This module contains transformations that are supposedly of common interest. """

from delb import TagNode, is_text_node

from inxs import (
    TRAVERSE_DEPTH_FIRST,
    TRAVERSE_BOTTOM_TO_TOP,
    TRAVERSE_LEFT_TO_RIGHT,
    lib,
    utils,
    Not,
    Rule,
    Transformation,
)

__all__ = []


# reduce_whitespaces


def _reduce_whitespace_handler(node: TagNode):
    for child in node.child_nodes(is_text_node, recurse=True):
        child.content = utils.reduce_whitespaces(node.content, strip="")


reduce_whitespaces = Transformation(Rule("/", _reduce_whitespace_handler))
"""
Normalizes any whitespace character in text nodes to a simple space and reduces
consecutive ones to one. Leading or tailing whitespaces are not stripped away.
"""
__all__.append("reduce_whitespaces")


# remove_empty_nodes


remove_empty_nodes = Transformation(
    Rule(Not(lib.has_children, lib.has_text, lib.has_attributes, "/"), lib.remove_node),
    name="remove_empty_nodes",
    traversal_order=(
        TRAVERSE_DEPTH_FIRST | TRAVERSE_LEFT_TO_RIGHT | TRAVERSE_BOTTOM_TO_TOP
    ),
)
"""
Removes nodes without attributes, text and children.
"""
__all__.append("remove_empty_nodes")
