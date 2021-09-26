"""
Test the Neogit service class
"""
from functools import reduce

import pytest

from neogit.config import settings
from tests.data.fs.conftest import TEST_DATA_FS, TestFSRoot
from tests.model import Branch, Commit

# commit
# --------------

# Multiple factors to test here
# branches:
# - test branch is created
# - test branch is updated to the new commit


def test_branch_is_created(neogit_init):
    neogit = neogit_init
    commit_name = "first commit"
    neogit.commit(commit_name, TEST_DATA_FS.dir_empty.path)
    # assert
    branch = Branch.nodes.get(name=settings.branch)
    assert branch is not None
    # ensure track relationship exists
    assert len(branch.tracks) == 1


def test_branch_is_updated(neogit_init):
    neogit = neogit_init
    old_commit_name = "first_commit"
    neogit.commit(old_commit_name, TEST_DATA_FS.dir_empty.path)
    branch = Branch.nodes.get(name=settings.branch)
    old_commit = branch.tracks[0]
    # recapture
    new_commit_name = "second commit"
    neogit.commit(new_commit_name, TEST_DATA_FS.dir_empty.path)
    # assert
    branch.refresh()
    new_commit = branch.tracks[0]
    assert old_commit != new_commit


# commits:
# - test that commit is created
# - test that a new commit is created on second capture

# TODO
# how to test commit sha1sum ? it depends on the date at time when the commit is created hard to test
# how to test commit date ?


def test_commit_is_created(neogit_init):
    neogit = neogit_init
    commit_name = "first commit"
    neogit.commit(commit_name, TEST_DATA_FS.dir_empty.path)
    commit = Commit.nodes.get(name=commit_name)
    # assert
    assert commit.name == commit_name
    assert len(commit.sha1sum) == 40
    assert commit.date != ""


def test_new_commit_is_created(neogit_init):
    neogit = neogit_init
    # create first commit
    prev_commit_name = "first commit"
    neogit.commit(prev_commit_name, TEST_DATA_FS.dir_empty.path)
    prev_commit = Commit.nodes.get(name=prev_commit_name)
    # create second commit
    new_commit_name = "second commit"
    neogit.commit(new_commit_name, TEST_DATA_FS.dir_empty.path)
    new_commit = Commit.nodes.get(name=new_commit_name)
    # assert
    assert new_commit.name == new_commit_name
    assert len(new_commit.sha1sum) == 40
    assert new_commit.date != ""
    assert new_commit.previous[0] == prev_commit


def gen_pytest_param_test_data_fs():
    """simple generator to get nice test name displayed in pytest parametrize"""
    for test_name, fs_root in TEST_DATA_FS.__dict__.items():
        yield pytest.param(fs_root, id=test_name)


# filesystems:
# - test that filesystem is created
# - test that same filesystem captured twice is pointed to by the new commit
@pytest.mark.parametrize("fs_root", list(gen_pytest_param_test_data_fs()))
def test_commit_filesystem_data_fs(neogit_init, fs_root: TestFSRoot):
    neogit = neogit_init
    commit_name = "first commit"
    neogit.commit(commit_name, fs_root.path)
    commit = Commit.nodes.get(name=commit_name)
    assert len(commit.filesystem) == 1
    assert commit.filesystem[0].asdict() == fs_root.tree.asdict()


# get_object_size
def test_get_object_size(neogit_init):
    neogit = neogit_init
    neogit.commit("first commit", TEST_DATA_FS.dir_one_file.path)
    first_child_blob = next(iter(TEST_DATA_FS.dir_one_file.tree.children_blob.values()))
    size = neogit.get_object_size(first_child_blob.sha1sum)
    assert size == 75146


# download_object_as_stream
def test_download_object_as_stream(neogit_init):
    neogit = neogit_init
    neogit.commit("first commit", TEST_DATA_FS.dir_one_file.path)
    first_child_blob_name, first_child_blob = next(iter(TEST_DATA_FS.dir_one_file.tree.children_blob.items()))
    file_content = reduce(lambda a, b: a + b, neogit.download_object_as_stream(first_child_blob.sha1sum))
    with open(TEST_DATA_FS.dir_one_file.path / first_child_blob_name, "rb") as f:
        assert file_content == f.read()
