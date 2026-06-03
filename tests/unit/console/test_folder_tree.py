# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from rich.markup import escape

from neogit.console.folder_tree import FolderState, fold_file, render_folder_tree

# --- render_folder_tree -----------------------------------------------------


def test_label_shows_folder_path():
    tree = render_folder_tree("/neogit/console", hidden=0, recent=[])
    assert tree.label == "📁 /neogit/console"


def test_each_file_is_a_checked_child():
    tree = render_folder_tree("/neogit/console", hidden=0, recent=["abstract.py", "empty.py"])
    assert [child.label for child in tree.children] == ["✓ abstract.py", "✓ empty.py"]


def test_more_node_shown_when_hidden_is_positive():
    tree = render_folder_tree("/big", hidden=15, recent=["f18.py", "f19.py"])
    labels = [child.label for child in tree.children]
    assert labels == ["… (15 more)", "✓ f18.py", "✓ f19.py"]


def test_no_more_node_when_nothing_hidden():
    tree = render_folder_tree("/exact", hidden=0, recent=["f0.py", "f1.py"])
    labels = [child.label for child in tree.children]
    assert labels == ["✓ f0.py", "✓ f1.py"]


def test_folder_label_and_names_are_markup_escaped():
    # Brackets are valid in Unix paths and would otherwise be parsed as Rich tags.
    tree = render_folder_tree("/a[b]", hidden=0, recent=["x[1].py"])
    assert tree.label == f"📁 {escape('/a[b]')}"
    assert tree.children[0].label == f"✓ {escape('x[1].py')}"


# --- fold_file --------------------------------------------------------------


def test_first_file_from_initial_state():
    state = fold_file(FolderState(), "/dir", "a.py", max_visible=12)
    assert state == FolderState(folder="/dir", hidden=0, recent=("a.py",))


def test_same_folder_accumulates_files():
    state = fold_file(FolderState(folder="/dir", recent=("a.py",)), "/dir", "b.py", max_visible=12)
    assert state == FolderState(folder="/dir", hidden=0, recent=("a.py", "b.py"))


def test_new_folder_resets_state():
    prev = FolderState(folder="/dir", hidden=3, recent=("a.py", "b.py"))
    state = fold_file(prev, "/other", "c.py", max_visible=12)
    assert state == FolderState(folder="/other", hidden=0, recent=("c.py",))


def test_recent_is_bounded_and_hidden_counts_dropped_files():
    state = FolderState()
    for i in range(20):
        state = fold_file(state, "/big", f"f{i}.py", max_visible=5)
    # recent holds only the last 5; the other 15 are counted as hidden
    assert len(state.recent) == 5
    assert state.recent == ("f15.py", "f16.py", "f17.py", "f18.py", "f19.py")
    assert state.hidden == 15
