"""
Benchmarks for MerkleFS builder and Neogit commit
(desired) fixture parameters
- settings.max_workers
    - 1
    - None (os.cpu_count())
    - os.cpu_count() * 2
- object storage
    - None
    - libcloud local
    - libcloud MinIO
- nb repeat (filesystem cache)
- clean / unclean capture (object storage)
    - clean: object storage must upload everything
    - unclean: all objects are already in object storage, just existence checks
"""


import tarfile
from pathlib import Path

import pytest
from git import Repo
from git.exc import InvalidGitRepositoryError
from more_itertools import consume

from neogit.merkle import MerkleFSTree
from tests.conftest import TEST_DATA

GIT_REPO_URL = "https://github.com/qemu/qemu"
NB_REPEAT = 5


@pytest.fixture()
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


@pytest.fixture()
def archive_git_repo(clone_git_repo):
    """archive the git repo into cache/archive.tar"""
    git_repo = clone_git_repo
    archive_path = Path(git_repo.working_dir).parent / "archive.tar"
    if not archive_path.exists():
        with open(archive_path, "wb") as archive_f:
            git_repo.archive(archive_f, format="tar")
    return archive_path


@pytest.fixture()
def extract_archive_workdir(archive_git_repo):
    archive_path = archive_git_repo
    workdir = Path(archive_path).parent / "workdir"
    if not workdir.exists():
        workdir.mkdir()
        with tarfile.TarFile(archive_path) as tar:
            tar.extractall(workdir)
    return workdir


@pytest.mark.parametrize("nb_repeat", range(NB_REPEAT))
def test_merkle_workdir(tmp_path, init_libcloud_object_storage_per_module, extract_archive_workdir, nb_repeat):
    """merklize a repository"""
    ts_object = init_libcloud_object_storage_per_module
    workdir = extract_archive_workdir
    builder = MerkleFSTree(workdir, ts_object)
    consume(builder.merkelize())


@pytest.mark.parametrize("nb_repeat", range(NB_REPEAT))
def test_commit_workdir(neogit_init, extract_archive_workdir, nb_repeat):
    """commit the workdir"""
    neogit = neogit_init
    workdir = extract_archive_workdir
    neogit.commit("first commit", workdir)
