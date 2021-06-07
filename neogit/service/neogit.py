"""Contains main Neogit class"""
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path, PurePath
from typing import Iterator, Optional, Type, Union, List, Dict

from neo4j import GraphDatabase, Transaction
from neo4j.exceptions import ClientError

from neogit.config import ObjectConfig, settings
from neogit.console import EmptyConsoleAdapter, RichConsoleAdapter
from neogit.diff import diff_trees
from neogit.merkle.angela import MerkleFSTree
from neogit.merkle.hasher import Hasher
from neogit.model import Branch, Commit, Tree
from neogit.object_storage import ContainerAlreadyExists, LibcloudObjectStorage, TSObjectStorage


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
    def __init__(self, gui_enabled: bool = False):
        """Initializes a Neogit instance, connects to Neo4j DB and Object Storage"""
        self._log = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._gui_enabled = gui_enabled
        self._graph_driver = GraphDatabase.driver(settings.neo4j.url, auth=settings.neo4j.creds)
        object_config = ObjectConfig.from_settings(settings)
        self._object_driver_ts = TSObjectStorage(LibcloudObjectStorage, object_config)
        self._object_driver = self._object_driver_ts.instance

    def iter_commit(self) -> Iterator[Commit]:
        """Enumerate all commits in the database"""
        with self._graph_driver.session() as session:
            yield from Commit.iter(session)

    def get_commit(self, sha1sum: str) -> Optional[Commit]:
        """Retrieve a specific commit from the database"""
        with self._graph_driver.session() as session:
            return Commit.get(session, sha1sum)

    def list_filesystem_at(self, os_sha1_list: List[str], fs_path: PurePath) -> Dict[str, Tree]:
        """List the filesystem entries at fs_path for a specific OS sha1sum"""
        with self._graph_driver.session() as session:
            target_tree_list: Dict[str, Tree] = {}
            for os_sha1 in os_sha1_list:
                commit: Optional[Commit] = Commit.get(session, os_sha1)
                if not commit:
                    raise RuntimeError("Commit not found")
                root_tree = commit.owns_filesystem()
                # ['/', 'Program Files', 'Microsoft', ...]
                # -> ['Program Files', 'Microsoft', ...]
                cur_tree = root_tree
                for path_part in fs_path.parts[1:]:
                    # get next tree
                    cur_tree = cur_tree.has_child_tree(session, path_part)
                target_tree_list[os_sha1] = cur_tree
            for os_sha1, tree in target_tree_list.items():
                tree.get_children(session)
            # get children
            return target_tree_list

    @measure_time
    def _build_tree_and_insert(self, root: Path, transaction: Transaction):
        console_cls: Union[Type[EmptyConsoleAdapter], Type[RichConsoleAdapter]] = EmptyConsoleAdapter
        if self._gui_enabled:
            console_cls = RichConsoleAdapter
        with console_cls() as console:
            builder = MerkleFSTree(root, self._object_driver_ts, console)
            for tree in builder.merkelize():
                tree.create_partial(transaction)
            return builder.root_tree

    def _commit_transaction(self, name: str, root: Path, tx):
        root_tree: Tree = self._build_tree_and_insert(root, tx)
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
        # add filesystem
        new_commit.add_filesystem(root_tree)
        # add previous if exists
        if prev_commit:
            new_commit.add_previous(prev_commit)
        # update branch
        branch.set_os_commit(new_commit)

    def init(self):
        """Initialize a neogit repository by creating indexes and constraints"""
        with self._graph_driver.session() as session:
            constraints = {"Blob": "sha1sum", "Tree": "sha1sum", "Commit": "sha1sum", "Branch": "name"}
            for label, unique_prop in constraints.items():
                try:
                    self._log.debug("Graph: creating unique contraint on %s:%s", label, unique_prop)
                    session.run(f"CREATE CONSTRAINT ON (n:{label}) ASSERT n.{unique_prop} IS UNIQUE")
                except ClientError as e:
                    if e.code == "Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists":
                        continue
        self._log.info("Graph: created unique constraints")
        # init object storage container
        container_name = settings.object.container_name
        try:
            self._log.debug("Object: creating container '%s'", container_name)
            self._object_driver.create_container(container_name)
        except ContainerAlreadyExists:
            pass
        self._log.info("Object: created container: '%s'", container_name)

    @measure_time
    def commit(self, name: str, root: Path):
        """Compute the Merkle TreeNode for the root directory and insert a new commit in the database"""
        if not root.exists():
            raise ValueError(f"Root directory {root} does not exist")
        with self._graph_driver.session() as session:
            tx = session.begin_transaction()
            try:
                self._commit_transaction(name, root, tx)
            except Exception:
                # rollback transaction
                tx.rollback()
                raise
            else:
                tx.commit()

    def log(self):
        branch_name: str = settings.branch
        with self._graph_driver.session() as session:
            branch = Branch(session, branch_name)
            if not branch:
                raise RuntimeError(f"Branch {branch_name} not found")

            # get last commit
            commit: Optional[Commit] = branch.os_commit

    def diff(self, ref1: str, ref2: str):
        # check if both refs exists
        with self._graph_driver.session() as session:
            ref1_tree_sha1 = Commit.get_tree_sha1_from_commit_sha1(session, ref1)
            ref2_tree_sha1 = Commit.get_tree_sha1_from_commit_sha1(session, ref2)
            yield from diff_trees(session, ref1_tree_sha1, ref2_tree_sha1)
