from pathlib import Path

from more_itertools import consume
from pytest import fixture

from neogit.merkle.angela import MerkleFSTree
from neogit.model import Blob, Tree


@fixture
def root_fs(fs):
    r = Path("/root")
    r.mkdir(parents=True)
    tree = Tree()
    tree.sha1sum = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    return r, tree


def test_merkelize_empty_dir(root_fs):
    root, expected = root_fs
    builder = MerkleFSTree(root)
    consume(builder.merkelize())
    tree = builder.root_tree

    assert expected, tree


@fixture
def one_subdir_fs(root_fs):
    root, expected = root_fs
    subdir = root / "subdir1"
    subdir.mkdir(parents=True)
    tree = Tree()
    tree.sha1sum = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    expected.children_tree["subdir1"] = tree
    expected.sha1sum = "ac7b58cb43a320c493188b1a976a27f94a4e53ea"
    return root, expected


def test_merkelize_one_subdir(one_subdir_fs):
    root, expected = one_subdir_fs
    builder = MerkleFSTree(root)
    consume(builder.merkelize())
    tree = builder.root_tree

    assert expected, tree


@fixture
def multiple_subdirs_fs(root_fs):
    root, expected = root_fs
    for subdir_name in ["subdir1", "subdir2", "subdir3"]:
        subdir = root / subdir_name
        subdir.mkdir(parents=True)
        subdir_tree = Tree()
        subdir_tree.sha1sum = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        expected.children_tree[subdir_name] = subdir_tree
    expected.sha1sum = "0dc6fc1493c0c6a9d56007b436ac6a3613e5e346"
    return root, expected


def test_merkelize_multiple_subdirs(multiple_subdirs_fs):
    root, expected = multiple_subdirs_fs
    builder = MerkleFSTree(root)
    consume(builder.merkelize())
    tree = builder.root_tree

    assert expected, tree


@fixture
def one_file_fs(root_fs):
    root, expected = root_fs
    one_file = root / "file1.txt"
    one_file.touch()
    file_blob = Blob()
    file_blob.sha1sum = "4c4e3587ef717dff0d533394483cd5d5feaa983a"
    expected.children_blob["file1.txt"] = file_blob
    expected.sha1sum = "0032782e6f3381866532878f1bd3c1405203fff7"
    return root, expected


def test_merkelize_one_file(one_file_fs):
    root, expected = one_file_fs
    builder = MerkleFSTree(root)
    consume(builder.merkelize())
    tree = builder.root_tree

    assert expected, tree


# def test_merkelize_current_neogit_repo():
#     root = Path("/home/wenzel/Projets/neogit")
#     tree = MerkleFSTree(root)
#     tree.merkelize()
