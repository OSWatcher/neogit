"""Implements a Visitor which handles Neo4j transaction upload and the Object Storage upload"""
from queue import Queue
from typing import Union

from attrs import define, field
from neo4j import Session, Transaction

from neogit.core.merkle import FSMerkleVisitor
from neogit.core.model import FSDirectoryNode, MerkleNode, Node
from neogit.merkle.uploaderthread import ObjectUploaderThread
from neogit.model.merkle import Tree
from neogit.object_storage import TSObjectStorage
from neogit.utils import BetterContextManager


@define(auto_attribs=True)
class NeoMerkleTreeBuilder(BetterContextManager):
    ts_object: TSObjectStorage = field()
    node_to_visit: Node = field()
    session: Union[Session, Transaction] = field()
    uploader_queue: Queue = field(init=False, default=Queue())
    uploader_thread: ObjectUploaderThread = field(init=False)
    visitor: FSMerkleVisitor = field(init=False)

    def safe_enter(self):
        self.visitor = self.ex.enter_context(FSMerkleVisitor(thread=True))
        self.uploader_thread = self.ex.enter_context(ObjectUploaderThread(self.ts_object, self.uploader_queue))
        return self

    def run(self):
        # start visting node in background
        self.visitor.run_visit(self.node_to_visit)
        # start the uploader thread
        # it will consume the VisitedNode items
        self.uploader_thread.start()
        last_item = None
        for item in self.visitor.as_gen():
            self.uploader_queue.put(item)
            # on every loop, check that one of the uploader thread pool didn't raise any fatal exception
            self.uploader_thread.check_exception()
            assert isinstance(item.return_value, MerkleNode)
            if not isinstance(item.node, FSDirectoryNode):
                continue
            # directory, upload it to Neo4j
            Tree.create_from_merkle_node_cypher(self.session, item.return_value)
            self.logger.info("Tree %s created from %s", item.return_value.hash, item.node.path)
            last_item = item
        root_merkle_node = last_item.return_value
        # put None in queue to stop uploader_thread
        self.uploader_queue.put(None)
        self.uploader_thread.join()
        # return root Tree
        return Tree.nodes.get(hash=root_merkle_node.hash)
