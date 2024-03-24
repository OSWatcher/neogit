from datetime import datetime

from neomodel import DateTimeProperty, RelationshipTo, StringProperty, StructuredNode

from neogit.merkle.hasher import Hasher

from .merkle import Tree


class Commit(StructuredNode):
    name = StringProperty(required=True)
    date = DateTimeProperty(required=True)
    hash = StringProperty(required=True, unique_index=True)
    sha1sum = StringProperty(required=True, unique_index=True)

    previous = RelationshipTo("Commit", "HAS_PREVIOUS")
    filesystem = RelationshipTo("Tree", "OWNS_FILESYSTEM")

    @classmethod
    def from_name(cls, name: str, filesystem_root: Tree):
        hasher = Hasher()
        date_now = datetime.now()
        commit_hash = hasher.commit(name, date_now.strftime("%Y-%m-%d %H:%M:%S"), filesystem_root.hash).digest()
        commit = cls(name=name, date=date_now, hash=commit_hash, sha1sum=commit_hash)
        # must save node before connecting it
        commit.save()
        commit.filesystem.connect(filesystem_root)
        return commit


class Branch(StructuredNode):
    name = StringProperty(required=True)

    tracks = RelationshipTo(Commit, "TRACKS_COMMIT")
