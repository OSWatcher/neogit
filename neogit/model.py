import os
from dataclasses import dataclass
from typing import Dict, Union

PathLike = Union[str, bytes, os.PathLike]


@dataclass(init=False)
class BlobNode:
    sha1sum: str


@dataclass(init=False)
class TreeNode:
    sha1sum: str
    children: Dict[str, Union[BlobNode, "TreeNode"]]

    def __init__(self):
        self.children = {}
