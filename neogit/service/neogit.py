"""Contains main Neogit class"""
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path, PurePath
from typing import Dict, Iterator, List, Optional

from gql import Client, gql
from neo4j import GraphDatabase
from neo4j.exceptions import ClientError
from neomodel import db

from neogit.config import settings
from neogit.core.model import FSDirectoryNode
from neogit.diff import diff_trees
from neogit.merkle import NeoMerkleTreeBuilder
from neogit.model import Branch, Commit, DiffStatus, FSDiffObject, FSSearchResult, FSSearchType, Tree
from neogit.model.gql import Commit as GQLCommit
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
    def __init__(self, object_driver_ts: TSObjectStorage, graphql_client: Client, gui_enabled: bool = False):
        """Initializes a Neogit instance, connects to Neo4j DB and Object Storage"""
        self._log = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._gui_enabled = gui_enabled
        self._gql_client = graphql_client
        # dynaconf settings are list, need to convert to tuple
        creds = tuple(settings.neo4j.creds) if settings.neo4j.creds is not None else None
        self._graph_driver = GraphDatabase.driver(settings.neo4j.url, auth=creds)
        db.set_connection(settings.neo4j.url_full)
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

    def init(self):
        """Initialize a neogit repository by creating indexes and constraints"""
        with self._graph_driver.session() as session:
            constraints = {"Blob": "hash", "Tree": "hash", "Commit": "hash", "Branch": "name"}
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
    def commit(self, name: str, root: Path) -> GQLCommit:
        """Compute the Merkle TreeNode for the root directory and insert a new commit in the database"""
        if not root.exists():
            raise ValueError(f"Root directory {root} does not exist")
        # build merkle tree
        root_node = FSDirectoryNode(root)
        with NeoMerkleTreeBuilder(self._object_driver_ts, root_node, self._gql_client) as builder:
            root_tree = builder.run()  # noqa: F841 TODO
        # get branch and the current tracked commit
        query = gql(
            """
            query($where: BranchWhere) {
              branches(where: $where) {
                name
                tracks {
                  hash
                }
              }
            }
            """
        )
        where_params = {"name": settings.branch}
        result = self._gql_client.execute(query, variable_values={"where": where_params})
        branches = result["branches"]
        previous_commit_hash: Optional[str] = None
        if not branches:
            # must create new branch
            query = gql(
                """
                mutation createNewBranch($input: [BranchCreateInput!]!) {
                    createBranches(input: $input) {
                        branches {
                            name
                        }
                    }
                }
                """
            )
            branch_create_params = {"name": settings.branch}
            self._log.info("Creating new branch: %s", settings.branch)
            self._gql_client.execute(query, variable_values={"input": branch_create_params})
        else:
            previous_commit_hash = branches[0]["tracks"]["hash"]
        gql_commit = GQLCommit(name, root_tree.hash)
        mut_new_commit_params = {
            # disconnect branch from all commits
            "disconnect": {"tracks": {}},
            # create the commit
            "input": {
                "hash": gql_commit.hash,
                "name": gql_commit.name,
                "date": gql_commit.date,
                "filesystem": {"connect": {"where": {"node": {"hash": root_tree.hash}}}},
            },
            "where": {"name": settings.branch},
            # connect branch to new commit
            "connect": {"tracks": {"where": {"node": {"hash": gql_commit.hash}}}},
        }
        # connect new commit to previous
        if previous_commit_hash:
            mut_new_commit_params["input"]["previous"] = {
                "connect": {"where": {"node": {"hash": previous_commit_hash}}}
            }
        query = gql(
            """
            mutation createNewCommit($disconnect: BranchDisconnectInput, $input: [CommitCreateInput!]!,
                $where: BranchWhere, $connect: BranchConnectInput) {
                untrackPrevious: updateBranches(where: $where, disconnect: $disconnect) {
                    branches {
                        tracks {
                            hash
                        }
                    }
                }
                createCommits(input: $input) {
                    commits {
                        name
                    }
                }
                trackNew: updateBranches(where: $where, connect: $connect) {
                    branches {
                        tracks {
                            hash
                        }
                    }
                }
            }
            """
        )
        result = self._gql_client.execute(query, variable_values=mut_new_commit_params)
        self._log.info("Commit created: %s", gql_commit)
        return gql_commit

    def log(self):
        branch_name: str = settings.branch
        with self._graph_driver.session() as session:
            branch = Branch(session, branch_name)
            if not branch:
                raise RuntimeError(f"Branch {branch_name} not found")
            # get last commit
            # TODO commit: Optional[Commit] = branch.os_commit
            raise NotImplementedError

    def diff_commits(self, base_commit_hash: str, diffee_commit_hash: str) -> Iterator[FSDiffObject]:
        query = gql(
            """
            query($baseCommitHash: String!, $diffeeCommitHash: String!) {
              diffCommits(base_commit_hash: $baseCommitHash, diffee_commit_hash: $diffeeCommitHash) {
                newitems {
                  path
                  old_hash
                  new_hash
                }
                delitems {
                  path
                  old_hash
                  new_hash
                }
                moditems {
                  path
                  old_hash
                  new_hash
                }
              }
            }
        """
        )
        result = self._gql_client.execute(
            query, variable_values={"baseCommitHash": base_commit_hash, "diffeeCommitHash": diffee_commit_hash}
        )
        for item in result["diffCommits"]["newitems"]:
            yield FSDiffObject(DiffStatus.NEW, item["path"], item["old_hash"], item["new_hash"])
        for item in result["diffCommits"]["delitems"]:
            yield FSDiffObject(DiffStatus.DEL, item["path"], item["old_hash"], item["new_hash"])
        for item in result["diffCommits"]["moditems"]:
            yield FSDiffObject(DiffStatus.MOD, item["path"], item["old_hash"], item["new_hash"])

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
