"""This module contains utils functions to build a MerkleTree"""

import os
from contextlib import contextmanager
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Dict, Iterator

from neogit.merkle.hasher import Hasher
from neogit.model import Blob, Tree

BUFFER_SIZE = 65535


@contextmanager
def filepath_merkle_ctx(filepath: Path) -> Iterator[BinaryIO]:
    """Return a binary file-like object from a filepath,
    depending on how the file should be merkelized in neogit"""
    if filepath.is_symlink():
        data = os.readlink(str(filepath)).encode()
        sio = BytesIO(data)
        yield sio
    elif filepath.is_file():
        with open(filepath, "rb") as f:
            yield f
    else:
        # empty file for now
        sio = BytesIO()
        yield sio


def iter_chunk(io: BinaryIO) -> Iterator[bytes]:
    """Simple chunk iterator reading from the io object parameter"""
    yield from iter(partial(io.read, BUFFER_SIZE), b"")


def merkelize_dir(cur_dir: Path, filename_to_sha1: Dict[str, str], tree_fs: Dict[Path, Tree]) -> Tree:
    tree: Tree = Tree()
    for filename, sha1 in filename_to_sha1.items():
        # create and insert a new Blob
        blob = Blob()
        blob.hash = sha1
        tree.children_blob[filename] = blob
    with os.scandir(cur_dir) as it:
        for subdir in filter(lambda entry: entry.is_dir(follow_symlinks=False), it):
            subdir_path = cur_dir / subdir.name
            try:
                tree.children_tree[subdir.name] = tree_fs[subdir_path]
            except KeyError:
                # dir skipped because libguestfs error
                continue
            else:
                del tree_fs[subdir_path]
    # compute final hash for tree
    hasher = Hasher()
    # IMPORTANT: sort the keys before using them
    # directories first
    for entry_name in sorted(tree.children_tree):
        child_sha1sum = tree.children_tree[entry_name].hash
        data = f"{entry_name}{child_sha1sum}\n"
        hasher.string(data.encode())
    # then files
    for entry_name in sorted(tree.children_blob):
        child_sha1sum = tree.children_blob[entry_name].hash
        data = f"{entry_name}{child_sha1sum}\n"
        hasher.string(data.encode())
    tree.hash = hasher.digest()
    return tree
