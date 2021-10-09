"""Some unit tests for the Visitor implementation of our MerkleTree"""

from pathlib import Path
from typing import Dict, Iterator, Union

import attr
import pytest
from pytest import fixture

from neogit.domain import FSDirectoryNode, MerkleNode
from neogit.merkle import MerkleVisitor

EMPTY_SHA1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"


@attr.s
class VirtualFSBlob:
    content: bytes = attr.ib()


@attr.s
class VirtualFSDirectory:
    merkeled_node: MerkleNode = attr.ib()
    children: Dict[str, Union["VirtualFSDirectory", VirtualFSBlob]] = attr.ib(factory=dict)


def gen_root_fs() -> Iterator[VirtualFSDirectory]:
    """This generator will yield every filesystem representation for each
    test that we want to perform on the MerkleTree generator.

    Each VirtualFSDirectory also contains its merkle_node representation"""
    # root
    root_merkle_node = MerkleNode(EMPTY_SHA1)
    root_dir = VirtualFSDirectory(root_merkle_node)
    yield pytest.param(root_dir, id="empty_dir")
    # one subdirectory
    subdir1_merkle_node = MerkleNode(EMPTY_SHA1)
    subdir1 = VirtualFSDirectory(subdir1_merkle_node)
    root_dir.merkeled_node.hash = "ac7b58cb43a320c493188b1a976a27f94a4e53ea"
    root_dir.children["subdir1"] = subdir1
    yield pytest.param(root_dir, id="one_subdir")
    # one file
    one_file_merkle_node = MerkleNode(EMPTY_SHA1)
    one_file_blob = VirtualFSBlob(b"")
    root_dir.children.clear()
    root_dir.children["one_file"] = one_file_blob
    root_dir.merkeled_node.hash = "b506c80ee672b2f4971b25ca8ddad8fbd1e7281f"
    root_dir.merkeled_node.children.clear()
    root_dir.merkeled_node.children["one_file"] = one_file_merkle_node
    yield pytest.param(root_dir, id="one_file")


@fixture(params=list(gen_root_fs()))
def root_fs(fs, request):
    root_dir: VirtualFSDirectory = request.param

    def build_fs(directory: VirtualFSDirectory, current_path: Path):
        """Build a filesystem recursively from it's representation"""
        # build current dir
        current_path.mkdir(exist_ok=True)
        # build children
        for child_name, child in directory.children.items():
            child_path = current_path / child_name
            if isinstance(child, VirtualFSBlob):
                child_path.touch()
            else:
                build_fs(child, child_path)

    build_fs(root_dir, Path("/"))
    return root_dir.merkeled_node


def test_merklevisitor_root_fs(root_fs):
    # arrange
    expected_root_merkle = root_fs
    root_fs_node = FSDirectoryNode(Path("/"))
    merkle_vs = MerkleVisitor()
    # act
    root_merkle = merkle_vs.visit(root_fs_node)
    # assert
    assert root_merkle, expected_root_merkle
