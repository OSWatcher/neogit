# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from queue import Queue
from threading import current_thread
from typing import Optional

from neogit.console import DEFAULT_ADAPTER, AbstractConsoleAdapter
from neogit.core.model import FSFileNode, MerkleNode
from neogit.core.visitor import VisitedNode
from neogit.merkle.uploader import ObjectUploader
from neogit.object_storage import TSObjectStorage


class ObjectUploaderThread:
    def __init__(
        self,
        ts_object: TSObjectStorage,
        queue: Queue,
        console: AbstractConsoleAdapter = DEFAULT_ADAPTER,
    ):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._queue = queue
        self._uploader = ObjectUploader(ts_object, console=console)
        # this class is a thread, represented by a "ThreadPoolExecutor" with one worker
        # Future are much easier to handle with result values and exceptions support
        self._submit_thread = ThreadPoolExecutor(thread_name_prefix="submit-upload-thread", max_workers=1)
        self._future: Optional[Future] = None

    def __enter__(self):
        self._submit_thread.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # if interrupted by exception, stop the thread
        if exc_type is not None:
            self._queue.put(None)
        self._submit_thread.__exit__(exc_type, exc_val, exc_tb)

    def start(self):
        self._future = self._submit_thread.submit(self._run, self._uploader, self._queue)

    def check_exception(self):
        self._uploader.check_exception()

    def join(self):
        return self._future.result()

    def _run(self, uploader: ObjectUploader, queue: Queue):
        # will consume VisitedNode objects
        while True:
            item: Optional[VisitedNode] = queue.get()
            if item is None:
                break
            if not isinstance(item.node, FSFileNode):
                continue
            assert isinstance(item.return_value, MerkleNode)
            uploader.submit(item.node.path, item.return_value.hash)
        uploader.wait()
        self._logger.debug("Thread %s done", current_thread().name)
