from typing import Dict, Union

from neomodel import RelationshipTo, StringProperty, StructuredNode, StructuredRel, db

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
    def create_from_merkle_node(cls, node: MerkleNode):
        """Build a Tree from a MerkleNode"""
        cls._create_child_blobs(node)
        cls._create_child_trees(node)
        # create parent
        query = """
        MERGE (p:Tree {hash: $hash})
        """
        db.cypher_query(query, {"hash": node.hash})
        cls._create_blob_relationship(node)
        cls._create_tree_relationship(node)

    @classmethod
    def _create_child_blobs(cls, node: MerkleNode):
        """Create child Blobs"""
        # create child blobs
        query = """
        UNWIND $unwind_param as blob_hash
        MERGE (b:Blob {hash: blob_hash})
        """
        blob_list = [child_node.hash for child_node in node.children.values() if child_node.label == MerkleLabel.Blob]
        db.cypher_query(query, {"unwind_param": blob_list})

    @classmethod
    def _create_child_trees(cls, node: MerkleNode):
        """Create child Trees"""
        # create child trees
        query = """
        UNWIND $unwind_param as tree_hash
        MERGE (t:Tree {hash: tree_hash})
        """
        tree_list = [child_node.hash for child_node in node.children.values() if child_node.label == MerkleLabel.Tree]
        db.cypher_query(query, {"unwind_param": tree_list})

    @classmethod
    def _create_blob_relationship(cls, node: MerkleNode):
        # create blob relationship
        # [{"name": "xxx", "hash: "xxxx"
        rel_list = [
            {"name": filename, "hash": child_node.hash}
            for filename, child_node in node.children.items()
            if child_node.label == MerkleLabel.Blob
        ]
        query = """
        MATCH (p:Tree {hash: $parent_hash})
        WITH p
        UNWIND $unwind_param as rel
        MATCH (c:Blob {hash: rel.hash})
        MERGE (p)-[:HAS_CHILD_BLOB {name: rel.name}]->(c)
        """
        db.cypher_query(query, {"parent_hash": node.hash, "unwind_param": rel_list})

    @classmethod
    def _create_tree_relationship(cls, node: MerkleNode):
        # create Tree relationship
        rel_list = [
            {"name": filename, "hash": child_node.hash}
            for filename, child_node in node.children.items()
            if child_node.label == MerkleLabel.Tree
        ]
        query = """
        MATCH (p:Tree {hash: $parent_hash})
        WITH p
        UNWIND $unwind_param as rel
        MATCH (c:Tree {hash: rel.hash})
        MERGE (p)-[:HAS_CHILD_TREE {name: rel.name}]->(c)
        """
        db.cypher_query(query, {"parent_hash": node.hash, "unwind_param": rel_list})

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
