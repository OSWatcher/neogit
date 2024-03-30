"""Implements a Visitor which handles Neo4j transaction upload and the Object Storage upload"""
import logging
from queue import Empty, Queue
from typing import Optional, Union

from neo4j import Session, Transaction

from neogit.core.merkle import FSMerkleVisitor
from neogit.core.model import FSDirectoryNode, MerkleNode, Node
from neogit.core.visitor import NodeVisitorThread, VisitedNode
from neogit.merkle.uploaderthread import ObjectUploaderThread
from neogit.model.merkle import Tree
from neogit.object_storage import TSObjectStorage


class NeoMerkleTreeBuilder:
    def __init__(self, ts_object: TSObjectStorage, node_to_visit: Node, session: Union[Session, Transaction]):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._session = session
        self._main_queue: Queue = Queue()
        self._uploader_queue: Queue = Queue()
        self._uploader_thread = ObjectUploaderThread(ts_object, self._uploader_queue)
        self._node_to_visit = node_to_visit
        self._visitor = FSMerkleVisitor([self._main_queue, self._uploader_queue])
        self._visitor_thread = NodeVisitorThread(self._visitor, node_to_visit)

    def __enter__(self):
        self._visitor_thread.__enter__()
        self._uploader_thread.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._visitor_thread.__exit__(exc_type, exc_val, exc_tb)
        self._uploader_thread.__exit__(exc_type, exc_val, exc_tb)

    def run(self):
        # start the visitor thread
        # it will begin producing VisitedNode items in the main queue
        self._visitor_thread.start()
        # start the uploader thread
        # it will consume the VisitedNode items
        self._uploader_thread.start()
        while True:
            # on every loop, check that one of the uploader thread pool didn't raise any fatal exception
            self._uploader_thread.check_exception()
            try:
                item: Optional[VisitedNode] = self._main_queue.get(timeout=1)
            except Empty:
                # no items yet
                # check if the visitor thread is dead
                self._logger.info("MainQueue: No MerkleNode items available. Waiting.")
                self._visitor_thread.check_exception()
                continue
            if item is None:
                break
            assert isinstance(item.return_value, MerkleNode)
            if not isinstance(item.node, FSDirectoryNode):
                continue
            # directory, upload it to Neo4j
            Tree.create_from_merkle_node_cypher(self._session, item.return_value)
            self._logger.info("Tree %s created from %s", item.return_value.hash, item.node.path)
        merkle_node = self._visitor_thread.join()
        self._uploader_thread.join()
        # return root Tree
        return Tree.nodes.get(hash=merkle_node.hash)
