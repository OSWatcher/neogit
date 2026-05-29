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


class TestDiffTreesRecursive:
    def test_added_directory_expands(self, neogit_init, tmp_path):
        old_root = _make_fs(tmp_path / "old", {"keep.txt": "k"})
        new_root = _make_fs(
            tmp_path / "new",
            {"keep.txt": "k", "sub/a.txt": "a", "sub/deep/b.txt": "b"},
        )
        old_t = _commit_tree_hash(neogit_init, old_root, "old")
        new_t = _commit_tree_hash(neogit_init, new_root, "new")
        with neogit_init._graph_driver.session() as session:
            diffs = list(diff_trees(session, old_t, new_t, recursive=True))
        by_path = {d.path: d for d in diffs}
        assert by_path[Path("/sub")].status == DiffStatus.NEW
        assert by_path[Path("/sub")].is_dir is True
        assert by_path[Path("/sub/a.txt")].status == DiffStatus.NEW
        assert by_path[Path("/sub/deep")].is_dir is True
        assert by_path[Path("/sub/deep")].status == DiffStatus.NEW
        assert by_path[Path("/sub/deep/b.txt")].status == DiffStatus.NEW

    def test_new_directory_not_expanded_without_recursive(self, neogit_init, tmp_path):
        # recursive=False must emit only the directory entry, not its contents.
        old_root = _make_fs(tmp_path / "old", {"keep.txt": "k"})
        new_root = _make_fs(tmp_path / "new", {"keep.txt": "k", "sub/a.txt": "a", "sub/deep/b.txt": "b"})
        old_t = _commit_tree_hash(neogit_init, old_root, "old")
        new_t = _commit_tree_hash(neogit_init, new_root, "new")
        with neogit_init._graph_driver.session() as session:
            diffs = list(diff_trees(session, old_t, new_t))
        by_path = {d.path: d for d in diffs}
        assert by_path[Path("/sub")].status == DiffStatus.NEW
        assert by_path[Path("/sub")].is_dir is True
        assert Path("/sub/a.txt") not in by_path
        assert Path("/sub/deep") not in by_path

    def test_removed_directory_expands(self, neogit_init, tmp_path):
        old_root = _make_fs(tmp_path / "old", {"keep.txt": "k", "sub/a.txt": "a"})
        new_root = _make_fs(tmp_path / "new", {"keep.txt": "k"})
        old_t = _commit_tree_hash(neogit_init, old_root, "old")
        new_t = _commit_tree_hash(neogit_init, new_root, "new")
        with neogit_init._graph_driver.session() as session:
            diffs = list(diff_trees(session, old_t, new_t, recursive=True))
        by_path = {d.path: d.status for d in diffs}
        assert by_path[Path("/sub")] == DiffStatus.DEL
        assert by_path[Path("/sub/a.txt")] == DiffStatus.DEL

    def test_nested_modification(self, neogit_init, tmp_path):
        old_root = _make_fs(tmp_path / "old", {"sub/a.txt": "1", "sub/keep.txt": "k"})
        new_root = _make_fs(tmp_path / "new", {"sub/a.txt": "2", "sub/keep.txt": "k"})
        old_t = _commit_tree_hash(neogit_init, old_root, "old")
        new_t = _commit_tree_hash(neogit_init, new_root, "new")
        with neogit_init._graph_driver.session() as session:
            diffs = list(diff_trees(session, old_t, new_t, recursive=True))
        by_path = {d.path: d.status for d in diffs}
        assert by_path[Path("/sub")] == DiffStatus.MOD
        assert by_path[Path("/sub/a.txt")] == DiffStatus.MOD
        assert Path("/sub/keep.txt") not in by_path

    def test_type_change_emits_del_and_new(self, neogit_init, tmp_path):
        # "x" is a file in old, a directory in new
        old_root = _make_fs(tmp_path / "old", {"x": "iam a file"})
        new_root = _make_fs(tmp_path / "new", {"x/inside.txt": "now a dir"})
        old_t = _commit_tree_hash(neogit_init, old_root, "old")
        new_t = _commit_tree_hash(neogit_init, new_root, "new")
        with neogit_init._graph_driver.session() as session:
            diffs = list(diff_trees(session, old_t, new_t, recursive=True))
        at_x = [d for d in diffs if d.path == Path("/x")]
        statuses = {d.status for d in at_x}
        assert DiffStatus.DEL in statuses
        assert DiffStatus.NEW in statuses
        assert any(d.path == Path("/x/inside.txt") and d.status == DiffStatus.NEW for d in diffs)
