# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

"""End-to-end cross-check of ``neogit diff`` against real ``git diff``.

Each diffed commit pair is its own parametrized test, so the test report lists one
line per transition (with the commit's short hash and summary in the test id).

Two flavours share the same comparison logic:

* ``test_synthetic_repo`` builds a small git repository on the fly and always runs --
  it keeps the diff engine honest in CI without any external state. One test per
  built-in state transition.
* ``test_real_repo`` points neogit at *your own* git repository. It is skipped
  unless you pass ``--repo``::

      poetry run pytest tests/e2e/test_diff.py::test_real_repo \\
          -k "FakeObjectStorage and workers-01" \\
          --persistdb --repo=/path/to/your/repo --repo-commits=30

  Every consecutive pair of (oldest-first) commits becomes an independent test that
  archives both trees, captures them with neogit, and checks that everything
  ``git diff`` reports is reproduced by ``neogit diff``. A fun way to watch neogit
  replay the history of a real project, commit by commit.

The comparison is one-directional (git changes are a subset of neogit's output):
neogit additionally emits directory entries, which git cannot track, so we only
check that nothing git sees is missing from neogit -- not the reverse.
"""
import re
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest
from git import Repo

from neogit.model import DiffStatus

# Sequence of full filesystem states for the synthetic repo; consecutive states are diffed.
STATES = [
    {
        "a.txt": "one",
        "src/main.c": "int main(void) { return 0; }\n",
        "docs/readme.md": "hello\n",
    },
    {
        # a.txt modified, src/util.c added, docs/readme.md unchanged
        "a.txt": "ONE changed",
        "src/main.c": "int main(void) { return 0; }\n",
        "src/util.c": "void util(void) {}\n",
        "docs/readme.md": "hello\n",
    },
    {
        # docs/readme.md deleted, nested file added, src/main.c modified
        "a.txt": "ONE changed",
        "src/main.c": "int main(void) { return 1; }\n",
        "src/util.c": "void util(void) {}\n",
        "src/deep/nested/x.h": "#pragma once\n",
    },
    {
        # src/util.c deleted, whole docs/ dir re-added, b.txt added
        "a.txt": "ONE changed",
        "src/main.c": "int main(void) { return 1; }\n",
        "src/deep/nested/x.h": "#pragma once\n",
        "docs/guide.md": "a guide\n",
        "b.txt": "two",
    },
]


