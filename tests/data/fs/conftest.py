from dataclasses import dataclass
from pathlib import Path

from tests.model import Tree

CUR_DIR = Path(__file__).resolve().parent


@dataclass
class TestFSRoot:
    """Represents a test filesystem root directory"""

    path: Path
    tree: Tree


@dataclass(init=False)
class TestFSDataDir:
    """Represents all tests filesystems available"""

    dir_empty = TestFSRoot


TEST_DATA_FS = TestFSDataDir()
TEST_DATA_FS.dir_empty = TestFSRoot(CUR_DIR / "dir_empty", Tree(sha1sum="da39a3ee5e6b4b0d3255bfef95601890afd80709"))
