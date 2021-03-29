from dataclasses import dataclass
from typing import Optional

from py2neo.ogm import Model, Property, RelatedTo


class BlobNode(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()


class TreeNode(Model):
    __primarykey__ = "sha1sum"

    sha1sum = Property()
    children_blobs = RelatedTo("BlobNode", "HAS_CHILD_BLOB")
    children_trees = RelatedTo("TreeNode", "HAS_CHILD_TREE")


@dataclass(init=False)
class CommitNode:
    sha1sum: str
    name: str
    filesystem: TreeNode
    last_commit: Optional["CommitNode"]


@dataclass(init=False)
class BranchNode:
    name: str
    commit: CommitNode
