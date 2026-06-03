# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

"""Pure rendering helper for the ``neogit commit --gui`` folder pane.

Given the current folder label and the names of files hashed in it, build a
Rich ``Tree`` showing the folder and its merkelized files. Kept free of any
mutable state, threads, or ``Live`` so it can be unit-tested in isolation.
"""

from typing import List, Optional, Sequence, Tuple

from rich.tree import Tree


def next_folder_state(
    cur_folder: Optional[str], cur_files: Sequence[str], folder: str, filename: str
) -> Tuple[str, List[str]]:
    """Fold a freshly hashed file into the pane's (folder, files) state.

    When ``folder`` differs from ``cur_folder`` the depth-first walk has moved
    on, so start a new list; otherwise append to the running one. Pure: callers
    own the mutable state and the locking.
    """
    if folder != cur_folder:
        return folder, [filename]
    return folder, [*cur_files, filename]


def render_folder_tree(folder_label: str, filenames: Sequence[str], max_visible: int) -> Tree:
    """Render ``folder_label`` and its ``filenames`` as a Rich ``Tree``.

    Each file is shown with a ✓ (merkelized) marker. When more than
    ``max_visible`` files are present, only the most recent ``max_visible`` are
    shown, preceded by a ``… (N more)`` node so a huge directory cannot overflow
    the panel.
    """
    tree = Tree(f"📁 {folder_label}")
    hidden = len(filenames) - max_visible
    if hidden > 0:
        tree.add(f"… ({hidden} more)")
        filenames = filenames[-max_visible:]
    for name in filenames:
        tree.add(f"✓ {name}")
    return tree
