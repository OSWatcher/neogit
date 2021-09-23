from typing import Dict, Union

from neomodel import RelationshipTo, StringProperty, StructuredNode, StructuredRel


class HasChildRel(StructuredRel):
    name = StringProperty(required=True)


class Blob(StructuredNode):
    sha1sum = StringProperty(required=True, unique_index=True)


class Tree(StructuredNode):
    sha1sum = StringProperty(required=True, unique_index=True)
    children_tree = RelationshipTo("Tree", "HAS_CHILD_TREE", model=HasChildRel)
    children_blob = RelationshipTo(Blob, "HAS_CHILD_BLOB", model=HasChildRel)

    def asdict(self) -> Dict[str, Union[str, Dict]]:
        """Return a representation of the Tree as a dictionary"""
        content = {}
        for child_tree in self.children_tree:
            rel = self.children_tree.relationship(child_tree)
            content[rel.name] = {"sha1sum": child_tree.sha1sum, "content": child_tree.asdict()}
        for child_blob in self.children_blob:
            rel = self.children_blob.relationship(child_blob)
            content[rel.name] = child_blob.sha1sum
        return {"sha1sum": self.sha1sum, "content": content}


class Commit(StructuredNode):
    name = StringProperty(required=True)
    sha1sum = StringProperty(required=True, unique_index=True)
    date = StringProperty(required=True)

    previous = RelationshipTo("Commit", "HAS_PREVIOUS")
    filesystem = RelationshipTo(Tree, "OWNS_FILESYSTEM")


class Branch(StructuredNode):
    name = StringProperty(required=True)
    tracks = RelationshipTo(Commit, "TRACKS_COMMIT")
