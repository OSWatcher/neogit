from pathlib import Path

from neogit.merkle import MerkleFSTree


def test_bench_merkle():
    builder = MerkleFSTree(Path(""))
    for _ in builder.merkelize():
        pass
