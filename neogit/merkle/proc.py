import logging
import os
import pickle
import traceback
from multiprocessing import Process, Queue
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Set

from neogit.merkle.utils import merkelize_dir
from neogit.model import Tree


class MerkleWorker(Process):
    def __init__(self, root: Path, queue: Queue, **kwargs):
        if not root.exists():
            raise ValueError(f"root dir {root} does not exists")
        self._root = root
        self._queue: Queue = queue
        self._visited: Set[Path] = set()
        self._stack: List[Path] = []
        self._tree_fs: Dict[Path, Tree] = {}
        self._logger = logging.getLogger(f"{MerkleWorker.__class__.__module__}.{MerkleWorker.__class__.__name__}")
        super().__init__(**kwargs)

    def run(self):
        try:
            root_node: Tree = self.dfs_iter()
        except Exception:
            f = traceback.format_exc()
            self._logger.warning("[%s] %s", self.name, f)
        else:
            with NamedTemporaryFile(delete=False) as f:
                pickle.dump(root_node, f)
                f.flush()
                self._logger.debug("[%s] PUSH RESULTS (%s)", self.name, f.name)
                self._queue.put(f.name)
                self._logger.debug("[%s] QUIT !", self.name)

    def dfs_iter(self) -> Tree:
        self._stack.append(self._root)
        while self._stack:
            cur_dir = self._stack.pop()

            if cur_dir not in self._visited:
                # visit DFS
                self._stack.append(cur_dir)

                with os.scandir(cur_dir) as it:
                    dirs = [entry for entry in it if entry.is_dir(follow_symlinks=False)]
                    for entry in dirs:
                        path_entry = Path(entry.path)
                        self._stack.append(path_entry)
                self._visited.add(cur_dir)
            else:
                tree_node: Tree = merkelize_dir(cur_dir, self._tree_fs)
                # add to fs
                self._tree_fs[cur_dir] = tree_node
                self._logger.debug("[%s] 📁 %s : %s", self.name, cur_dir, tree_node.sha1sum)
                self._visited.remove(cur_dir)
        return self._tree_fs[self._root]
