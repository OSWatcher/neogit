"""This module contains utils functions to build a MerkleTree"""

import os
from pathlib import Path
from typing import Dict

from neogit.merkle.hasher import Hasher
from neogit.model import Blob, Tree


def merkelize_dir(cur_dir: Path, filename_to_sha1: Dict[str, str], tree_fs: Dict[Path, Tree]) -> Tree:
    tree: Tree = Tree()
    for filename, sha1 in filename_to_sha1.items():
        # create and insert a new Blob
        blob = Blob()
        blob.sha1sum = sha1
        tree.children_blob[filename] = blob
    with os.scandir(cur_dir) as it:
        for subdir in filter(lambda entry: entry.is_dir(follow_symlinks=False), it):
            subdir_path = cur_dir / subdir.name
            tree.children_tree[subdir.name] = tree_fs[subdir_path]
            del tree_fs[subdir_path]
    # compute final hash for tree
    hasher = Hasher()
    # IMPORTANT: sort the keys before using them
    # directories first
    for entry_name in sorted(tree.children_tree):
        child_sha1sum = tree.children_tree[entry_name].sha1sum
        data = f"{entry_name}{child_sha1sum}\n"
        hasher.string(data.encode())
    # then files
    for entry_name in sorted(tree.children_blob):
        child_sha1sum = tree.children_blob[entry_name].sha1sum
        data = f"{entry_name}{child_sha1sum}\n"
        hasher.string(data.encode())
    tree.sha1sum = hasher.digest()
    return tree
