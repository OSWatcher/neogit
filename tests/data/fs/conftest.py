"""
It's not possible to use neomodel to build a local subgraph.
Instead we are creating dataclasses to represent Trees and Blobs,
and implement an asdict method to generate a dictionary representation.

The same is done on the neomodel Tree StructuredNode, and both dict are
compared in the integration tests
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Union

CUR_DIR = Path(__file__).resolve().parent


@dataclass
class TestBlob:
    sha1sum: str


@dataclass
class TestTree:
    sha1sum: str
    children_tree: Dict[str, "TestTree"] = field(default_factory=dict)
    children_blob: Dict[str, TestBlob] = field(default_factory=dict)

    def asdict(self) -> Dict[str, Union[str, Dict]]:
        """Represents the tree as a dictionary"""
        content = {}
        for child_name, child_tree in self.children_tree.items():
            content[child_name] = {"sha1sum": child_tree.sha1sum, "content": child_tree.asdict()}
        for child_name, child_blob in self.children_blob.items():
            content[child_name] = child_blob.sha1sum
        return {"sha1sum": self.sha1sum, "content": content}


@dataclass
class TestFSRoot:
    """Represents a test filesystem root directory"""

    # make pytest ignore this class
    __test__ = False
    path: Path
    tree: TestTree


@dataclass(init=False)
class TestDataFsDir:
    """Represents all tests filesystems available"""

    dir_empty = TestFSRoot
    dir_one_file = TestFSRoot
    dir_one_subdir = TestFSRoot


TEST_DATA_FS = TestDataFsDir()
# dir_empty
TEST_DATA_FS.dir_empty = TestFSRoot(CUR_DIR / "dir_empty", TestTree(sha1sum="da39a3ee5e6b4b0d3255bfef95601890afd80709"))
# dir_one_file
tree = TestTree(sha1sum="0032782e6f3381866532878f1bd3c1405203fff7")
file_raw_blob = TestBlob(sha1sum="4c4e3587ef717dff0d533394483cd5d5feaa983a")
tree.children_blob["file.raw"] = file_raw_blob
TEST_DATA_FS.dir_one_file = TestFSRoot(CUR_DIR / "dir_one_file", tree)
# dir_one_subdir
subdir_tree = TestTree(sha1sum="da39a3ee5e6b4b0d3255bfef95601890afd80709")
tree = TestTree(sha1sum="ac7b58cb43a320c493188b1a976a27f94a4e53ea")
tree.children_tree["subdir"] = subdir_tree
TEST_DATA_FS.dir_one_subdir = TestFSRoot(CUR_DIR / "dir_one_subdir", tree)
