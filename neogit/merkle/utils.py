"""This module contains utils functions to build a MerkleTree"""

import os
from pathlib import Path
from typing import Dict

from neogit.merkle.hasher import Hasher
from neogit.model import BlobNode, TreeNode


def merkelize_file(filepath: Path) -> BlobNode:
    """Create a BlobNode from a single file"""
    blob = BlobNode()
    hasher = Hasher()
    filepath = Path(filepath)
    sha1sum = hasher.filepath(filepath).digest()
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
                blob: BlobNode = merkelize_file(Path(entry.path))
                # add to treenode
                tree.children[entry.name] = blob
            if entry.is_dir(follow_symlinks=False):
                entry_path = Path(entry.path)
                assert entry_path in tree_fs
                tree.children[entry.name] = tree_fs[entry_path]
                # remove entry from tree_fs to save RAM
                del tree_fs[entry_path]
        # compute final hash for tree
        hasher = Hasher()
        # IMPORTANT: sort the keys before using them
        sorted_children_filenames = sorted(tree.children.keys())
        for child_name in sorted_children_filenames:
            child_node = tree.children[child_name]
            data = f"{child_name}{child_node.sha1sum}\n"
            hasher.string(data.encode())
        tree.sha1sum = hasher.digest()
        return tree
