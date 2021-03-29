import logging
import os
import pickle
from multiprocessing import Queue
from pathlib import Path
from typing import Dict, Tuple

from neogit.merkle.proc import MerkleWorker
from neogit.merkle.utils import merkelize_dir
from neogit.model import TreeNode

DEFAULT_MAX_WORKERS = 4


def iterable_queue(queue: Queue):
    while True:
        item = queue.get()
        if item is None:
            return
        yield item


class MerkleFSTree:
    def __init__(self, root_fs: Path, max_workers: int = None):
        if not root_fs.exists():
            raise ValueError(f"root {root_fs} does not exists")
        self._logger = logging.getLogger(f"{MerkleFSTree.__module__}.{MerkleFSTree.__class__.__name__}")
        self._max_workers = max_workers if max_workers is not None else DEFAULT_MAX_WORKERS
        self._root = root_fs
        self._workers: Dict[Path, Tuple[MerkleWorker, Queue]] = {}

    def merkelize(self) -> TreeNode:
        with os.scandir(self._root) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    entry_path = Path(entry.path)
                    worker_queue: Queue = Queue()
                    worker = MerkleWorker(entry_path, worker_queue)
                    worker.start()
                    self._workers[entry_path] = (worker, worker_queue)
        tree_fs = {}
        for w_path, (worker, w_queue) in self._workers.items():
            worker.join()
            logging.debug("waiting for results from %s", worker.name)
            serial_path = w_queue.get()
            with open(serial_path, mode="rb") as f:
                node = pickle.load(f)
            os.remove(serial_path)
            logging.debug("results from %s", worker.name)
            tree_fs[w_path] = node
        root_node = merkelize_dir(self._root, tree_fs)
        logging.info("📁 %s : %s", self._root, root_node.sha1sum)
        return root_node
