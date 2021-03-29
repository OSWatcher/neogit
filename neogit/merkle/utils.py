"""This module contains utils functions to build a MerkleTree"""

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
                tree.children_blobs.add(blob, name=entry.name)
            if entry.is_dir(follow_symlinks=False):
                entry_path = Path(entry.path)
                assert entry_path in tree_fs
                tree.children_trees.add(tree_fs[entry_path], name=entry.name)
                # remove entry from tree_fs to save RAM
                del tree_fs[entry_path]
        # compute final hash for tree
        hasher = Hasher()
        # IMPORTANT: sort the keys before using them
        # directories first, then files
        for _parent, (_rel_type, rel_props), child in sorted(
            tree.children_trees.triples(), key=lambda tup: tup[1][1]["name"]
        ):
            data = f"{rel_props['name']}{child.sha1sum}\n"
            hasher.string(data.encode())
        for _parent, (_rel_type, rel_props), child in sorted(
            tree.children_blobs.triples(), key=lambda tup: tup[1][1]["name"]
        ):
            data = f"{rel_props['name']}{child.sha1sum}\n"
            hasher.string(data.encode())
        tree.sha1sum = hasher.digest()
        return tree
