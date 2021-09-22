from neomodel import StructuredNode, StringProperty, DateTimeProperty, RelationshipTo


class Commit(StructuredNode):
    name = StringProperty(required=True)
    sha1sum = StringProperty(required=True, unique_index=True)
    date = DateTimeProperty()


class Branch(StructuredNode):
    name = StringProperty(required=True)
    tracks = RelationshipTo(Commit, "TRACKS_COMMIT")
