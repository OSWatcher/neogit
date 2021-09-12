import hashlib
from typing import Union

from neogit.model import Tree

COMMIT_STRING = """
{name}{date}{tree_sha1}
"""


class Hasher:
    """Produces a hash sum"""

    def __init__(self):
        self._hash = hashlib.sha1()

    def from_io(self, io):
        buffer = bytearray(65536)
        view = memoryview(buffer)
        # readinto avoid temporary buffers
        for block_size in iter(lambda: io.readinto(view), 0):
            self._hash.update(view[:block_size])

    def string(self, string: Union[str, bytes]) -> "Hasher":
        self._hash.update(string)
        return self

    def commit(self, name, date, root_tree: Tree) -> "Hasher":
        commit_string_formatted = COMMIT_STRING.format(name=name, date=date, tree_sha1=root_tree.sha1sum)
        self._hash.update(commit_string_formatted.encode())
        return self

    def digest(self) -> str:
        return self._hash.hexdigest()
