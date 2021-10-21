"""Testing the NeoMerkleTreeBuilder

This class will start merkelizing a given node, in a thread, thanks to
the NodeVisitorThread, while uploading any relevant object in the object storage,
and merging any Tree in Neo4j"""

from pathlib import Path
from unittest.mock import patch

from neogit.core.model import FSDirectoryNode
from neogit.merkle import NeoMerkleTreeBuilder


@patch("neogit.merkle.visitor.Tree", autospec=True)
@patch("neogit.merkle.visitor.Blob", autospec=True)
def test_that_no_hang(mocked_blob, mocked_tree, fs, fake_ts_object_storage, root_fs):
    # arrange
    node = FSDirectoryNode(Path("/"))
    # act
    with NeoMerkleTreeBuilder(fake_ts_object_storage, node) as builder:
        builder.run()
    # assert
