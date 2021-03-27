import hashlib
import logging
import os
import pickle
import traceback
from multiprocessing import Process, Queue
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Set

from neogit.model import BlobNode, PathLike, TreeNode


def compute_sha1(filepath: PathLike) -> str:
    """Compute SHA1 sum from filepath"""
    sha1 = hashlib.sha1()
    buffer = bytearray(65536)
    view = memoryview(buffer)
    # no need to buffering, we read the data once
    with open(filepath, "rb", buffering=0) as f:
        # readinto avoid temporary buffers
        for block_size in iter(lambda: f.readinto(view), 0):  # type: ignore
            sha1.update(view[:block_size])
    return sha1.hexdigest()


def merkelize_file(filepath: PathLike) -> BlobNode:
    """Create a BlobNode from a single file"""
    blob = BlobNode()
    sha1sum = compute_sha1(filepath)
    blob.sha1sum = sha1sum
    return blob


def merkelize_dir(directory: Path, tree_fs: Dict[Path, TreeNode]) -> TreeNode:
    """
    Convert a directory to a Merkel TreeNode object, given its subdirectories associated
    TreeNodes in tree_fs

    params:
        directory: the directory to merkelize
        tree_fs: the dict children filename -> TreeNode

    return:
        TreeNode
    """
    with os.scandir(directory) as it:
        tree = TreeNode()
        for entry in it:
            if entry.is_file():
                blob: BlobNode = merkelize_file(entry.path)
                # add to treenode
                tree.children[entry.name] = blob
            if entry.is_dir(follow_symlinks=False):
                entry_path = Path(entry.path)
                assert entry_path in tree_fs
                tree.children[entry.name] = tree_fs[entry_path]
                # remove entry from tree_fs to save RAM
                del tree_fs[entry_path]
        # compute final hash for tree
        hashsum = hashlib.sha1()
        for child_name, child_node in tree.children.items():
            data = f"{child_name}{child_node.sha1sum}\n".encode()
            hashsum.update(data)
        tree.sha1sum = hashsum.hexdigest()
        return tree


class MerkleWorker(Process):
    def __init__(self, root: Path, queue: Queue, **kwargs):
        if not root.exists():
            raise ValueError(f"root dir {root} does not exists")
        self._root = root
        self._queue: Queue = queue
        self._visited: Set[Path] = set()
        self._stack: List[Path] = []
        self._tree_fs: Dict[Path, TreeNode] = {}
        self._logger = logging.getLogger(f"{MerkleWorker.__class__.__module__}.{MerkleWorker.__class__.__name__}")
        super().__init__(**kwargs)

    def run(self):
        try:
            root_node: TreeNode = self.dfs_iter()
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

    def dfs_iter(self) -> TreeNode:
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
                tree_node: TreeNode = merkelize_dir(cur_dir, self._tree_fs)
                # add to fs
                self._tree_fs[cur_dir] = tree_node
                self._logger.debug("[%s] 📁 %s : %s", self.name, cur_dir, tree_node.sha1sum)
                self._visited.remove(cur_dir)
        return self._tree_fs[self._root]
