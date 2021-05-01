"""Merkle tree pipeline

Each file goes through this pipeline to do all the necessary operations
"""
import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from neogit.config import settings
from neogit.merkle.hasher import Hasher


class MerklePipeline:
    def __init__(self):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._max_workers: Optional[int] = settings.get("max_workers", os.cpu_count())
        # build thread pool to compute SHA1s
        # hashlib: the Python GIL is released for data larger than 2047 bytes at object creation or on update
        self._sha1_pool = ThreadPoolExecutor(self._max_workers, "sha1-pool")
        # pipeline results
        self._result: Dict[str, Future] = {}

    def _merkelize_file_list(self, filepath_list: List[Path]):
        """merkelize a list of files. executed in a thread"""
        tid = threading.get_ident()
        result: Dict[Path, str] = {}
        for filepath in filepath_list:
            hash = Hasher()
            hash.filepath(filepath)
            sha1 = hash.digest()
            self._logger.debug("[%s]📄 %s: %s", tid, filepath, sha1)
            result[filepath] = sha1
        return result

    def submit(self, filepath_list: List[Path]) -> str:
        """submit a list of filepath to the pipeline

        Returns:
            str: the task uuid to get the results
        """
        future = self._sha1_pool.submit(self._merkelize_file_list, filepath_list)
        task_id = str(uuid4())
        # task -> future
        self._result[task_id] = future
        return task_id

    def get_task_result(self, task_id: str) -> Dict[Path, str]:
        future = self._result[task_id]
        res: Dict[Path, str] = future.result()
        del self._result[task_id]
        return res
