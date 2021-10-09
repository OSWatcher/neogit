"""
Visitor design pattern

Taken from https://github.com/nodejs/node/blob/master/tools/inspector_protocol/jinja2/visitor.py (NodeJS)
"""

from functools import wraps
from typing import Callable, Optional

from neogit.core.model import Node


def visit_hook(f):
    """Add pre/post hook on node visit"""

    @wraps(f)
    def wrapper(self, node: Node, *args, **kwargs):
        # call pre_visit hook, if any
        pre_method_name = f"pre_visit_{node.__class__.__name__}"
        pre_visit_f = getattr(self, pre_method_name, None)
        if pre_visit_f:
            pre_visit_f(node, *args, **kwargs)
        # call main func
        # this func needs self
        visit_ret_val = f(self, node, *args, **kwargs)
        # call post_visit hook, if any
        post_method_name = f"post_visit_{node.__class__.__name__}"
        post_visit_f = getattr(self, post_method_name, None)
        if post_visit_f:
            post_visit_f(node, visit_ret_val, *args, **kwargs)
        return visit_ret_val

    return wrapper


class NodeVisitor(object):
    """Walks the abstract syntax tree and call visitor functions for every
    node found.  The visitor functions may return values which will be
    forwarded by the `visit` method.
    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `get_visitor` function.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.
    """

    def get_visitor(self, node: Node) -> Optional[Callable]:
        """Return the visitor function for this node or `None` if no visitor
        exists for this node.  In that case the generic visit function is
        used instead.
        """
        method = "visit_" + node.__class__.__name__
        return getattr(self, method, None)

    @visit_hook
    def visit(self, node: Node, *args, **kwargs):
        """Visit a node."""
        f = self.get_visitor(node)
        if f is not None:
            return f(node, *args, **kwargs)
        return self.generic_visit(node, *args, **kwargs)

    def generic_visit(self, node: Node, *args, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        for node in node.iter_child_nodes():
            self.visit(node, *args, **kwargs)
