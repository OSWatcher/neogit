"""
Visitor design pattern

Taken from https://github.com/nodejs/node/blob/master/tools/inspector_protocol/jinja2/visitor.py (NodeJS)
"""

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from queue import Queue
from typing import Callable, Generator, Optional, Self

from attrs import define, field
from attrs.validators import instance_of

from neogit.core.model import Node
from neogit.utils import DEFAULT_CLASS_LOGGER, BetterContextManager


@define(auto_attribs=True)
class VisitedNode:
    """A node that has been visited by a visitor and the return value of the visit function."""

    node: Node = field(validator=instance_of(Node))
    """The node that was visited."""
    return_value: Node = field()
    """The return value of the visit function."""


@define(auto_attribs=True)
class NodeVisitor(BetterContextManager):
    """Walks the abstract syntax tree and call visitor functions for every
    node found.  The visitor functions may return values which will be
    forwarded by the `visit` method.
    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `get_visitor` function.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.
    """

    # runs in a separate thread
    thread: bool = field(kw_only=True, default=False)
    thread_pool: Optional[ThreadPoolExecutor] = field(default=None, init=False)
    logger: logging.Logger = field(default=DEFAULT_CLASS_LOGGER, init=False)
    # queue to put visited items when visitor runs in background
    # items should be consumed by the generator
    queue: Optional[Queue] = field(default=None, init=False)

    def safe_enter(self) -> Self:
        if self.thread:
            self.thread_pool = self.ex.enter_context(
                ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"thread-{self.__class__.__name__}")
            )
            self.queue = Queue()
        return self

    def get_visitor(self, node: Node, prefix="visit_") -> Optional[Callable]:
        """Return the visitor function for this node or `None` if no visitor
        exists for this node.  In that case the generic visit function is
        used instead.
        """
        method = prefix + node.__class__.__name__
        return getattr(self, method, None)

    def run_visit(self, node: Node, *args, **kwargs) -> Optional[VisitedNode]:
        """Start visiting a node."""
        if self.thread:
            future = self.thread_pool.submit(self.visit, node, *args, **kwargs)

            def add_none_item(f: Future):
                self.queue.put(None)

            future.add_done_callback(add_none_item)
            # add callback to existack to check future for exceptions
            self.ex.callback(future.result)
            return None
        return self.visit(node, *args, **kwargs)

    def visit(self, node: Node, *args, **kwargs) -> VisitedNode:
        """Visit a node."""
        f = self.get_visitor(node)
        if f is not None:
            visited_node = f(node, *args, **kwargs)
        else:
            visited_node = self.generic_visit(node, *args, **kwargs)
        if self.queue:
            self.queue.put(visited_node)
        return visited_node

    def generic_visit(self, node: Node, *args, **kwargs) -> VisitedNode:
        """Called if no explicit visitor function exists for a node."""
        for node in node.iter_child_nodes():
            self.visit(node, *args, **kwargs)
        return VisitedNode(node, None)

    def as_gen(self) -> Generator[VisitedNode, None, None]:
        # iterate over queue while not None item received
        if self.queue is None:
            return
        while True:
            item = self.queue.get()
            if item is None:
                break
            yield item
