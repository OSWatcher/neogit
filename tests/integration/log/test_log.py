# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest


def _make_fs(root: Path, files: dict) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for relpath, content in files.items():
        p = root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return root


def test_log_returns_commits_newest_first(neogit_init, tmp_path):
    branch = "master"
    h1 = neogit_init.commit("snap-1", _make_fs(tmp_path / "s1", {"a.txt": "1"}), branch_name=branch)
    h2 = neogit_init.commit("snap-2", _make_fs(tmp_path / "s2", {"a.txt": "2"}), branch_name=branch)
    h3 = neogit_init.commit("snap-3", _make_fs(tmp_path / "s3", {"a.txt": "3"}), branch_name=branch)

    commits = neogit_init.log(branch)

    assert [c.hash for c in commits] == [h3, h2, h1]
    assert [c.name for c in commits] == ["snap-3", "snap-2", "snap-1"]


def test_log_unknown_branch_raises_value_error(neogit_init):
    with pytest.raises(ValueError, match="does-not-exist"):
        neogit_init.log("does-not-exist")


def test_log_only_returns_target_branch_commits(neogit_init, tmp_path):
    a = neogit_init.commit("a1", _make_fs(tmp_path / "a", {"f": "a"}), branch_name="alpha")
    b = neogit_init.commit("b1", _make_fs(tmp_path / "b", {"f": "b"}), branch_name="beta")

    alpha = neogit_init.log("alpha")
    beta = neogit_init.log("beta")

    assert [c.hash for c in alpha] == [a]
    assert [c.hash for c in beta] == [b]
