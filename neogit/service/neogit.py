"""Contains main Neogit class"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from neo4j import GraphDatabase

from neogit.merkle.angela import MerkleFSTree
from neogit.merkle.hasher import Hasher
from neogit.model import Branch, Commit, Tree

DEFAULT_BRANCH_NAME = "master"
DEFAULT_URL = "bolt://localhost:7687"


class Neogit:
    def __init__(self, root: Path):
        self._root: Path = root
        self._driver = GraphDatabase.driver(DEFAULT_URL)
        if not self._root.exists():
            raise ValueError(f"Root directory {self._root} does not exist")

    def _commit_transaction(self, name: str, tx):
        builder = MerkleFSTree(self._root)
        root_tree: Tree = builder.merkelize()
        # test branch
        branch = Branch(tx, DEFAULT_BRANCH_NAME)
        if not branch:
            logging.debug("Creating branch: %s", branch.name)
            branch.create()
        # get previous commit
        prev_commit: Optional[Commit] = branch.os_commit
        # compute new commit digest
        hasher = Hasher()
        commit_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_commit_sha1sum = hasher.commit(name, commit_date, root_tree).digest()
        # create OS commit
        new_commit: Commit = Commit(tx, name, new_commit_sha1sum, commit_date)
        new_commit.create()
        # create filesystem tree
        root_tree.create(tx)
        # add filesystem
        new_commit.add_filesystem(root_tree)
        # add previous if exists
        if prev_commit:
            new_commit.add_previous(prev_commit)
        # update branch
        branch.set_os_commit(new_commit)

    def commit(self, name: str):
        """Compute the Merkle TreeNode for the root directory and insert a new commit in the database"""
        with self._driver.session() as session:
            tx = session.begin_transaction()
            try:
                self._commit_transaction(name, tx)
            except Exception:
                # rollback transaction
                tx.rollback()
                raise
            else:
                tx.commit()
