"""Implements a Visitor which handles Neo4j transaction upload and the Object Storage upload"""
import logging
from queue import Queue
from typing import Optional

from neogit.core.merkle import MerkleVisitor
from neogit.core.model import FSDirectoryNode, MerkleLabel, MerkleNode, Node
from neogit.core.visitor import NodeVisitorThread, VisitedNode
from neogit.merkle.uploaderthread import ObjectUploaderThread
from neogit.model.merkle import Blob, Tree
from neogit.object_storage import TSObjectStorage


class NeoMerkleTreeBuilder:
    def __init__(self, ts_object: TSObjectStorage, node_to_visit: Node):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._main_queue: Queue = Queue()
        self._uploader_queue: Queue = Queue()
        self._uploader_thread = ObjectUploaderThread(ts_object, self._uploader_queue)
        self._node_to_visit = node_to_visit
        self._visitor = MerkleVisitor([self._main_queue, self._uploader_queue])
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
            item: Optional[VisitedNode] = self._main_queue.get()
            if item is None:
                break
            assert isinstance(item.return_value, MerkleNode)
            if not isinstance(item.node, FSDirectoryNode):
                continue
            # directory, upload it to Neo4j
            # Ensure all child blobs have been created
            for child_blob in (
                child for child in item.return_value.children.values() if child.label == MerkleLabel.Blob
            ):
                try:
                    Blob.nodes.get(hash=child_blob.hash)
                except Blob.DoesNotExist:
                    blob = Blob(hash=child_blob.hash)
                    blob.save()

            # Build Tree node
            tree = Tree.from_merkle_node(item.return_value)
            tree.save()
        merkle_node = self._visitor_thread.join()
        self._uploader_thread.join()
        # convert to Tree
        return Tree.from_merkle_node(merkle_node)
