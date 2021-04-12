import hashlib
from pathlib import Path
from typing import Union

from neogit.model import Tree

COMMIT_STRING = """
{name}{date}{tree_sha1}
"""


class Hasher:
    """Produces a hash sum"""

    def __init__(self):
        self._hash = hashlib.sha1()

    def filepath(self, filepath: Path) -> "Hasher":
        buffer = bytearray(65536)
        view = memoryview(buffer)
        # no need to buffering, we read the data once
        with open(filepath, "rb", buffering=0) as f:
            # readinto avoid temporary buffers
            for block_size in iter(lambda: f.readinto(view), 0):  # type: ignore
                self._hash.update(view[:block_size])
        return self

    def string(self, string: Union[str, bytes]) -> "Hasher":
        self._hash.update(string)
        return self

    def commit(self, name, date, root_tree: Tree) -> "Hasher":
        commit_string_formatted = COMMIT_STRING.format(name=name, date=date, tree_sha1=root_tree.sha1sum)
        self._hash.update(commit_string_formatted.encode())
        return self

    def digest(self) -> str:
        return self._hash.hexdigest()
