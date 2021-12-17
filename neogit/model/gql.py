from datetime import datetime

import attr

from neogit.merkle.hasher import Hasher

COMMIT_HASH_STRING = """
{name}{date}{tree_sha1}
"""


@attr.s(init=False)
class Commit:
    hash: str = attr.ib()
    name: str = attr.ib()
    date: str = attr.ib()

    def __init__(self, name: str, fs_hash: str):
        self.date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.name = name
        hasher = Hasher()
        hasher.from_bytes(COMMIT_HASH_STRING.format(name=self.name, date=self.date, tree_sha1=fs_hash).encode())
        self.hash = hasher.digest()
