import logging
import os
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from queue import Queue
from threading import Thread


from neogit.model import Tree
from neogit.config import settings
from neogit.merkle.utils import merkelize_file, merkelize_dir


class MerkleFSTree:
    def __init__(self, root_fs: Path):
        if not root_fs.exists():
            raise ValueError(f"root {root_fs} does not exists")
        self._logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._max_workers: Optional[int] = settings.get("max_workers")
        self._root: Path = root_fs

        self._expl_thread = Thread(target=self._explore_dfs, args=(self._root,), name="explore")
        self._sha1_pool = ThreadPoolExecutor(self._max_workers, "sha1-pool")
        self._task_queue: Queue = Queue()
        self._tree_fs: Dict[Path, Tree] = {}

    def merkelize(self) -> Tree:
        self._expl_thread.start()
        while True:
            task = self._task_queue.get()
            if task is None:
                break
            cur_dir, filename_to_future, subdir_list = task
            # wait for futures completion
            filename_to_sha1: Dict[str, str] = {}
            for file_sha1_fut in as_completed(list(filename_to_future.keys())):
                filename: str = filename_to_future[file_sha1_fut]
                filename_to_sha1[filename] = file_sha1_fut.result()
            tree: Tree = merkelize_dir(cur_dir, filename_to_sha1, subdir_list, self._tree_fs)
            self._logger.debug("📁 %s: %s", cur_dir, tree.sha1sum)
            # update tree_fs
            self._tree_fs[cur_dir] = tree
        self._expl_thread.join()
        # return root tree
        return self._tree_fs[self._root]

    def _explore_dfs(self, cur_dir: Path):
        self._explore_dfs_rec(cur_dir)
        # stop consuming tasks
        self._task_queue.put(None)

    def _explore_dfs_rec(self, cur_dir: Path):
        with os.scandir(cur_dir) as it:
            # process dirs first
            entries = list(it)
            subdir_list = []
            for subdir in [entry for entry in entries if entry.is_dir(follow_symlinks=False)]:
                subdir_list.append(subdir.name)
                subdir_path = Path(subdir.path)
                self._explore_dfs_rec(subdir_path)
            future_to_filename: Dict[Future, str] = {}
            for file in [entry for entry in entries if not entry.is_dir(follow_symlinks=False)]:
                filepath = Path(file.path)
                future = self._sha1_pool.submit(merkelize_file, filepath)
                future_to_filename[future] = filepath.name
            task: Tuple[Path, Dict[Future, str], List[str]] = (cur_dir, future_to_filename, subdir_list)
            self._task_queue.put(task)
