"""Implements a Visitor which handles Neo4j transaction upload and the Object Storage upload"""
import logging
from queue import Queue
from typing import Union

from neo4j import Session, Transaction

from neogit.core.merkle import FSMerkleVisitor
from neogit.core.model import FSDirectoryNode, MerkleNode, Node
from neogit.merkle.uploaderthread import ObjectUploaderThread
from neogit.model.merkle import Tree
from neogit.object_storage import TSObjectStorage


class NeoMerkleTreeBuilder:
    def __init__(self, ts_object: TSObjectStorage, node_to_visit: Node, session: Union[Session, Transaction]):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._session = session
        self._uploader_queue: Queue = Queue()
        self._uploader_thread = ObjectUploaderThread(ts_object, self._uploader_queue)
        self._node_to_visit = node_to_visit
        self._visitor = FSMerkleVisitor()

    def __enter__(self):
        self._uploader_thread.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._uploader_thread.__exit__(exc_type, exc_val, exc_tb)

    def run(self):
        # start the uploader thread
        # it will consume the VisitedNode items
        self._uploader_thread.start()
        last_item = None
        for item in self._visitor.visit(self._node_to_visit):
            self._uploader_queue.put(item)
            # on every loop, check that one of the uploader thread pool didn't raise any fatal exception
            self._uploader_thread.check_exception()
            assert isinstance(item.return_value, MerkleNode)
            if not isinstance(item.node, FSDirectoryNode):
                continue
            # directory, upload it to Neo4j
            Tree.create_from_merkle_node_cypher(self._session, item.return_value)
            self._logger.info("Tree %s created from %s", item.return_value.hash, item.node.path)
            last_item = item
        root_merkle_node = last_item.return_value
        # put None in queue to stop uploader_thread
        self._uploader_queue.put(None)
        self._uploader_thread.join()
        # return root Tree
        return Tree.nodes.get(hash=root_merkle_node.hash)
