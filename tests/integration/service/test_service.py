"""
Test the Neogit service class
"""
from pytest import fixture

from neogit.object_storage import FakeObjectStorage, TSObjectStorage
from neogit.service import Neogit
from tests.conftest import TEST_DATA_FS_DIR_EMPTY
from tests.model import Commit, Branch
from neogit.config import settings

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
    neogit.commit(commit_name, TEST_DATA_FS_DIR_EMPTY)
    # assert
    branch = Branch.nodes.get(name=settings.branch)
    assert branch is not None
    # ensure track relationship exists
    assert len(branch.tracks) == 1


# commits:
# - test that commit is created
# - test that a new commit is created on second capture
#
# filesystems:
# - test that filesystem is created
# - test that same filesystem captured twice is pointed to by the new commit
