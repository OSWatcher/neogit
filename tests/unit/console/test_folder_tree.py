# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from neogit.console.folder_tree import next_folder_state, render_folder_tree


def test_label_shows_folder_path():
    tree = render_folder_tree("/neogit/console", [], max_visible=12)
    assert tree.label == "📁 /neogit/console"


def test_each_file_is_a_checked_child():
    tree = render_folder_tree("/neogit/console", ["abstract.py", "empty.py"], max_visible=12)
    assert [child.label for child in tree.children] == ["✓ abstract.py", "✓ empty.py"]


def test_truncates_to_last_max_visible_with_more_node():
    files = [f"f{i}.py" for i in range(20)]
    tree = render_folder_tree("/big", files, max_visible=5)
    labels = [child.label for child in tree.children]
    # leading "… (N more)" node, then the most recent 5 files
    assert labels[0] == "… (15 more)"
    assert labels[1:] == ["✓ f15.py", "✓ f16.py", "✓ f17.py", "✓ f18.py", "✓ f19.py"]


def test_no_more_node_when_exactly_at_limit():
    files = [f"f{i}.py" for i in range(5)]
    tree = render_folder_tree("/exact", files, max_visible=5)
    labels = [child.label for child in tree.children]
    assert labels == ["✓ f0.py", "✓ f1.py", "✓ f2.py", "✓ f3.py", "✓ f4.py"]


def test_same_folder_accumulates_files():
    folder, files = next_folder_state("/dir", ["a.py"], "/dir", "b.py")
    assert folder == "/dir"
    assert files == ["a.py", "b.py"]


def test_new_folder_resets_file_list():
    folder, files = next_folder_state("/dir", ["a.py", "b.py"], "/other", "c.py")
    assert folder == "/other"
    assert files == ["c.py"]


def test_first_folder_from_none():
    folder, files = next_folder_state(None, [], "/dir", "a.py")
    assert folder == "/dir"
    assert files == ["a.py"]
