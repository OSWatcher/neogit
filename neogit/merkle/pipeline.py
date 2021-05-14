"""Merkle tree pipeline

Each file goes through this pipeline to do all the necessary operations
"""
import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from io import SEEK_END, SEEK_SET
from pathlib import Path
from threading import Condition, local
from typing import Dict, Iterator, Optional, Tuple
from uuid import uuid4

from neogit.config import settings
from neogit.console import DEFAULT_ADAPTER, AbstractConsoleAdapter, TaskPool
from neogit.merkle.hasher import Hasher
from neogit.merkle.utils import filepath_merkle_ctx, iter_chunk
from neogit.object_storage import ObjectDoesNotExistError, TSObjectStorage


class MerklePipeline:
    def __init__(self, root: Path, ts_object: TSObjectStorage, console: AbstractConsoleAdapter = DEFAULT_ADAPTER):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._max_workers: Optional[int] = settings.get("max_workers", os.cpu_count())
        self._root = root
        self._ts_object = ts_object
        self._console = console
        # build thread pool to compute SHA1s
        # hashlib: the Python GIL is released for data larger than 2047 bytes at object creation or on update
        self._sha1_pool = ThreadPoolExecutor(self._max_workers, "sha1-pool")
        self._storage_pool = ThreadPoolExecutor(thread_name_prefix="stor-pool")
        # pipeline results
        self._pipeline_results: Dict[str, Optional[Tuple[Path, str]]] = {}
        # condition variable
        self._cv = Condition()
        # cache container object per thread
        self._th_local = local()

    def _get_container(self):
        """get the container and cache it in a thread local variable.

        Every thread must have their own container object"""
        try:
            container = self._th_local.container
        except AttributeError:
            obj_adapter = self._ts_object.instance
            container_name = settings.object.container_name
            container = obj_adapter.get_container(container_name)
            self._th_local.container = container
        return container

    def _merkelize_file(self, task_id: str, filepath: Path):
        """pipeline stage to merkelize a given file"""
        with filepath_merkle_ctx(filepath) as io:
            file_size = io.seek(0, SEEK_END)
            io.seek(0, SEEK_SET)
            task_name = str(filepath.relative_to(self._root))
            self._console.set_pool_task(TaskPool.SHA1, task_name, file_size)
            hash = Hasher()
            for chunk in iter_chunk(io):
                hash.string(chunk)
                self._console.update_pool_task(TaskPool.SHA1, len(chunk))
            sha1 = hash.digest()
            result = filepath, sha1
            return task_id, result

    def _pipe_merkelize_to_upload(self, f: Future):
        task_id, result = f.result()
        future = self._storage_pool.submit(self._storage_upload, task_id, *result)
        future.add_done_callback(self._pipeline_end)

    def _storage_upload(self, task_id: str, filepath: Path, sha1sum: str):
        """pipeline stage to upload a given object to the object storage"""
        # get per-thread object storage instance
        obj_adapter = self._ts_object.instance

        # get container
        container = self._get_container()

        # upload to object storage if necessary
        obj_name = sha1sum
        try:
            obj_adapter.get_object(container, obj_name)
        except ObjectDoesNotExistError:
            with filepath_merkle_ctx(filepath) as io:
                size = io.seek(0, SEEK_END)
                task_name = str(filepath.relative_to(self._root))
                self._console.set_pool_task(TaskPool.Storage, task_name, size)
                io.seek(0, SEEK_SET)

                def iter_chunk_progress() -> Iterator[bytes]:
                    for chunk in iter_chunk(io):
                        yield chunk
                        self._console.update_pool_task(TaskPool.Storage, len(chunk))

                obj_adapter.upload_object_via_stream(iter_chunk_progress(), container, obj_name)

        result = filepath, sha1sum
        return task_id, result

    def _pipeline_end(self, f: Future):
        task_id, result = f.result()
        filepath, sha1sum = result
        tid = threading.get_ident()
        # associate result
        with self._cv:
            self._logger.debug("[%s]📄 %s: %s", tid, filepath, sha1sum)
            self._pipeline_results[task_id] = filepath, sha1sum
            # notify consumers
            self._cv.notify_all()

    def submit(self, filepath: Path) -> str:
        """submit a filepath to the pipeline

        Returns:
            str: the task uuid to get the results
        """
        task_id = str(uuid4())
        # add task to the ordered dict
        # task_id -> no results yet
        self._pipeline_results[task_id] = None
        # then schedule it
        future = self._sha1_pool.submit(self._merkelize_file, task_id, filepath)
        future.add_done_callback(self._pipe_merkelize_to_upload)

        return task_id

    def result(self, task_id: str) -> Tuple[Path, str]:
        """Fetch the pipeline results associated with a task_id, wait if necessary"""
        with self._cv:
            self._cv.wait_for(lambda: self._pipeline_results[task_id] is not None)
            result: Optional[Tuple[Path, str]] = self._pipeline_results[task_id]
            assert result
            # remove entry to avoid filling RAM
            del self._pipeline_results[task_id]
            return result
