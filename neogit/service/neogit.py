"""Contains main Neogit class"""
from pathlib import Path
from typing import Optional

from neogit.merkle.angela import MerkleFSTree
from neogit.merkle.hasher import Hasher
from neogit.model import Branch, Commit, Tree
from neogit.repo.abstract import AbstractGraphRepository

DEFAULT_BRANCH_NAME = "master"


class Neogit:
    def __init__(self, root: Path, repo: AbstractGraphRepository):
        self._root: Path = root
        if not self._root.exists():
            raise ValueError(f"Root directory {self._root} does not exist")
        self._repo = repo

    def commit(self, name: str):
        """Compute the Merkle TreeNode for the root directory and insert a new commit in the database"""
        builder = MerkleFSTree(self._root)
        root_tree: Tree = builder.merkelize()
        # get master branch, if it exists
        master_branch = Branch()
        master_branch.name = DEFAULT_BRANCH_NAME
        prev_commit: Optional[Commit] = None
        if self._repo.exists(master_branch):
            try:
                prev_commit = list(master_branch.commit)[0]
            except IndexError:
                raise RuntimeError("Branch has no commit")
        else:
            # if already has commits, inconsistent state
            # safety check
            assert not self._repo.match(Commit).exists(), "Inconsistent repo state detected. Branch node is missing"
        # create OS commit
        new_commit: Commit = Commit()
        new_commit.name = name
        new_commit.filesystem.add(root_tree, name="/")
        hasher = Hasher()
        new_commit.sha1sum = hasher.commit(new_commit).digest()
        if prev_commit is not None:
            new_commit.previous_commit.add(prev_commit)
        # save it
        self._repo.save(new_commit)
        # clear prev commit pointer and update it
        master_branch.commit.clear()
        master_branch.commit.add(new_commit)
        self._repo.save(master_branch)
