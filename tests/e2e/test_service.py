# from neogit.model import Branch
# from neogit.repo.py2neo import Py2NeoRepository
from neogit.service import Neogit
from tests.conftest import TEST_DATA_FS


# neogit.repo doesn't exist anymore
# def test_single_commit_dir_empty(py2neo_repo: Py2NeoRepository):
#     empty_dir_path = TEST_DATA_FS / "dir_empty"
#     neogit = Neogit(empty_dir_path, py2neo_repo)
#     branch_name = "master"
#     commit_name = "first_commit"

#     neogit.commit(commit_name)

#     # branch master should have been created
#     m = py2neo_repo.match(Branch)
#     assert m.count() == 1
#     branch = m.first()
#     assert branch.name == branch_name
#     # master should point to first commit
#     commits = list(branch.commit)
#     assert len(commits) == 1
#     commit = commits[0]
#     assert commit.name == commit_name
#     # first commit should have no previous
#     assert not list(commit.previous_commit)
#     # first commit should point to Tree node
#     trees = list(commit.filesystem)
#     assert len(trees) == 1
#     tree = trees[0]
#     # tree node should have empty dir sha1
#     assert "da39a3ee5e6b4b0d3255bfef95601890afd80709", tree.hash


# neo4j_con doesn't exist anymore
def test_neogit_commit(minio_db):
    raise AssertionError()
