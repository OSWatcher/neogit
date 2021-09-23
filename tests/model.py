from neomodel import RelationshipTo, StringProperty, StructuredNode, StructuredRel


class HasChildRel(StructuredRel):
    name = StringProperty(required=True)


class Blob(StructuredNode):
    sha1sum = StringProperty(required=True, unique_index=True)


class Tree(StructuredNode):
    sha1sum = StringProperty(required=True, unique_index=True)
    children_tree = RelationshipTo("Tree", "HAS_CHILD_TREE", model=HasChildRel)
    children_blob = RelationshipTo(Blob, "HAS_CHILD_BLOB", model=HasChildRel)


class Commit(StructuredNode):
    name = StringProperty(required=True)
    sha1sum = StringProperty(required=True, unique_index=True)
    date = StringProperty(required=True)

    previous = RelationshipTo("Commit", "HAS_PREVIOUS")
    filesystem = RelationshipTo(Tree, "OWNS_FILESYSTEM")


class Branch(StructuredNode):
    name = StringProperty(required=True)
    tracks = RelationshipTo(Commit, "TRACKS_COMMIT")
