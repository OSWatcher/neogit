# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from enum import Enum, auto
from typing import Iterator, Optional, Set

from neomodel import DateTimeNeo4jFormatProperty, RelationshipTo, StringProperty, StructuredNode, db

from neogit.merkle.hasher import Hasher

from .merkle import Tree


class CommitCapabilities(Enum):
    Blob = auto()
    Tree = auto()
    MimeType = auto()
    WinRegKey = auto()
    WinRegValue = auto()


class Commit(StructuredNode):
    name = StringProperty(required=True)
    date = DateTimeNeo4jFormatProperty(required=True)
    hash = StringProperty(required=True, unique_index=True)
    sha1sum = StringProperty(required=True, unique_index=True)
    description = StringProperty()

    previous = RelationshipTo("Commit", "HAS_PREVIOUS")
    filesystem = RelationshipTo("Tree", "OWNS_FILESYSTEM")
    plugin = RelationshipTo("PluginRun", "HAS_PLUGIN_RUN")

    @classmethod
    def from_name(
        cls, name: str, filesystem_root: Tree, description: Optional[str] = None, date: Optional[datetime] = None
    ):
        """Create a new commit from a name and filesystem tree.

        Args:
            name: Commit name/identifier
            filesystem_root: Root Tree node of the filesystem
            description: Optional commit description
            date: Optional timezone-aware commit date. If None, uses datetime.now(timezone.utc).
                  Must have tzinfo set (e.g., datetime(2024,1,1,12,0,0,tzinfo=timezone.utc))

        Returns:
            Newly created Commit instance

        Raises:
            ValueError: If date is provided without timezone information (naive datetime)
        """
        hasher = Hasher()
        # Ensure timezone-aware datetime (UTC by default)
        if date is None:
            date_now = datetime.now(timezone.utc)
        else:
            if date.tzinfo is None:
                raise ValueError(
                    "date parameter must be timezone-aware. "
                    "Use datetime.now(timezone.utc) or provide a timezone: "
                    "date.replace(tzinfo=timezone.utc)"
                )
            date_now = date
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


class PluginRun(StructuredNode):
    """A node to represents which plugins have been run on a commit"""

    filetype = DateTimeNeo4jFormatProperty()
    winreg = DateTimeNeo4jFormatProperty()
    symbols = DateTimeNeo4jFormatProperty()


class Branch(StructuredNode):
    name = StringProperty(required=True)

    tracks = RelationshipTo(Commit, "TRACKS_COMMIT")

    def iter_commits(self) -> Iterator[Commit]:
        commit = self.tracks.single()
        while commit:
            yield commit
            commit = commit.previous.single()

    def commit_exists(self, commit_name: str) -> Optional[Commit]:
        found = [commit for commit in self.iter_commits() if commit_name == commit.name]
        if len(found) > 1:
            raise ValueError(f"Multiple commits with name {commit_name} found in branch {self.name}")
        return found[0] if found else None
