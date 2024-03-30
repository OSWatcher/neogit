# need to import hashlib._Hash
from __future__ import annotations

import hashlib

from neogit.core.model.node import Node
from neogit.core.visitor import NodeVisitor


class MerkleVisitor(NodeVisitor):

    # override visit method to define hashing algorithm
    def visit(self, node: Node, *args, **kwargs):
        # configure hashing algorithm here
        hash_obj = hashlib.sha1()
        return super().visit(node, hash_obj, *args, **kwargs)
