from neomodel import RelationshipTo, StringProperty, StructuredNode


class Commit(StructuredNode):
    name = StringProperty(required=True)
    sha1sum = StringProperty(required=True, unique_index=True)
    date = StringProperty(required=True)

    previous = RelationshipTo("Commit", "HAS_PREVIOUS")


class Branch(StructuredNode):
    name = StringProperty(required=True)
    tracks = RelationshipTo(Commit, "TRACKS_COMMIT")
