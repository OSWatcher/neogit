"""
Visitor design pattern

Taken from https://github.com/nodejs/node/blob/master/tools/inspector_protocol/jinja2/visitor.py (NodeJS)
"""

import logging
from typing import Callable, Generator, Optional

from attrs import define, field
from attrs.validators import instance_of

from neogit.core.model import Node
from neogit.utils import DEFAULT_CLASS_LOGGER


@define(auto_attribs=True)
class VisitedNode:
    """A node that has been visited by a visitor and the return value of the visit function."""

    node: Node = field(validator=instance_of(Node))
    """The node that was visited."""
    return_value: Node = field()
    """The return value of the visit function."""


@define(auto_attribs=True)
class NodeVisitor:
    """Walks the abstract syntax tree and call visitor functions for every
    node found.  The visitor functions may return values which will be
    forwarded by the `visit` method.
    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `get_visitor` function.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.
    """

    logger: logging.Logger = field(default=DEFAULT_CLASS_LOGGER, init=False)

    def get_visitor(self, node: Node, prefix="visit_") -> Optional[Callable]:
        """Return the visitor function for this node or `None` if no visitor
        exists for this node.  In that case the generic visit function is
        used instead.
        """
        method = prefix + node.__class__.__name__
        return getattr(self, method, None)

    def visit(self, node: Node, *args, **kwargs) -> Generator[VisitedNode, None, None]:
        """Visit a node."""
        f = self.get_visitor(node)
        self.logger.debug("visit %s", node)
        if f is not None:
            yield from f(node, *args, **kwargs)
        else:
            yield from self.generic_visit(node, *args, **kwargs)

    def generic_visit(self, node: Node, *args, **kwargs) -> Generator[VisitedNode, None, None]:
        """Called if no explicit visitor function exists for a node."""
        for node in node.iter_child_nodes():
            yield from self.visit(node, *args, **kwargs)

    def done_visiting(self):
        """a workaround method to put the None object inside the queue, if any"""
        # TODO: better interface ?
        if self.queue_list:
            for q in self.queue_list:
                q.put(None)
