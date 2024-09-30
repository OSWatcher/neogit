from datetime import datetime
from typing import Set

from neomodel import DateTimeProperty, RelationshipTo, StringProperty, StructuredNode, db

from neogit.merkle.hasher import Hasher

from .merkle import Tree
from enum import Enum, auto

class CommitCapabilities(Enum):
    Blob = auto()
    Tree = auto()
    MimeType = auto()
    WinRegKey = auto()
    WinRegValue = auto()


class Commit(StructuredNode):
    name = StringProperty(required=True)
    date = DateTimeProperty(required=True)
    hash = StringProperty(required=True, unique_index=True)
    sha1sum = StringProperty(required=True, unique_index=True)
    description = StringProperty()

    previous = RelationshipTo("Commit", "HAS_PREVIOUS")
    filesystem = RelationshipTo("Tree", "OWNS_FILESYSTEM")

    @classmethod
    def from_name(cls, name: str, filesystem_root: Tree, description: str = None):
        hasher = Hasher()
        date_now = datetime.now()
        commit_hash = hasher.commit(name, date_now.strftime("%Y-%m-%d %H:%M:%S"), filesystem_root.hash).digest()
        commit = cls(name=name, date=date_now, hash=commit_hash, sha1sum=commit_hash, description=description)
        # must save node before connecting it
        commit.save()
        commit.filesystem.connect(filesystem_root)
        return commit

    def get_capabilities(self) -> Set[CommitCapabilities]:
        query = """
        MATCH path=(c:Commit {hash: $commit_hash})-[*]->(n)
        WHERE NONE(rel IN relationships(path) WHERE type(rel) = 'HAS_PREVIOUS')
        WITH n, labels(n) AS labels_list
        UNWIND labels_list AS label
        RETURN COLLECT(DISTINCT label) AS uniqueLabels
        """.strip()
        result, _ = db.cypher_query(query, {"commit_hash": self.hash})
        label_set = set()
        for label in result[0][0]:
            label_set.add(CommitCapabilities[label])
        return label_set


class Branch(StructuredNode):
    name = StringProperty(required=True)

    tracks = RelationshipTo(Commit, "TRACKS_COMMIT")
