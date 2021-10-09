"""Some unit tests for the Visitor implementation of our MerkleTree"""

from pathlib import Path

from neogit.core.model import FSDirectoryNode
from neogit.core.merkle import MerkleVisitor


def test_merklevisitor_root_fs(root_fs):
    # arrange
    expected_root_merkle = root_fs
    root_fs_node = FSDirectoryNode(Path("/"))
    merkle_vs = MerkleVisitor()
    # act
    root_merkle = merkle_vs.visit(root_fs_node)
    # assert
    assert root_merkle, expected_root_merkle
