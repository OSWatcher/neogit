from neomodel import RelationshipTo, StringProperty, StructuredNode


class Commit(StructuredNode):
    name = StringProperty(required=True)
    sha1sum = StringProperty(required=True, unique_index=True)
    date = StringProperty(required=True)

    previous = RelationshipTo("Commit", "HAS_PREVIOUS")


class Branch(StructuredNode):
    name = StringProperty(required=True)
    tracks = RelationshipTo(Commit, "TRACKS_COMMIT")


class Blob(StructuredNode):
    sha1sum = StringProperty(required=True, unique_index=True)


class Tree(StructuredNode):
    sha1sum = StringProperty(required=True, unique_index=True)
    children_tree = RelationshipTo("Tree", "HAS_CHILD_TREE")
    children_blob = RelationshipTo(Blob, "HAS_CHILD_BLOB")
