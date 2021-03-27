from pathlib import Path

from neogit.merkle.angela import MerkleFSTree
from neogit.model import TreeNode
from tests.conftest import TEST_DATA_FS, ROOT_REPO


def test_merkelize_empty_dir():
    empty_dir = TEST_DATA_FS / "empty_dir"
    root = Path(empty_dir)
    tree = MerkleFSTree(root)
    tree_node: TreeNode = tree.merkelize()

    expected = TreeNode()
    expected.sha1sum = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    assert expected, tree_node


def test_merkelize_current_neogit_repo():
    root = ROOT_REPO
    tree = MerkleFSTree(root)
    tree.merkelize()
