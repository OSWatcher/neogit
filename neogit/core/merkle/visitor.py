# need to import hashlib._Hash
from __future__ import annotations

import hashlib

from attrs import define

from neogit.core.model.node import Node
from neogit.core.visitor import NodeVisitor


@define(auto_attribs=True)
class MerkleVisitor(NodeVisitor):

    # override visit method to define hashing algorithm
    def visit(self, node: Node, *args, **kwargs):
        # configure hashing algorithm here
        hash_obj = hashlib.sha1()
        return super().visit(node, hash_obj, *args, **kwargs)
