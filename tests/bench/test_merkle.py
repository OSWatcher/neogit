"""
Benchmarks for MerkleFS builder and Neogit commit
(desired) fixture parameters
- settings.max_workers
    - 1
    - None (os.cpu_count())
    - os.cpu_count() * 2
- object storage
    - None (TODO)
    - libcloud local
    - libcloud MinIO (TODO, bug with MinIO and libcloud)
- nb repeat (filesystem cache)
- clean / unclean capture (object storage)
    - clean: object storage must upload everything
    - unclean: all objects are already in object storage, just existence checks
"""


import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest
from git import Repo
from git.exc import InvalidGitRepositoryError

from neogit.core.model import FSDirectoryNode
from neogit.merkle import NeoMerkleTreeBuilder
from tests.conftest import TEST_DATA

GIT_REPO_URL = "https://github.com/qemu/qemu"
NB_REPEAT = 5


@pytest.fixture(scope="session")
def clone_git_repo():
    """clone the repo in a tests/data/cache directory"""
    repo_path = TEST_DATA / "cache" / "repo"
    repo_path.mkdir(parents=True, exist_ok=True)
    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        # need to clone
        repo = Repo.clone_from(GIT_REPO_URL, repo_path)
    # pull
    repo.git.pull("origin", "master")
    return repo


@pytest.fixture(scope="class")
def archive_git_repo(clone_git_repo):
    """archive the git repo into cache/archive.tar"""
    git_repo = clone_git_repo
    archive_path = Path(git_repo.working_dir).parent / "archive.tar"
    if not archive_path.exists():
        with open(archive_path, "wb") as archive_f:
            git_repo.archive(archive_f, format="tar")
    return archive_path


@pytest.fixture(scope="function")
def extract_archive_workdir_per_func(archive_git_repo):
    archive_path = archive_git_repo
    workdir = Path(archive_path).parent / "workdir"
    if not workdir.exists():
        workdir.mkdir()
        with tarfile.TarFile(archive_path) as tar:
            tar.extractall(workdir)
    return workdir


@pytest.fixture(scope="class")
def extract_archive_workdir_per_class(archive_git_repo):
    archive_path = archive_git_repo
    workdir = Path(archive_path).parent / "workdir"
    if not workdir.exists():
        workdir.mkdir()
        with tarfile.TarFile(archive_path) as tar:
            tar.extractall(workdir)
    return workdir


# fixture to commit a workdir in neo4j, per class


@patch("neogit.merkle.visitor.Tree", autospec=True)
@pytest.mark.parametrize("nb_repeat", range(1, NB_REPEAT + 1), ids=lambda val: f"repeat-{val}")
def test_merkle_workdir(
    mocked_tree, tmp_path, init_libcloud_object_storage_per_module, extract_archive_workdir_per_func, nb_repeat
):
    """Only test the MerkleFSTree builder speed"""
    ts_object = init_libcloud_object_storage_per_module
    workdir = extract_archive_workdir_per_func
    # arrange
    node = FSDirectoryNode(workdir)
    # act
    with NeoMerkleTreeBuilder(ts_object, node) as builder:
        builder.run()


@pytest.mark.parametrize("nb_repeat", range(1, NB_REPEAT + 1), ids=lambda val: f"repeat-{val}")
def test_commit_speed_workdir_fresh(neogit_init, extract_archive_workdir_per_func, nb_repeat):
    """Test the commit speed on a fresh workdir (nothing the graph / object DBs)"""
    neogit = neogit_init
    workdir = extract_archive_workdir_per_func
    neogit.commit("first commit", workdir)


class TestCommitSpeedAlreadyMerged:
    """
    with a class scope
    - neogit init once
    - neo4j cleanup once

    -> test speed of graph merge when whole Tree already exists
    -> TODO: object storage
    """

    @pytest.fixture(scope="class")
    def commit_workdir(self, neogit_init_per_class, extract_archive_workdir_per_class):
        """simple feature to commit a workdir"""
        neogit = neogit_init_per_class
        workdir = extract_archive_workdir_per_class
        neogit.commit("first commit", workdir)

    @pytest.mark.parametrize("nb_repeat", range(1, NB_REPEAT + 1), ids=lambda val: f"repeat-{val}")
    def test_speed_commit_workdir_already_merged(
        self, neogit_init_per_class, extract_archive_workdir_per_func, commit_workdir, nb_repeat
    ):
        """commit the workdir, and test the commit speed since the graph has already been merged"""
        neogit = neogit_init_per_class
        workdir = extract_archive_workdir_per_func
        neogit.commit("first commit", workdir)
