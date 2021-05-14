import logging
import os
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Dict, Iterator, List, Optional, Tuple

from more_itertools import partition

from neogit.config import settings
from neogit.console import DEFAULT_ADAPTER, AbstractConsoleAdapter
from neogit.merkle.pipeline import MerklePipeline
from neogit.merkle.utils import merkelize_dir
from neogit.model import DirInfo, Tree
from neogit.object_storage import TSObjectStorage


class MerkleFSTree:
    def __init__(self, root_fs: Path, ts_object: TSObjectStorage, console: AbstractConsoleAdapter = DEFAULT_ADAPTER):
        if not root_fs.exists():
            raise ValueError(f"root {root_fs} does not exists")
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._max_workers: Optional[int] = settings.get("max_workers")
        self._root: Path = root_fs
        self._console = console

        self._expl_thread = Thread(target=self._explore_dfs, args=(self._root,), name="explore")
        self._pipeline = MerklePipeline(self._root, ts_object, console)
        self._task_queue: Queue = Queue()
        self._tree_fs: Dict[Path, Tree] = {}

    @property
    def root_tree(self):
        return self._tree_fs[self._root]

    def merkelize(self) -> Iterator[Tree]:
        self._expl_thread.start()
        while True:
            dir_task = self._task_queue.get()
            if dir_task is None:
                break

            dir_info, pipe_task_list = dir_task
            # update gui
            self._console.set_cur_tree(dir_info)
            # get pipeline results
            filename_to_sha1: Dict[str, str] = {}
            for task in pipe_task_list:
                filepath, sha1sum = self._pipeline.result(task)
                filename_to_sha1[filepath.name] = sha1sum
            tree: Tree = merkelize_dir(dir_info.dir, filename_to_sha1, self._tree_fs)
            self._logger.debug("📁 %s: %s", dir_info.dir, tree.sha1sum)
            yield tree
            # update gui
            self._console.advance_main_bar_progress()
            # update tree_fs
            self._tree_fs[dir_info.dir] = tree
        self._expl_thread.join()

    def _explore_dfs(self, cur_dir: Path):
        self._explore_dfs_rec(cur_dir)
        # stop consuming tasks
        self._task_queue.put(None)

    def _explore_dfs_rec(self, cur_dir: Path):
        # update progress bar early, since we know there is a new dir to process
        self._console.increase_main_bar_total()
        with os.scandir(cur_dir) as it:
            files, dirs = partition(lambda item: item.is_dir(follow_symlinks=False), it)
            # start by exploring DFS
            subdirs: List[str] = []
            for d in dirs:
                subdir_path = Path(d.path)
                subdirs.append(d.name)
                self._explore_dfs_rec(subdir_path)
            # submit the files to the pipeline
            pipe_task_list: List[str] = []
            filename_list: List[str] = []
            for f in files:
                filepath = cur_dir / f.name
                filename_list.append(f.name)
                task_id: str = self._pipeline.submit(filepath)
                pipe_task_list.append(task_id)
            # create new dir_task and put it in the queue
            dir_info = DirInfo(cur_dir, filename_list, subdirs)
            dir_task: Tuple[DirInfo, List[str]] = dir_info, pipe_task_list
            self._task_queue.put(dir_task)
