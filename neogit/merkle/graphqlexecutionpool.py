import logging
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from threading import Lock, get_ident
from typing import Dict, Optional

from gql import Client, gql

from neogit.core.model import FSDirectoryNode, MerkleLabel, MerkleNode


class GraphQLExecutionPool:
    def __init__(self, graphql_client: Client):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._gql_client: Client = graphql_client
        # give human readable worker count for each worker
        self._tid_to_number: Dict[int, int] = {}
        self._pool = ThreadPoolExecutor(thread_name_prefix="graphql-execution")
        self._exception: Optional[BaseException] = None

    def check_exception(self):
        with Lock():
            if self._exception:
                raise self._exception

    def wait(self):
        self._pool.shutdown(wait=True)

    def submit_execute_graphql(self, merklenode: MerkleNode, directorynode: FSDirectoryNode):
        future = self._pool.submit(self.execute_graphql, merklenode, directorynode)
        future.add_done_callback(self.done_callback)

    def ensure_worker_has_humanid(self) -> int:
        tid = get_ident()
        try:
            worker_number = self._tid_to_number[tid]
        except KeyError:
            self._tid_to_number[tid] = len(self._tid_to_number) + 1
            worker_number = self._tid_to_number[tid]
        return worker_number

    def execute_graphql(self, merklenode: MerkleNode, directorynode: FSDirectoryNode):
        worker_number: int = self.ensure_worker_has_humanid()
        # directory, create new Tree mutation
        query = gql(
            """
            mutation createDirectory($input: TreeCreateInput!) {
                mergeTree(input: $input)
            }
            """
        )
        child_blobs = [
            {"node": {"hash": node.hash}, "edge": {"name": name}}
            for name, node in merklenode.children.items()
            if node.label == MerkleLabel.Blob
        ]
        child_trees = [
            {"node": {"hash": node.hash}, "edge": {"name": name}}
            for name, node in merklenode.children.items()
            if node.label == MerkleLabel.Tree
        ]
        tree_create_input = {
            "hash": merklenode.hash,
            "child_blobs": {"create": child_blobs},
            "child_trees": {"create": child_trees},
        }
        start = datetime.now()
        self._gql_client.execute(query, variable_values={"input": tree_create_input})
        end = datetime.now()
        self._logger.info(
            "[%s]Tree %s created from %s (took: %s)", worker_number, merklenode.hash, directorynode.path, end - start
        )

    def done_callback(self, future: Future):
        with Lock():
            try:
                future.exception()
            except BaseException as e:
                self._exception = e
