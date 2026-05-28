# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

"""
Domain model objects
"""
import typing
from abc import ABC
from typing import Iterator

from attrs import define

if typing.TYPE_CHECKING:
    from neogit.core.visitor import NodeVisitor


@define(auto_attribs=True)
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
