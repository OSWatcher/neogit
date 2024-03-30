# need to import hashlib._Hash
from __future__ import annotations

import hashlib
import os
from typing import Generator

from attrs import define
from more_itertools import consume

from ..model import FSDirectoryNode, FSFileNode, MerkleLabel, MerkleNode
from ..visitor import VisitedNode
from .visitor import MerkleVisitor


@define(auto_attribs=True)
class FSMerkleVisitor(MerkleVisitor):
    """Visitor to compute MerkleNode hash from FSNode"""

    def visit_FSFileNode(
        self, node: FSFileNode, hash_obj: hashlib._Hash, *args, **kwargs
    ) -> Generator[VisitedNode, None, None]:
        if node.path.is_symlink():
            # symlink, hash link target
            data: bytes = os.readlink(str(node.path)).encode()
            hash_obj.update(data)
        elif node.path.is_file():
            # file, hash content
            with open(node.path, "rb") as f:
                consume(hash_obj.update(chunk) for chunk in iter(lambda: f.read(4096), b""))
        else:
            # treat as empty file
            hash_obj.update(b"")
        # build merkle node and return it
        merkle_node = MerkleNode(hash=hash_obj.hexdigest(), label=MerkleLabel.Blob)
        yield VisitedNode(node=node, return_value=merkle_node)

    def visit_FSDirectoryNode(
        self, node: FSDirectoryNode, hash_obj: hashlib._Hash, *args, **kwargs
    ) -> Generator[VisitedNode, None, None]:
        # sort by 2 criterias
        # - dir first
        # - filename
        # "not e.path.is_dir" because False is inferior to True and will be sorted first
        merkle_children = {}
        for child_node in sorted(node.iter_child_nodes(), key=lambda e: (not e.path.is_dir(), e.path.name)):
            last_visited = None
            for visited_node in self.visit(child_node):
                yield visited_node
                last_visited = visited_node
            merkle_node = last_visited.return_value
            data = f"{child_node.path.name}{merkle_node.hash}\n".encode()
            hash_obj.update(data)
            merkle_children[child_node.path.name] = merkle_node
        # compute final hash for this dir
        merkle_node = MerkleNode(hash=hash_obj.hexdigest(), children=merkle_children, label=MerkleLabel.Tree)
        yield VisitedNode(node=node, return_value=merkle_node)
