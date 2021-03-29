from dataclasses import dataclass
from typing import Dict, Optional, Union


@dataclass(init=False)
class BlobNode:
    sha1sum: str


@dataclass(init=False)
class TreeNode:
    sha1sum: str
    children: Dict[str, Union[BlobNode, "TreeNode"]]

    def __init__(self):
        self.children = {}


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