def _slug(text: str, length: int = 24) -> str:
    """Filesystem/pytest-id friendly slug of a commit summary."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip())[:length].strip("-")
    return slug or "nomsg"


def _sync_worktree(repo_path: Path, files: dict) -> None:
    """Make the working tree match ``files`` exactly (write/overwrite + delete)."""
    for existing in repo_path.rglob("*"):
        if existing.is_file() and ".git" not in existing.parts:
            rel = existing.relative_to(repo_path).as_posix()
            if rel not in files:
                existing.unlink()
    for rel, content in files.items():
        p = repo_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def _init_repo(repo_path: Path) -> Repo:
    repo = Repo.init(repo_path)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "neogit test")
        cw.set_value("user", "email", "test@example.com")
    return repo


def _capture_commit(neogit, repo: Repo, hexsha: str, message: str) -> str:
    """git archive a commit, extract it, and capture it with neogit. Return neogit hash."""
    with TemporaryDirectory() as extract_dir, NamedTemporaryFile(suffix=".tar") as archive:
        repo.archive(archive, format="tar", treeish=hexsha)
        archive.flush()
        subprocess.run(["tar", "-xf", archive.name, "-C", extract_dir], check=True)
        return neogit.commit(message, Path(extract_dir))


def _git_change_path(diff_obj) -> str:
    # 'A' sets b_path, 'D' sets a_path, 'M' sets both; prefer whichever is present.
    return diff_obj.b_path or diff_obj.a_path


def _assert_git_subset_of_neogit(repo: Repo, base_hex: str, diffee_hex: str, neogit_diff: list) -> None:
    """Assert every file git reports changed is reproduced by neogit (with matching status)."""
    git_diff = repo.commit(base_hex).diff(repo.commit(diffee_hex))
    # neogit reports both dirs and files; git only files -> compare against files
    neo_files = {(d.path, d.status) for d in neogit_diff if not d.is_dir}
    for change_type, status in (("A", DiffStatus.NEW), ("D", DiffStatus.DEL), ("M", DiffStatus.MOD)):
        for diff_obj in git_diff.iter_change_type(change_type):
            if getattr(diff_obj, "renamed_file", False):
                # iter_change_type("M") can also surface renames; skip those.
                continue
            git_path = _git_change_path(diff_obj)
            expected = Path("/") / git_path
            assert (expected, status) in neo_files, (
                f"{base_hex[:7]}..{diffee_hex[:7]}: git {status.name} {git_path!r} "
                f"missing from neogit diff {sorted((str(p), s.name) for p, s in neo_files)}"
            )


def pytest_generate_tests(metafunc):
    """Turn a real git repo's commit pairs into one parametrized test each.

    Reads ``--repo`` / ``--repo-commits`` at collection time. Without ``--repo`` a
    single skipped placeholder is emitted.
    """
    if "real_commit_pair" not in metafunc.fixturenames:
        return
    repo_path = metafunc.config.getoption("repo")
    if repo_path is None:
        metafunc.parametrize(
            "real_commit_pair",
            [pytest.param(None, marks=pytest.mark.skip(reason="pass --repo=<git repo> to run this cross-check"))],
        )
        return
    limit = metafunc.config.getoption("repo_commits")
    repo = Repo(repo_path)
    commits = list(reversed(list(repo.iter_commits())))[:limit]  # oldest-first, capped
    params = []
    for index, (base, diffee) in enumerate(zip(commits, commits[1:])):
        test_id = f"{index:03d}-{diffee.hexsha[:8]}-{_slug(diffee.summary)}"  # noqa: E231
        params.append(pytest.param((base.hexsha, diffee.hexsha), id=test_id))
    if not params:
        params = [pytest.param(None, marks=pytest.mark.skip(reason="need at least two commits to diff"))]
    metafunc.parametrize("real_commit_pair", params)


@pytest.fixture
def git_repo(arg_repo_root):
    return Repo(arg_repo_root) if arg_repo_root is not None else None


@pytest.mark.parametrize(
    "state_index",
    range(len(STATES) - 1),
    ids=[f"state{i}-to-state{i + 1}" for i in range(len(STATES) - 1)],
)
def test_synthetic_repo(neogit_init, tmp_path, state_index):
    """Diff one built-in state transition (a fresh 2-commit repo) against neogit."""
    repo_path = tmp_path / "gitrepo"
    repo_path.mkdir()
    repo = _init_repo(repo_path)

    hexshas = []
    for state in (STATES[state_index], STATES[state_index + 1]):
        _sync_worktree(repo_path, state)
        repo.git.add(A=True)
        repo.git.commit(m=f"state {len(hexshas)}")
        hexshas.append(repo.head.commit.hexsha)

    base_neo = _capture_commit(neogit_init, repo, hexshas[0], "base")
    diffee_neo = _capture_commit(neogit_init, repo, hexshas[1], "diffee")
    neogit_diff = list(neogit_init.diff(base_neo, diffee_neo))
    _assert_git_subset_of_neogit(repo, hexshas[0], hexshas[1], neogit_diff)


def test_real_repo(neogit_init, git_repo, real_commit_pair):
    """Cross-check one commit pair of a real git repo (via ``--repo``) against neogit."""
    base_hex, diffee_hex = real_commit_pair
    base_neo = _capture_commit(neogit_init, git_repo, base_hex, base_hex)
    diffee_neo = _capture_commit(neogit_init, git_repo, diffee_hex, diffee_hex)
    neogit_diff = list(neogit_init.diff(base_neo, diffee_neo))
    _assert_git_subset_of_neogit(git_repo, base_hex, diffee_hex, neogit_diff)
