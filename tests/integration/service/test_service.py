"""
Test the Neogit service class
"""
from datetime import datetime
from functools import reduce

import pytest

from neogit.config import settings
from neogit.model.neo import Branch, Commit
from tests.data.fs.conftest import TEST_DATA_FS, TestFSRoot

# commit
# --------------

# Multiple factors to test here
# branches:
# - test branch is created
# - test branch is updated to the new commit


def test_branch_is_created(neogit_init):
    neogit = neogit_init
    commit_name = "first commit"
    neogit.commit(commit_name, TEST_DATA_FS.dir_one_file.path)
    # assert
    branch = Branch.nodes.get(name=settings.branch)
    assert branch is not None
    # ensure track relationship exists
    assert len(branch.tracks) == 1


def test_branch_is_updated(neogit_init):
    neogit = neogit_init
    old_commit_name = "first_commit"
    neogit.commit(old_commit_name, TEST_DATA_FS.dir_one_file.path)
    branch = Branch.nodes.get(name=settings.branch)
    old_commit = branch.tracks[0]
    # recapture
    new_commit_name = "second commit"
    neogit.commit(new_commit_name, TEST_DATA_FS.dir_one_file.path)
    # assert
    branch.refresh()
    new_commit = branch.tracks[0]
    assert old_commit != new_commit


# commits:
# - test that commit is created
# - test that a new commit is created on second capture


def test_commit_is_created(neogit_init):
    neogit = neogit_init
    commit_name = "first commit"
    test_date = datetime(2024, 1, 15, 10, 30, 0)
    commit_hash = neogit.commit(commit_name, TEST_DATA_FS.dir_one_file.path, date=test_date)
    commit = Commit.nodes.get(name=commit_name)
    # assert
    assert commit.name == commit_name
    assert len(commit.hash) == 40
    assert commit.hash == commit_hash
    assert commit.date.replace(tzinfo=None) == test_date


def test_new_commit_is_created(neogit_init):
    neogit = neogit_init
    # create first commit
    prev_commit_name = "first commit"
    date1 = datetime(2024, 1, 15, 10, 30, 0)
    hash1 = neogit.commit(prev_commit_name, TEST_DATA_FS.dir_one_file.path, date=date1)
    prev_commit = Commit.nodes.get(name=prev_commit_name)
    # create second commit
    new_commit_name = "second commit"
    date2 = datetime(2024, 1, 16, 10, 30, 0)
    hash2 = neogit.commit(new_commit_name, TEST_DATA_FS.dir_one_file.path, date=date2)
    new_commit = Commit.nodes.get(name=new_commit_name)
    # assert
    assert new_commit.name == new_commit_name
    assert len(new_commit.hash) == 40
    assert new_commit.hash == hash2
    assert new_commit.date.replace(tzinfo=None) == date2
    assert new_commit.previous[0] == prev_commit
    # Verify different dates produce different hashes
    assert hash1 != hash2


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
    test_date = datetime(2024, 1, 15, 10, 30, 0)
    neogit.commit(commit_name, fs_root.path, date=test_date)
    commit = Commit.nodes.get(name=commit_name)
    assert len(commit.filesystem) == 1
    assert commit.filesystem[0].asdict() == fs_root.tree.asdict()
    assert commit.date.replace(tzinfo=None) == test_date


# get_object_size
def test_get_object_size(neogit_init):
    neogit = neogit_init
    neogit.commit("first commit", TEST_DATA_FS.dir_one_file.path)
    first_child_blob = next(iter(TEST_DATA_FS.dir_one_file.tree.children_blob.values()))
    size = neogit.get_object_size(first_child_blob.hash)
    assert size == 75146


# download_object_as_stream
def test_download_object_as_stream(neogit_init):
    neogit = neogit_init
    neogit.commit("first commit", TEST_DATA_FS.dir_one_file.path)
    first_child_blob_name, first_child_blob = next(iter(TEST_DATA_FS.dir_one_file.tree.children_blob.items()))
    file_content = reduce(lambda a, b: a + b, neogit.download_object_as_stream(first_child_blob.hash))
    with open(TEST_DATA_FS.dir_one_file.path / first_child_blob_name, "rb") as f:
        assert file_content == f.read()


# Custom date tests
# ------------------


def test_commit_with_custom_date(neogit_init):
    """Test that custom date is properly used in commit creation and hash calculation."""
    neogit = neogit_init
    commit_name = "dated_commit"
    custom_date = datetime(2023, 6, 15, 14, 30, 0)

    commit_hash = neogit.commit(commit_name, TEST_DATA_FS.dir_one_file.path, date=custom_date)

    commit = Commit.nodes.get(name=commit_name)
    # Neo4j stores dates with UTC timezone, so compare just the date values
    assert commit.date.replace(tzinfo=None) == custom_date
    assert commit.hash == commit_hash
    assert len(commit.hash) == 40


def test_same_commit_different_dates_different_hashes(neogit_init):
    """Test that same content with different dates produces different hashes."""
    neogit = neogit_init

    date1 = datetime(2023, 1, 1, 0, 0, 0)
    date2 = datetime(2023, 1, 2, 0, 0, 0)

    hash1 = neogit.commit("commit1", TEST_DATA_FS.dir_one_file.path, date=date1)
    hash2 = neogit.commit("commit2", TEST_DATA_FS.dir_one_file.path, date=date2)

    # Different dates should produce different hashes even with same filesystem
    assert hash1 != hash2

    # Verify dates are stored correctly (Neo4j stores with UTC timezone)
    commit1 = Commit.nodes.get(hash=hash1)
    commit2 = Commit.nodes.get(hash=hash2)
    assert commit1.date.replace(tzinfo=None) == date1
    assert commit2.date.replace(tzinfo=None) == date2


def test_commit_without_date_uses_now(neogit_init):
    """Test backward compatibility: commits without date parameter use datetime.now()."""
    neogit = neogit_init
    commit_name = "auto_dated_commit"

    # Capture time before and after
    before = datetime.now()
    commit_hash = neogit.commit(commit_name, TEST_DATA_FS.dir_one_file.path)
    after = datetime.now()

    commit = Commit.nodes.get(name=commit_name)
    # Verify the date was set automatically and is between before and after (remove timezone for comparison)
    commit_date_naive = commit.date.replace(tzinfo=None)
    assert before <= commit_date_naive <= after
    assert commit.hash == commit_hash
    assert len(commit.hash) == 40
