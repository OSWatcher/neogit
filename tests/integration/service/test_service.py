"""
Test the Neogit service class
"""
from pytest import fixture

from neogit.config import settings
from neogit.object_storage import FakeObjectStorage, TSObjectStorage
from neogit.service import Neogit
from tests.data.fs.conftest import TEST_DATA_FS
from tests.model import Branch, Commit


@fixture(scope="function")
def neogit(clean_neo4j_db):
    """creates an instance of Neogit, inject a fake object storage as dependency"""
    ts_obj = TSObjectStorage(FakeObjectStorage, None)
    neogit = Neogit(ts_obj)
    return neogit


@fixture(scope="function")
def neogit_init(neogit):
    neogit.init()
    return neogit


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


# filesystems:
# - test that filesystem is created
# - test that same filesystem captured twice is pointed to by the new commit
