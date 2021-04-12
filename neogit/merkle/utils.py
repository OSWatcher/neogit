"""This module contains utils functions to build a MerkleTree"""

import logging
import os
from pathlib import Path
from typing import Dict

from neogit.merkle.hasher import Hasher
from neogit.model import Blob, Tree


def merkelize_file(filepath: Path) -> Blob:
    """Create a BlobNode from a single file"""
    blob = Blob()
    hasher = Hasher()
    filepath = Path(filepath)
    sha1sum = hasher.filepath(filepath).digest()
    blob.sha1sum = sha1sum
    return blob


def merkelize_dir(directory: Path, tree_fs: Dict[Path, Tree]) -> Tree:
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
        tree = Tree()
        for entry in it:
            if entry.is_file():
                blob: Blob = merkelize_file(Path(entry.path))
                # add to treenode
                tree.children_blob[entry.name] = blob
            if entry.is_dir(follow_symlinks=False):
                entry_path = Path(entry.path)
                assert entry_path in tree_fs
                tree.children_tree[entry.name] = tree_fs[entry_path]
                # remove entry from tree_fs to save RAM
                del tree_fs[entry_path]
        # compute final hash for tree
        hasher = Hasher()
        # IMPORTANT: sort the keys before using them
        # directories first
        for entry_name in sorted(tree.children_tree):
            child_sha1sum = tree.children_tree[entry_name].sha1sum
            logging.debug(child_sha1sum)
            data = f"{entry_name}{child_sha1sum}\n"
            hasher.string(data.encode())
        logging.debug(hasher.digest())
        # then files
        for entry_name in sorted(tree.children_blob):
            child_sha1sum = tree.children_blob[entry_name].sha1sum
            data = f"{entry_name}{child_sha1sum}\n"
            hasher.string(data.encode())
        tree.sha1sum = hasher.digest()
        return tree
