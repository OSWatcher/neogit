import hashlib

from more_itertools import consume

from neogit.core.model import FSDirectoryNode, FSFileNode, MerkleLabel, MerkleNode
from neogit.core.visitor import NodeVisitor


class MerkleVisitor(NodeVisitor):
    """Visit a Node and build a MerkleTree"""

    def visit_FSFileNode(self, node: FSFileNode, *args, **kwargs) -> MerkleNode:
        hash_obj = hashlib.sha1()
        # iterate on the hashable bytes data and update the hash
        consume(map(lambda data: hash_obj.update(data), node.hashable_data()))
        # build merkle node and return it
        merkle_node = MerkleNode(hash=hash_obj.hexdigest(), label=MerkleLabel.Blob)
        return merkle_node

    def visit_FSDirectoryNode(self, node: FSDirectoryNode, *args, **kwargs) -> MerkleNode:
        hash_obj = hashlib.sha1()
        # sort by 2 criterias
        # - dir first
        # - filename
        # "not e.path.is_dir" because False is inferior to True and will be sorted first
        merkle_children = {}
        for child_node in sorted(node.iter_child_nodes(), key=lambda e: (not e.path.is_dir(), e.path.name)):
            merkle_node = self.visit(child_node)
            data = f"{child_node.path.name}{merkle_node.hash}\n".encode()
            hash_obj.update(data)
            merkle_children[child_node.path.name] = merkle_node
        # compute final hash for this dir
        merkle_node = MerkleNode(hash=hash_obj.hexdigest(), children=merkle_children, label=MerkleLabel.Tree)
        return merkle_node
