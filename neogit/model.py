from dataclasses import dataclass
from typing import Dict

from py2neo.ogm import Model, Property, RelatedTo


@dataclass(init=False)
class Blob:
    sha1sum: str


@dataclass(init=False)
class Tree:
    sha1sum: str
    children_blob: Dict[str, Blob]
    children_tree: Dict[str, "Tree"]

    def __init__(self):
        self.children_tree = {}
        self.children_blob = {}


class Commit(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()
    name = Property()
    filesystem = RelatedTo("Tree", "HAS_FILESYSTEM")
    previous_commit = RelatedTo("Commit", "HAS_PREVIOUS_COMMIT")


class Branch(Model):
    __primarykey__ = "name"

    name = Property()
    commit = RelatedTo("Commit", "TRACKS_COMMIT")
