"""This module takes care of uploading objects to the object storage"""
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial
from pathlib import Path
from threading import Lock, get_ident, local
from typing import Dict, Optional

import attr

from neogit.config import settings
from neogit.merkle.utils import BUFFER_SIZE, filepath_merkle_ctx
from neogit.object_storage import ObjectDoesNotExistError, TSObjectStorage


@attr.s
class UploadObject:
    filepath: Path = attr.ib()
    hash: str = attr.ib()


class ObjectUploader:
    def __init__(self, ts_object: TSObjectStorage):
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._ts_object = ts_object
        max_workers: Optional[int] = settings.get("max_workers")
        self._upload_pool = ThreadPoolExecutor(thread_name_prefix="upload-pool", max_workers=max_workers)
        # cache container object per thread
        self._th_local = local()
        # give human readable worker count for each worker
        self._tid_to_number: Dict[int, int] = {}
        # future to upload object
        self._fut_to_upobj: Dict[Future, UploadObject] = {}
        # if any exception was raised by one of the future
        self._has_exception: Optional[BaseException] = None

    def __enter__(self):
        self._upload_pool.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._upload_pool.__exit__(exc_type, exc_val, exc_tb)

    def submit(self, filepath: Path, hash: str):
        object = UploadObject(filepath, hash)
        future: Future = self._upload_pool.submit(self._storage_upload, object)
        self._fut_to_upobj[future] = object
        future.add_done_callback(self._check_upload_result)

    def wait(self):
        """Wait for the pool to terminate"""
        self.__exit__(None, None, None)

    def _check_upload_result(self, future: Future):
        """Checks the result of the Future object and logs the error if any"""
        upload_object = self._fut_to_upobj[future]
        exception = future.exception()
        if exception is not None:
            # TODO: how to cancel insertion
            self._logger.warning(f"Failed to upload {upload_object}: {exception}")
            # lock the thread before updating the variable
            # it will be checked by another thread
            with Lock():
                self._has_exception = exception
        # remove entry in dict
        del self._fut_to_upobj[future]

    def check_exception(self):
        """Checks if any exception was raised by one of the future, and raise it"""
        if self._has_exception is not None:
            raise self._has_exception

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

    def _storage_upload(self, to_upload_obj: UploadObject):
        """pipeline stage to upload a given object to the object storage"""
        # get per-thread object storage instance
        obj_adapter = self._ts_object.instance
        tid = get_ident()
        try:
            worker_number = self._tid_to_number[tid]
        except KeyError:
            self._tid_to_number[tid] = len(self._tid_to_number) + 1
            worker_number = self._tid_to_number[tid]

        # get container
        container = self._get_container()

        # upload to object storage if necessary
        obj_name = to_upload_obj.hash
        try:
            obj_adapter.get_object(container, obj_name)
        except ObjectDoesNotExistError:
            # get an IO object from filepath, depending on file type
            with filepath_merkle_ctx(to_upload_obj.filepath) as io:
                read_chunk_iter = iter(partial(io.read, BUFFER_SIZE), b"")
                obj_adapter.upload_object_via_stream(read_chunk_iter, container, obj_name)
            self._logger.debug("[%s]%s Uploaded", worker_number, to_upload_obj.hash)
        else:
            self._logger.debug("[%s]%s Exists", worker_number, to_upload_obj.hash)
        return True
