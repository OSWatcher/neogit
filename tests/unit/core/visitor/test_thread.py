from queue import Queue

from neogit.core.model import Node
from neogit.core.visitor import NodeVisitor, NodeVisitorThread, VisitedNode


def test_node_visitor_thread():
    # arrange
    queue = Queue()
    visitor = NodeVisitor(queue)
    node = Node()
    # act
    with NodeVisitorThread(visitor, node) as thread:
        thread.start()
        thread.join()
    # assert
    assert queue.qsize() == 2
    assert queue.get() == VisitedNode(node, None)
    # sentinel
    assert queue.get() is None
