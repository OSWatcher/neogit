"""Contains main Neogit class"""
import logging
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from neo4j import GraphDatabase, Transaction, exceptions
from neomodel import db

from neogit.config import ObjectConfig, settings
from neogit.core.model import FSDirectoryNode
from neogit.merkle import NeoMerkleTreeBuilder
from neogit.model import FSSearchResult, FSSearchType
from neogit.model.neo import Branch as NeoBranch
from neogit.model.neo import Commit as NeoCommit
from neogit.object_storage import ContainerAlreadyExists, LibcloudObjectStorage, TSObjectStorage
from neogit.search import search_by_filename, search_by_path, search_by_sha1
from neogit.utils import setup_logging

# TODO: neomodel
# from neogit.utils import traverse_path_tree


def measure_time(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        start = datetime.now()
        res = method(self, *args, **kwargs)
        end = datetime.now()
        self._log.debug("%s execution time: %s", method.__name__, end - start)
        return res

    return wrapper


# a wrapper on db.cypher_query with exponential backoff
# when DeadlockDetected is raised
def cypher_query_with_backoff(
    query: str, params: Dict[str, Any], max_retries: int = 10, initial_retry_delay=0.5
) -> List[Dict[str, Any]]:
    retries = 0
    while True:
        try:
            return db.cypher_query(query, params)
        except exceptions.TransientError as e:
            if e.code != "Neo.TransientError.Transaction.DeadlockDetected":
                raise
            logging.info("Deadlock detected, retrying (%s)", retries)
            retries += 1
            if retries > max_retries:
                raise e
            time.sleep(initial_retry_delay * (2**retries))


class Neogit:
    def __init__(self, object_driver_ts: TSObjectStorage = None, gui_enabled: bool = False, debug: bool = False):
        """Initializes a Neogit instance, connects to Neo4j DB and Object Storage"""
        setup_logging(debug)
        if object_driver_ts is None:
            obj_config = ObjectConfig.from_settings(settings)
            object_driver_ts = TSObjectStorage(LibcloudObjectStorage, obj_config)
        self._log = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._gui_enabled = gui_enabled
        # dynaconf settings are list, need to convert to tuple
        creds = tuple(settings.neo4j.creds) if settings.neo4j.creds is not None else None
        self._graph_driver = GraphDatabase.driver(settings.neo4j.url, auth=creds)
        db.set_connection(settings.neo4j.url_full)
        self.db = db
        self._object_driver_ts = object_driver_ts
        self._object_driver = self._object_driver_ts.instance

    # TODO: neomodel
    # def list_filesystem_at(self, os_sha1_list: List[str], fs_path: PurePath) -> Dict[str, Tree]:
    #     """List the filesystem entries at fs_path for a specific OS sha1sum"""
    #     with self._graph_driver.session() as session:
    #         target_tree_list: Dict[str, Tree] = {}
    #         for os_sha1 in os_sha1_list:
    #             commit: Optional[Commit] = Commit.get(session, os_sha1)
    #             if not commit:
    #                 raise RuntimeError("Commit not found")
    #             tree_sha1 = traverse_path_tree(session, os_sha1, fs_path)
    #             final_tree = Tree()
    #             final_tree.sha1sum = tree_sha1
    #             target_tree_list[os_sha1] = final_tree
    #         for tree in target_tree_list.values():
    #             tree.get_children(session)
    #         # get children
    #         return target_tree_list

    def init(self):
        """Initialize a neogit repository by creating indexes and constraints"""
        with self._graph_driver.session() as session:
            constraints = {
                "Blob": ["hash", "sha1sum"],
                "Tree": ["hash", "sha1sum"],
                "Commit": ["hash", "sha1sum"],
                "Branch": ["name"],
            }
            # constraints = {"Blob": ["hash"], "Tree": ["hash"], "Commit": ["hash"], "Branch": "name"}
            for label, unique_prop_list in constraints.items():
                for unique_prop in unique_prop_list:
                    self._log.debug("Graph: creating unique contraint on %s:%s", label, unique_prop)
                    session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{unique_prop} IS UNIQUE")
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
    def commit(
        self, name: str, root: Path, desc: str = None, branch_name: str = None, unique: bool = False, before: str = None
    ) -> str:
        """Compute the Merkle TreeNode for the root directory and insert a new commit in the database"""
        branch_name = branch_name or settings.branch
        if not root.exists():
            raise ValueError(f"Root directory {root} does not exist")
        with db.write_transaction as transaction_proxy:
            try:
                branch = NeoBranch.nodes.get(name=branch_name)
            except NeoBranch.DoesNotExist:
                # ensure branch is created
                branch = NeoBranch(name=branch_name)
                branch.save()
            else:
                if unique:
                    # check if that commit already exists in that branch
                    found = branch.commit_exists(name)
                    if found:
                        return found.hash

            # commit should be created
            trans: Transaction = transaction_proxy.db._active_transaction
            # check before exists
            if before:
                # check before exists
                before_commit = branch.commit_exists(before)
                if not before_commit:
                    raise ValueError(f"Commit {before} not found")

            # build merkle tree
            root_node = FSDirectoryNode(root)
            with NeoMerkleTreeBuilder(self._object_driver_ts, root_node, trans) as builder:
                root_tree = builder.run()

            # create new commit
            new_commit = NeoCommit.from_name(name, root_tree, description=desc)
            # where should it be inserted ?
            if before:
                # save before's previous
                before_prev = before_commit.previous.single()
                if before_prev:
                    # connect new commit to before's previous
                    new_commit.previous.connect(before_prev)
                # connect before's previous to new commit
                before_commit.previous.replace(new_commit)
            else:
                # save current branch head
                branch_head = branch.tracks.single()
                # insert at the beginning
                branch.tracks.replace(new_commit)
                # connect new commit to branch head
                new_commit.previous.connect(branch_head)

            return new_commit.hash

    def create_branch(self, branch_name: str, commit_sha1: str):
        with db.write_transaction:
            try:
                branch = NeoBranch.nodes.get(name=branch_name)
            except NeoBranch.DoesNotExist:
                branch = NeoBranch(name=branch_name)
                commit = NeoCommit.nodes.get(hash=commit_sha1)
                branch.save()
                branch.tracks.replace(commit)
            else:
                raise ValueError(f"Branch {branch_name} already exists")

    # def log(self):
    #     branch_name: str = settings.branch
    #     with self._graph_driver.session() as session:
    #         branch = Branch(session, branch_name)
    #         if not branch:
    #             raise RuntimeError(f"Branch {branch_name} not found")
    #         # get last commit
    #         # TODO commit: Optional[Commit] = branch.os_commit
    #         raise NotImplementedError

    # def diff(self, ref1: str, ref2: str):
    #     # check if both refs exists
    #     with self._graph_driver.session() as session:
    #         ref1_tree_sha1 = Commit.get_tree_sha1_from_commit_sha1(session, ref1)
    #         ref2_tree_sha1 = Commit.get_tree_sha1_from_commit_sha1(session, ref2)
    #         yield from diff_trees(session, ref1_tree_sha1, ref2_tree_sha1)

    # def diff_filesystem_at(self, os1_sha1: str, os2_sha1: str, fs_path: Path) -> Iterator[FSDiffObject]:
    #     with self._graph_driver.session() as session:
    #         try:
    #             os1_final_tree_sha1 = traverse_path_tree(session, os1_sha1, fs_path)
    #         except RuntimeError:
    #             os1_final_tree = None
    #         else:
    #             os1_final_tree = Tree()
    #             os1_final_tree.sha1sum = os1_final_tree_sha1
    #         try:
    #             os2_final_tree_sha1 = traverse_path_tree(session, os2_sha1, fs_path)
    #         except RuntimeError:
    #             os2_final_tree = None
    #         else:
    #             os2_final_tree = Tree()
    #             os2_final_tree.sha1sum = os2_final_tree_sha1
    #         if os1_final_tree is None and os2_final_tree:
    #             # path is a new directory on OS2
    #             # get fs entries
    #             fs_entries = self.list_filesystem_at([os2_sha1], fs_path)[os2_sha1]
    #             for child_name, child_tree in fs_entries.children_tree.items():
    #                 yield FSDiffObject(DiffStatus.NEW, True, fs_path / child_name, None, child_tree.sha1sum)
    #             for child_name, child_blob in fs_entries.children_blob.items():
    #                 yield FSDiffObject(DiffStatus.NEW, False, fs_path / child_name, None, child_blob.sha1sum)
    #         elif os1_final_tree and os2_final_tree is None:
    #             # path is deleted directory on OS2
    #             fs_entries = self.list_filesystem_at([os1_sha1], fs_path)[os1_sha1]
    #             for child_name, child_tree in fs_entries.children_tree.items():
    #                 yield FSDiffObject(DiffStatus.DEL, True, fs_path / child_name, child_tree.sha1sum, None)
    #             for child_name, child_blob in fs_entries.children_blob.items():
    #                 yield FSDiffObject(DiffStatus.DEL, False, fs_path / child_name, child_blob.sha1sum, None)
    #         elif os1_final_tree and os2_final_tree:
    #             yield from diff_trees(session, os1_final_tree.sha1sum, os2_final_tree.sha1sum, fs_path)
    #         else:
    #             raise RuntimeError(f"Path {fs_path} not found OS commits")

    def get_object_size(self, obj_sha1: str) -> int:
        container_name = settings.object.container_name
        container = self._object_driver.get_container(container_name)
        obj = self._object_driver.get_object(container, obj_sha1)
        return obj.size

    def download_object_as_stream(self, obj_sha1: str, chunk_size: Optional[int] = None) -> Iterator[bytes]:
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
