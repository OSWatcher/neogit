from neogit.core.model import Node
from neogit.core.visitor import NodeVisitor, NodeVisitorThread, VisitedNode


def test_node_visitor_thread():
    # arrange
    with NodeVisitor(thread=True) as visitor:
        node = Node()
        # act
        with NodeVisitorThread(visitor, node) as thread:
            thread.start()
            thread.join()
        # assert
        assert visitor.queue.qsize() == 2
        assert visitor.queue.get() == VisitedNode(node, None)
        # sentinel
        assert visitor.queue.get() is None
