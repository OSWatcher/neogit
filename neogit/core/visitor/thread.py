import logging
from concurrent.futures import Future, ThreadPoolExecutor
from threading import current_thread
from typing import Optional

from neogit.core.model import Node
from neogit.core.visitor import NodeVisitor


class NodeVisitorThread:
    """Visit a Node inside a thread"""

    def __init__(self, visitor: NodeVisitor, node_to_visit: Node):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        # manages one thread with ThreadPoolExecutor
        # with Future objects, it's easy to return a value and get exceptions
        self._pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=f"node-visitor-{visitor.__class__.__name__}-thread"
        )
        self._visitor = visitor
        self._node_to_visit = node_to_visit
        self._future: Optional[Future] = None

    def __enter__(self):
        self._pool.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # shutdown pool
        self._pool.__exit__(exc_type, exc_val, exc_tb)

    def start(self):
        self.__enter__()
        self._future = self._pool.submit(self._run, self._visitor, self._node_to_visit)

    def check_exception(self):
        if not self._future:
            return
        if self._future.running():
            return
        exc = self._future.exception()
        if exc:
            raise exc

    def join(self):
        return self._future.result()

    def _run(self, visitor: NodeVisitor, node_to_visit: Node):
        value = visitor.visit(node_to_visit)
        # put None in queue
        visitor.done_visiting()
        self._logger.debug("Thread %s done", current_thread().name)
        return value
