# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from neogit.diff import diff_trees
from neogit.model import DiffStatus
from neogit.model.neo import Commit


def _make_fs(root: Path, files: dict, empty_dirs: tuple = ()) -> Path:
    """Create a filesystem layout under `root`. `files` maps relpath -> content."""
    root.mkdir(parents=True, exist_ok=True)
    for relpath, content in files.items():
        p = root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    for d in empty_dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    return root


def _commit_tree_hash(neogit, root: Path, name: str) -> str:
    commit_hash = neogit.commit(name, root)
    return Commit.nodes.get(hash=commit_hash).filesystem.single().hash


class TestDiffTreesDirect:
    def test_flat_changes_non_recursive(self, neogit_init, tmp_path):
        old_root = _make_fs(tmp_path / "old", {"keep.txt": "k", "gone.txt": "g", "mod.txt": "1"})
        new_root = _make_fs(tmp_path / "new", {"keep.txt": "k", "mod.txt": "2", "added.txt": "a"})
        old_t = _commit_tree_hash(neogit_init, old_root, "old")
        new_t = _commit_tree_hash(neogit_init, new_root, "new")
        with neogit_init._graph_driver.session() as session:
            diffs = list(diff_trees(session, old_t, new_t))
        by_path = {d.path: d.status for d in diffs}
        assert by_path[Path("/added.txt")] == DiffStatus.NEW
        assert by_path[Path("/gone.txt")] == DiffStatus.DEL
        assert by_path[Path("/mod.txt")] == DiffStatus.MOD
        assert Path("/keep.txt") not in by_path

    def test_empty_old_tree_reports_all_new(self, neogit_init, tmp_path):
        # Regression guard: empty old tree must still report new files.
        old_root = _make_fs(tmp_path / "old", {})  # empty root dir
        new_root = _make_fs(tmp_path / "new", {"a.txt": "a", "b.txt": "b"})
        old_t = _commit_tree_hash(neogit_init, old_root, "old")
        new_t = _commit_tree_hash(neogit_init, new_root, "new")
        with neogit_init._graph_driver.session() as session:
            diffs = list(diff_trees(session, old_t, new_t))
        statuses = {d.path.name: d.status for d in diffs}
        assert statuses.get("a.txt") == DiffStatus.NEW
        assert statuses.get("b.txt") == DiffStatus.NEW

    def test_identical_trees_empty(self, neogit_init, tmp_path):
        old_root = _make_fs(tmp_path / "old", {"a.txt": "a"})
        new_root = _make_fs(tmp_path / "new", {"a.txt": "a"})
        old_t = _commit_tree_hash(neogit_init, old_root, "old")
        new_t = _commit_tree_hash(neogit_init, new_root, "new")
        with neogit_init._graph_driver.session() as session:
            diffs = list(diff_trees(session, old_t, new_t))
        assert diffs == []
