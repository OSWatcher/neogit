"""This module contains utils functions to build a MerkleTree"""

import hashlib
import os
from pathlib import Path
from typing import Dict

from neogit.model import PathLike, BlobNode, TreeNode


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