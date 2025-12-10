# need to import hashlib._Hash
from __future__ import annotations

import hashlib
import logging
import os

from attrs import define

from ..model import FSDirectoryNode, FSFileNode, MerkleLabel, MerkleNode
from ..visitor import VisitedNode
from .visitor import MerkleVisitor

logger = logging.getLogger(__name__)


def _safe_is_dir_key(node):
    """
    Safe sorting key that handles I/O errors from FUSE mounts.

    Returns tuple (is_file, name) for sorting directories before files.
    On OSError, treats entry as a file and logs warning.
    """
    try:
        return (not node.path.is_dir(), node.path.name)
    except OSError as e:
        logger.warning("SKIP is_dir check: %s (%s)", node.path, e)
        return (True, node.path.name)  # Treat as file


@define(auto_attribs=True)
class FSMerkleVisitor(MerkleVisitor):
    """Visitor to compute MerkleNode hash from FSNode"""

    def visit_FSFileNode(self, node: FSFileNode, hash_obj: hashlib._Hash, *args, **kwargs) -> VisitedNode:
        if node.path.is_symlink():
            # symlink, hash link target
            data: bytes = os.readlink(str(node.path)).encode()
            hash_obj.update(data)
        elif node.path.is_file():
            # file, hash content
            with open(node.path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
        else:
            # treat as empty file
            hash_obj.update(b"")
        # build merkle node and return it
        merkle_node = MerkleNode(hash=hash_obj.hexdigest(), label=MerkleLabel.Blob)
        return VisitedNode(node=node, return_value=merkle_node)

    def visit_FSDirectoryNode(self, node: FSDirectoryNode, hash_obj: hashlib._Hash, *args, **kwargs) -> VisitedNode:
        # sort by 2 criterias
        # - dir first
        # - filename
        # "not e.path.is_dir" because False is inferior to True and will be sorted first
        merkle_children = {}
        for child_node in sorted(node.iter_child_nodes(), key=_safe_is_dir_key):
            child_visited_node = self.visit(child_node)
            merkle_node = child_visited_node.return_value
            data = f"{child_node.path.name}{merkle_node.hash}\n".encode()
            hash_obj.update(data)
            merkle_children[child_node.path.name] = merkle_node
        # compute final hash for this dir
        merkle_node = MerkleNode(hash=hash_obj.hexdigest(), children=merkle_children, label=MerkleLabel.Tree)
        return VisitedNode(node=node, return_value=merkle_node)
