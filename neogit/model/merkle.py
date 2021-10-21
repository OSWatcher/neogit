from typing import Dict, Union

from neomodel import RelationshipTo, StringProperty, StructuredNode, StructuredRel

from neogit.core.model import MerkleLabel, MerkleNode


class HasChildRel(StructuredRel):
    """HAS_CHILD relationship"""

    """filename"""
    name = StringProperty(required=True)


class BaseMerkleNode(StructuredNode):
    """A simple abstract class to put common properties between Blobs and Trees"""

    __abstract_node__ = True
    hash = StringProperty(unique_index=True, required=True)


class Blob(BaseMerkleNode):
    pass


class Tree(BaseMerkleNode):
    children_blob = RelationshipTo(Blob, "HAS_CHILD_BLOB", model=HasChildRel)
    children_tree = RelationshipTo("Tree", "HAS_CHILD_TREE", model=HasChildRel)

    @classmethod
    def from_merkle_node(cls, node: MerkleNode) -> "Tree":
        """Build a Tree from a MerkleNode"""
        try:
            tree = cls.nodes.get(hash=node.hash)
        except Tree.DoesNotExist:
            tree = cls(hash=node.hash)
        # save the tree before connecting any nodes to it
        tree.save()
        # retrieve children
        for child_name, child_node in node.children.items():
            rel_properties = {"name": child_name}
            if child_node.label == MerkleLabel.Blob:
                # Blob
                child_neo_node = Blob.nodes.get(hash=child_node.hash)
                tree.children_blob.connect(child_neo_node, rel_properties)
            elif child_node.label == MerkleLabel.Tree:
                # Tree
                child_neo_node = Tree.nodes.get(hash=child_node.hash)
                tree.children_tree.connect(child_neo_node, rel_properties)
            else:
                raise NotImplementedError
        return tree

    def asdict(self) -> Dict[str, Union[str, Dict]]:
        """Return a representation of the Tree as a dictionary"""
        content = {}
        for child_tree in self.children_tree:
            rel = self.children_tree.relationship(child_tree)
            content[rel.name] = {"hash": child_tree.hash, "content": child_tree.asdict()}
        for child_blob in self.children_blob:
            rel = self.children_blob.relationship(child_blob)
            content[rel.name] = child_blob.hash
        return {"hash": self.hash, "content": content}
