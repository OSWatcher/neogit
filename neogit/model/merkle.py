# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from pathlib import PurePath
from typing import Dict, Generator, Tuple, Union

from neo4j import Session, Transaction
from neomodel import DoesNotExist, RelationshipTo, StringProperty, StructuredNode, StructuredRel, db

from neogit.core.model import MerkleLabel, MerkleNode


class HasChildRel(StructuredRel):
    """HAS_CHILD relationship"""

    """filename"""
    name = StringProperty(required=True)


class BaseMerkleNode(StructuredNode):
    """A simple abstract class to put common properties between Blobs and Trees"""

    __abstract_node__ = True
    hash = StringProperty(unique_index=True, required=True)
    sha1sum = StringProperty(unique_index=True, required=True)


class Blob(BaseMerkleNode):
    pass


class Tree(BaseMerkleNode):
    children_blob = RelationshipTo(Blob, "HAS_CHILD_BLOB", model=HasChildRel)
    children_tree = RelationshipTo("Tree", "HAS_CHILD_TREE", model=HasChildRel)

    @classmethod
    def create_from_merkle_node_neomodel(cls, node: MerkleNode) -> "Tree":
        """Build a Tree from a MerkleNode"""
        try:
            tree = cls._cached_retrieve_merkle_node(node.hash, node.label)
        except DoesNotExist:
            tree = cls(hash=node.hash)
            # the tree must be saved before connecting any nodes
            tree.save()
            # separate trees from blobs
            child_blobs = {
                child_name: child_node
                for child_name, child_node in node.children.items()
                if child_node.label == MerkleLabel.Blob
            }
            child_trees = {
                child_name: child_node
                for child_name, child_node in node.children.items()
                if child_node.label == MerkleLabel.Tree
            }
            # create children blobs
            blob_props = [{"hash": child_blob.hash} for child_blob in child_blobs.values()]
            Blob.get_or_create(props=blob_props, relationship=tree.children_blob)
            # create children trees
            tree_props = [{"hash": child_tree.hash for child_tree in child_trees.values()}]
            cls.get_or_create(props=tree_props, relationship=tree.children_tree)
        return tree

    @classmethod
    @lru_cache(maxsize=1024)
    def _cached_retrieve_merkle_node(cls, hash: str, label: MerkleLabel):
        if label == MerkleLabel.Blob:
            return Blob.nodes.get(hash=hash)
        elif label == MerkleLabel.Tree:
            return Tree.nodes.get(hash=hash)
        else:
            raise NotImplementedError

    @classmethod
    def create_from_merkle_node_neomodel_cypher(cls, node: MerkleNode):
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

    @classmethod
    def create_from_merkle_node_cypher(cls, session: Union[Session, Transaction], node: MerkleNode):
        """Create the Tree using a session or transaction from the neo4j driver"""
        query = """
        MERGE (p:Tree {hash: $hash, sha1sum: $hash})
        WITH p
        FOREACH (blob IN $blob_hashes |
            MERGE (b:Blob {hash: blob.hash, sha1sum: blob.hash})
            MERGE (p)-[:HAS_CHILD_BLOB {name: blob.name}]->(b)
        )
        FOREACH (tree IN $tree_hashes |
            MERGE (t:Tree {hash: tree.hash, sha1sum: tree.hash})
            MERGE (p)-[:HAS_CHILD_TREE {name: tree.name}]->(t)
        )
        """
        blob_hashes = [
            {"hash": n.hash, "name": filename} for filename, n in node.children.items() if n.label == MerkleLabel.Blob
        ]
        tree_hashes = [
            {"hash": n.hash, "name": filename} for filename, n in node.children.items() if n.label == MerkleLabel.Tree
        ]
        session.run(query, {"hash": node.hash, "blob_hashes": blob_hashes, "tree_hashes": tree_hashes})

    def all_blobs(self) -> Generator[Tuple[PurePath, Blob], None, None]:
        """Retrieve all Blobs under this Tree, at any depth"""
        # bug: https://github.com/neo4j/neo4j/issues/13483
        # need to add Commit in the MATCH pattern, otherwise the query will return nothing (cartesian product)
        query = """
        MATCH (c:Commit)-[:OWNS_FILESYSTEM]->(t:Tree)
        WHERE t.hash = $root_hash
        WITH t
        MATCH path = (t:Tree)-[:HAS_CHILD_BLOB|HAS_CHILD_TREE*]->(b:Blob)
        RETURN [rel IN relationships(path) | rel.name] AS parts, b
        """
        rows, _ = self.cypher(query, {"root_hash": self.hash})
        for row in rows:
            # skip the first element of the parts list, which is the null value from OWNS_FILESYSTEM
            yield PurePath(*row[0]), Blob.inflate(row[1])

    def list_children(self) -> list[str]:
        """Return list of child names (both trees and blobs)."""
        child_names = []

        # Get blob children names
        for blob in self.children_blob.all():
            rel = self.children_blob.relationship(blob)
            child_names.append(rel.name)

        # Get tree children names
        for tree in self.children_tree.all():
            rel = self.children_tree.relationship(tree)
            child_names.append(rel.name)

        return sorted(child_names)

    def iter_children(self) -> Generator[Tuple[str, Union["Tree", Blob]], None, None]:
        """Iterate over all children (trees and blobs) with their names."""
        for blob in self.children_blob.all():
            rel = self.children_blob.relationship(blob)
            yield rel.name, blob

        for tree in self.children_tree.all():
            rel = self.children_tree.relationship(tree)
            yield rel.name, tree

    def get_child_at_path(self, path: PurePath) -> Union["Tree", Blob]:
        """Return the child (tree or blob) at the specified path."""
        idx = 1 if path.is_absolute() else 0
        path_parts = path.parts[idx:]

        if not path_parts:
            return self

        # Navigate to parent directory using cypher for efficiency
        tree_parts = path_parts[:-1]
        cur_tree = self
        for tree_part in tree_parts:
            query = """
            MATCH (p:Tree)-[r:HAS_CHILD_TREE]->(c:Tree)
            WHERE p.hash = $parent_hash
                AND r.name = $filename
            RETURN c
            """
            rows, _ = self.cypher(query, {"parent_hash": cur_tree.hash, "filename": tree_part})
            try:
                node = rows[0][0]
            except IndexError:
                raise FileNotFoundError(f"Tree not found: {tree_part}")
            else:
                cur_tree = Tree.inflate(node)

        # Get final child (blob or tree)
        filename = path_parts[-1]

        # Try blob first
        query = """
        MATCH (p:Tree)-[r:HAS_CHILD_BLOB]->(c:Blob)
        WHERE p.hash = $parent_hash
            AND r.name = $filename
        RETURN c
        """
        rows, _ = self.cypher(query, {"parent_hash": cur_tree.hash, "filename": filename})
        if rows:
            return Blob.inflate(rows[0][0])

        # Try tree
        query = """
        MATCH (p:Tree)-[r:HAS_CHILD_TREE]->(c:Tree)
        WHERE p.hash = $parent_hash
            AND r.name = $filename
        RETURN c
        """
        rows, _ = self.cypher(query, {"parent_hash": cur_tree.hash, "filename": filename})
        if rows:
            return Tree.inflate(rows[0][0])

        raise FileNotFoundError(f"Child not found: {filename}")

    def get_tree_at_path(self, path: PurePath) -> "Tree":
        """Return the tree at the specified path."""
        child = self.get_child_at_path(path)
        if not isinstance(child, Tree):
            raise FileNotFoundError(f"Path is not a tree: {path}")
        return child

    def get_blob_at_path(self, path: PurePath) -> Blob:
        """Return the blob at the specified path"""
        child = self.get_child_at_path(path)
        if not isinstance(child, Blob):
            raise FileNotFoundError(f"Path is not a blob: {path}")
        return child

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
