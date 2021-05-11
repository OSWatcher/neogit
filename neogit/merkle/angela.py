import logging
import os
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Dict, Iterator, Optional, Tuple

from more_itertools import partition

from neogit.config import settings
from neogit.merkle.pipeline import MerklePipeline
from neogit.merkle.utils import merkelize_dir
from neogit.model import Tree
from neogit.object_storage import TSObjectStorage


class MerkleFSTree:
    def __init__(self, root_fs: Path, ts_object: TSObjectStorage):
        if not root_fs.exists():
            raise ValueError(f"root {root_fs} does not exists")
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._max_workers: Optional[int] = settings.get("max_workers")
        self._root: Path = root_fs

        self._expl_thread = Thread(target=self._explore_dfs, args=(self._root,), name="explore")
        self._pipeline = MerklePipeline(ts_object)
        self._task_queue: Queue = Queue()
        self._tree_fs: Dict[Path, Tree] = {}

    @property
    def root_tree(self):
        return self._tree_fs[self._root]

    def merkelize(self) -> Iterator[Tree]:
        self._expl_thread.start()
        while True:
            task = self._task_queue.get()
            if task is None:
                break
            cur_dir, pipeline_task = task
            filename_to_sha1: Dict[str, str] = self._pipeline.get_task_result(pipeline_task)
            tree: Tree = merkelize_dir(cur_dir, filename_to_sha1, self._tree_fs)
            self._logger.debug("📁 %s: %s", cur_dir, tree.sha1sum)
            yield tree
            # update tree_fs
            self._tree_fs[cur_dir] = tree
        self._expl_thread.join()

    def _explore_dfs(self, cur_dir: Path):
        self._explore_dfs_rec(cur_dir)
        # stop consuming tasks
        self._task_queue.put(None)

    def _explore_dfs_rec(self, cur_dir: Path):
        with os.scandir(cur_dir) as it:
            files, dirs = partition(lambda item: item.is_dir(follow_symlinks=False), it)
            # start by exploring DFS
            for d in dirs:
                subdir_path = Path(d.path)
                self._explore_dfs_rec(subdir_path)
            # submit the files to the pipeline
            filename_list = [e.name for e in files]
            pipeline_task: str = self._pipeline.submit(cur_dir, filename_list)
            # create new task and put it to the queue
            task: Tuple[Path, str] = (cur_dir, pipeline_task)
            self._task_queue.put(task)
