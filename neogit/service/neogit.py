"""Contains main Neogit class"""
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path, PurePath
from typing import Dict, Iterator, List, Optional, Type, Union

from neo4j import GraphDatabase, Transaction
from neo4j.exceptions import ClientError

from neogit.config import settings
from neogit.console import EmptyConsoleAdapter, RichConsoleAdapter
from neogit.diff import diff_trees
from neogit.merkle.angela import MerkleFSTree
from neogit.merkle.hasher import Hasher
from neogit.model import Branch, Commit, DiffStatus, FSDiffObject, FSSearchResult, FSSearchType, Tree
from neogit.object_storage import ContainerAlreadyExists, TSObjectStorage
from neogit.search import search_by_filename, search_by_path, search_by_sha1
from neogit.utils import traverse_path_tree


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
    def __init__(self, object_driver_ts: TSObjectStorage, gui_enabled: bool = False):
        """Initializes a Neogit instance, connects to Neo4j DB and Object Storage"""
        self._log = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._gui_enabled = gui_enabled
        # dynaconf settings are list, need to convert to tuple
        creds = tuple(settings.neo4j.creds) if settings.neo4j.creds is not None else None
        self._graph_driver = GraphDatabase.driver(settings.neo4j.url, auth=creds)
        self._object_driver_ts = object_driver_ts
        self._object_driver = self._object_driver_ts.instance

    def iter_commit(self) -> Iterator[Commit]:
        """Enumerate all commits in the database"""
        with self._graph_driver.session() as session:
            yield from Commit.iter(session, settings.branch)

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
                tree_sha1 = traverse_path_tree(session, os_sha1, fs_path)
                final_tree = Tree()
                final_tree.sha1sum = tree_sha1
                target_tree_list[os_sha1] = final_tree
            for tree in target_tree_list.values():
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
            # TODO commit: Optional[Commit] = branch.os_commit
            raise NotImplementedError

    def diff(self, ref1: str, ref2: str):
        # check if both refs exists
        with self._graph_driver.session() as session:
            ref1_tree_sha1 = Commit.get_tree_sha1_from_commit_sha1(session, ref1)
            ref2_tree_sha1 = Commit.get_tree_sha1_from_commit_sha1(session, ref2)
            yield from diff_trees(session, ref1_tree_sha1, ref2_tree_sha1)

    def diff_filesystem_at(self, os1_sha1: str, os2_sha1: str, fs_path: Path) -> Iterator[FSDiffObject]:
        with self._graph_driver.session() as session:
            try:
                os1_final_tree_sha1 = traverse_path_tree(session, os1_sha1, fs_path)
            except RuntimeError:
                os1_final_tree = None
            else:
                os1_final_tree = Tree()
                os1_final_tree.sha1sum = os1_final_tree_sha1
            try:
                os2_final_tree_sha1 = traverse_path_tree(session, os2_sha1, fs_path)
            except RuntimeError:
                os2_final_tree = None
            else:
                os2_final_tree = Tree()
                os2_final_tree.sha1sum = os2_final_tree_sha1
            if os1_final_tree is None and os2_final_tree:
                # path is a new directory on OS2
                # get fs entries
                fs_entries = self.list_filesystem_at([os2_sha1], fs_path)[os2_sha1]
                for child_name, child_tree in fs_entries.children_tree.items():
                    yield FSDiffObject(DiffStatus.NEW, True, fs_path / child_name, None, child_tree.sha1sum)
                for child_name, child_blob in fs_entries.children_blob.items():
                    yield FSDiffObject(DiffStatus.NEW, False, fs_path / child_name, None, child_blob.sha1sum)
            elif os1_final_tree and os2_final_tree is None:
                # path is deleted directory on OS2
                fs_entries = self.list_filesystem_at([os1_sha1], fs_path)[os1_sha1]
                for child_name, child_tree in fs_entries.children_tree.items():
                    yield FSDiffObject(DiffStatus.DEL, True, fs_path / child_name, child_tree.sha1sum, None)
                for child_name, child_blob in fs_entries.children_blob.items():
                    yield FSDiffObject(DiffStatus.DEL, False, fs_path / child_name, child_blob.sha1sum, None)
            elif os1_final_tree and os2_final_tree:
                yield from diff_trees(session, os1_final_tree.sha1sum, os2_final_tree.sha1sum, fs_path)
            else:
                raise RuntimeError(f"Path {fs_path} not found OS commits")

    def get_object_size(self, obj_sha1: str) -> int:
        container_name = settings.object.container_name
        container = self._object_driver.get_container(container_name)
        obj = self._object_driver.get_object(container, obj_sha1)
        return obj.size

    def download_object_as_stream(self, obj_sha1: str, chunk_size: int = None) -> Iterator[bytes]:
        container_name = settings.object.container_name
        container = self._object_driver.get_container(container_name)
        obj = self._object_driver.get_object(container, obj_sha1)
        yield from self._object_driver.download_object_as_stream(obj, chunk_size)

    def filesystem_search(
        self, os_sha1_list: Optional[List[str]], search_expr: str, search_type: FSSearchType
    ) -> Iterator[FSSearchResult]:
        with self._graph_driver.session() as session:
            if search_type == FSSearchType.Filename:
                yield from search_by_filename(session, os_sha1_list, search_expr)
            elif search_type == FSSearchType.Path:
                yield from search_by_path(session, os_sha1_list, search_expr)
            elif search_type == FSSearchType.SHA1:
                yield from search_by_sha1(session, os_sha1_list, search_expr)
