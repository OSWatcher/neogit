"""Contains main Neogit class"""
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional

from neo4j import GraphDatabase, Transaction
from neo4j.exceptions import ClientError

from neogit.config import settings
from neogit.merkle.angela import MerkleFSTree
from neogit.merkle.hasher import Hasher
from neogit.model import Branch, Commit, Tree


def measure_time(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        start = datetime.now()
        res = method(self, *args, **kwargs)
        end = datetime.now()
        self._log.debug("%s execution time: %s", method.__name__, end - start)
        return res

    return wrapper


class Neogit:
    def __init__(self, root: Path):
        self._log = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._root: Path = root
        self._driver = GraphDatabase.driver(settings.neo4j.url)
        if not self._root.exists():
            raise ValueError(f"Root directory {self._root} does not exist")

    @measure_time
    def _build_merkle_tree(self) -> Tree:
        builder = MerkleFSTree(self._root)
        return builder.merkelize()

    @measure_time
    def _insert_fileystem(self, root: Tree, transaction: Transaction):
        root.create(transaction)

    def _commit_transaction(self, name: str, tx):
        root_tree: Tree = self._build_merkle_tree()
        # test branch
        branch = Branch(tx, settings.branch)
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
        self._insert_fileystem(root_tree, tx)
        # add filesystem
        new_commit.add_filesystem(root_tree)
        # add previous if exists
        if prev_commit:
            new_commit.add_previous(prev_commit)
        # update branch
        branch.set_os_commit(new_commit)

    def init(self):
        """Initialize a neogit repository by creating indexes and constraints"""
        with self._driver.session() as session:
            constraints = {"Blob": "sha1sum", "Tree": "sha1sum", "Commit": "sha1sum", "Branch": "name"}
            for label, unique_prop in constraints.items():
                try:
                    session.run(f"CREATE CONSTRAINT ON (n:{label}) ASSERT n.{unique_prop} IS UNIQUE")
                except ClientError as e:
                    if e.code == "Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists":
                        continue

    @measure_time
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
