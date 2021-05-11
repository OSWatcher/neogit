"""Merkle tree pipeline

Each file goes through this pipeline to do all the necessary operations
"""
import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from itertools import tee
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional
from uuid import uuid4

from neogit.config import settings
from neogit.merkle.hasher import Hasher
from neogit.merkle.utils import filepath_merkle_ctx, iter_chunk
from neogit.object_storage import TSObjectStorage


class MerklePipeline:
    def __init__(self, ts_object: TSObjectStorage):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._max_workers: Optional[int] = settings.get("max_workers", os.cpu_count())
        self._ts_object = ts_object
        # build thread pool to compute SHA1s
        # hashlib: the Python GIL is released for data larger than 2047 bytes at object creation or on update
        self._sha1_pool = ThreadPoolExecutor(self._max_workers, "sha1-pool")
        # pipeline results
        self._result: Dict[str, Future] = {}

    def _merkelize_file_list(self, dir: Path, filename_list: List[str]):
        """merkelize a list of files.

        for each file:
        1. compute the SHA1
        2. upload the file to the object storage
        """
        # get per-thread object storage instance
        obj_adapter = self._ts_object.instance
        # get container
        container_name = settings.object.container_name
        container = obj_adapter.get_container(container_name)
        # for each file
        tid = threading.get_ident()
        filename_to_sha1: Dict[str, str] = {}
        for filename in filename_list:
            # compute the SHA1
            filepath = dir / filename
            with filepath_merkle_ctx(filepath) as io:
                chunk_gen_sha1, chunk_gen_upload = tee(iter_chunk(io))
                hash = Hasher()
                [hash.string(chunk) for chunk in chunk_gen_sha1]
                sha1 = hash.digest()
                filename_to_sha1[filename] = sha1
                # upload to object storage
                obj_name = sha1
                obj_adapter.upload_object_via_stream(chunk_gen_upload, container, obj_name)
        self._logger.debug("[%s] %s: %s", tid, dir, pformat(filename_to_sha1))
        return filename_to_sha1

    def submit(self, dir: Path, filename_list: List[str]) -> str:
        """submit a list of filename to the pipeline, from a directory

        Returns:
            str: the task uuid to get the results
        """
        future = self._sha1_pool.submit(self._merkelize_file_list, dir, filename_list)
        task_id = str(uuid4())
        # task -> future
        self._result[task_id] = future
        return task_id

    def get_task_result(self, task_id: str) -> Dict[str, str]:
        future = self._result[task_id]
        res: Dict[str, str] = future.result()
        del self._result[task_id]
        return res
