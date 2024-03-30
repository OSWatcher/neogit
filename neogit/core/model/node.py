"""
Domain model objects
"""
import typing
from abc import ABC
from typing import Any, Dict, Iterator

import attr

if typing.TYPE_CHECKING:
    from neogit.core.visitor import NodeVisitor


@attr.s
class RelationshipTo:
    """Oriented relationship between two nodes"""

    name: str = attr.ib()
    start_node: "Node" = attr.ib()
    end_node: "Node" = attr.ib()
    properties: Dict[str, Any] = attr.ib(factory=dict)


@attr.s
class Node(ABC):
    """Basic node representation"""

    def iter_child_nodes(self) -> Iterator["Node"]:
        yield from ()

    def is_leaf(self) -> bool:
        try:
            next(self.iter_child_nodes())
        except StopIteration:
            return False
        else:
            return True

    def accept(self, v: "NodeVisitor"):
        """Accepts a visitor"""
        v.visit(self)
