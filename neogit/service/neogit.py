"""Contains main Neogit class"""
from pathlib import Path

from neogit.merkle.angela import MerkleFSTree
from neogit.merkle.hasher import Hasher
from neogit.model import CommitNode, TreeNode
from neogit.repo.abstract import AbstractGraphRepository


class Neogit:
    def __init__(self, root: Path, repo: AbstractGraphRepository):
        self._root: Path = root
        self._repo = repo
        if not self._root.exists():
            raise ValueError(f"Root directory {self._root} does not exist")

    def commit(self, name: str):
        """Compute the Merkle TreeNode for the root directory and insert a new commit in the database"""
        builder = MerkleFSTree(self._root)
        root_tree: TreeNode = builder.merkelize()
        # create OS commit
        commit_node: CommitNode = CommitNode()
        commit_node.name = name
        commit_node.filesystem = root_tree
        hasher = Hasher()
        commit_node.sha1sum = hasher.commit(commit_node).digest()
        # TODO: get last commit
        # commit_node.last_commit
