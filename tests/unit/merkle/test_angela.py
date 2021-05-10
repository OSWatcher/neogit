from pathlib import Path
from pytest import fixture, set_trace

from neogit.merkle.angela import MerkleFSTree
from neogit.model import Tree
from more_itertools import consume


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

# def test_merkelize_current_neogit_repo():
#     root = Path("/home/wenzel/Projets/neogit")
#     tree = MerkleFSTree(root)
#     tree.merkelize()
