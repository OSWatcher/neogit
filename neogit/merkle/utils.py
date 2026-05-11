"""IO utilities used while building a MerkleTree"""

import os
from contextlib import contextmanager
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterator

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
