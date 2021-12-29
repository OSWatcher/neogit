# test diffing against a git repo
#
# this module take a local git repository path, and for each commit starting from the first one on the branch
# commit the repo's content with neogit, and then compares the diff output against git ones to valides neogit diff
#
# git log
# reversed()
# git archive
# extract to tmpdir
# commit with Neogit
# git diff vs neogit diff
from itertools import islice
from pathlib import Path
from typing import Iterator, List, Optional

import pytest
import tarfile
from git import Repo, Commit
from tempfile import TemporaryDirectory, NamedTemporaryFile
import attr
from gql import Client
from gql.transport.requests import RequestsHTTPTransport

from neogit.config import settings, ObjectConfig
from neogit.model import DiffStatus
from neogit.object_storage import TSObjectStorage, LibcloudObjectStorage
from neogit.service import Neogit

LIMIT = 100


def neogit_instance():
    # GraphQL Client
    transport = RequestsHTTPTransport(settings.graphql.url, verify=True, retries=3)
    client = Client(transport=transport, fetch_schema_from_transport=True)
    # init TSObjectStorage and inject dependency
    obj_config = ObjectConfig.from_settings(settings)
    tsobj = TSObjectStorage(LibcloudObjectStorage, obj_config)
    return Neogit(tsobj, client)


@attr.s
class CommitRange:
    current: Optional[str] = attr.ib()
    previous: Optional[str] = attr.ib()

    def push(self, commithex: str):
        """push new commit, shift"""
        self.previous = self.current
        self.current = commithex


@attr.s
class GitToNeogitDiff:
    # git repo
    repo: Repo = attr.ib()
    # neogit instance
    neogit: Neogit = attr.ib()
    # git commits [previous, current]
    repo_range: CommitRange = attr.ib()
    # neogit commits [previous, current]
    neogit_range: CommitRange = attr.ib()


def gen_git_log():
    """generate a reverse git log, instiantiate GitToNeogitDiff structure and returns it as well as the next commit"""
    # how to get arg_repo_root ?
    # hardcoded for now
    repo_path = "/home/wenzel/Projets/libvmi"
    # create a git repo object
    repo = Repo(repo_path)
    neogit = neogit_instance()
    git_to_neogit_diff = GitToNeogitDiff(repo, neogit, CommitRange(None, None), CommitRange(None, None))
    for index, commit in enumerate(islice(reversed(list(repo.iter_commits())), LIMIT)):
        yield pytest.param(git_to_neogit_diff, commit, id=commit.hexsha)


@pytest.mark.parametrize("git_to_neogit_diff, commit", gen_git_log())
def test_diff_repo(git_to_neogit_diff, commit):
    """diff 2 commits in a repo
    we do the heavy work here since pytest expands all fixtures and parametrization before starting the test suite
    it was therefore not possible to create the tarball/extract/capture in the gen_git_log generator"""
    neogit = git_to_neogit_diff.neogit
    repo = git_to_neogit_diff.repo
    # archive git repo
    with TemporaryDirectory() as tmp_extract_dir:
        with NamedTemporaryFile() as tmp_archive:
            repo.archive(tmp_archive, format="tar", treeish=commit.hexsha)
            tmp_archive.flush()
            # extract it into tmp dir
            with tarfile.TarFile(tmp_archive.name) as tarball:
                tarball.extractall(tmp_extract_dir)
        extract_dir_path = Path(tmp_extract_dir)
        # capture with Neogit
        neogit_commit = neogit.commit(commit.message, extract_dir_path)
    # update git_to_neogit_diff
    git_to_neogit_diff.repo_range.push(commit.hexsha)
    git_to_neogit_diff.neogit_range.push(neogit_commit.hash)

    # skip test if no previous commit
    if git_to_neogit_diff.repo_range.previous is None or git_to_neogit_diff.neogit_range.previous is None:
        return

    # diff_git = Repo.diff()
    repo = git_to_neogit_diff.repo
    base_git = repo.commit(git_to_neogit_diff.repo_range.previous)
    diffee_git = repo.commit(git_to_neogit_diff.repo_range.current)
    git_diff = base_git.diff(diffee_git)

    # diff_neogit = Neogit.diff()
    base_neogit = git_to_neogit_diff.neogit_range.previous
    diffee_neogit = git_to_neogit_diff.neogit_range.current
    neogit_diff = list(git_to_neogit_diff.neogit.diff_commits(base_neogit, diffee_neogit))
    # compare diffs
    #   test new files
    for diff_obj in git_diff.iter_change_type("A"):
        assert [d for d in neogit_diff if d.path == diff_obj.a_path and d.status == DiffStatus.NEW]
    #   test del files
    for diff_obj in git_diff.iter_change_type("D"):
        assert [d for d in neogit_diff if d.path == diff_obj.a_path and d.status == DiffStatus.DEL]
    #   test mod files
    for diff_obj in git_diff.iter_change_type("M"):
        # iter_change_type("M") also yields renamed files (weird, is this a bug ?)
        if diff_obj.renamed:
            continue
        assert [d for d in neogit_diff if d.path == diff_obj.a_path and d.status == DiffStatus.MOD]
    # this test is not bulletproof, but gives a good harness for bugs in the diff algorithm
