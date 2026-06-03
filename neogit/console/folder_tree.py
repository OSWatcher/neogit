# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

"""Pure state + rendering helpers for the ``neogit commit --gui`` folder pane.

The pane shows the directory whose files are currently being hashed and the
files merkelized in it so far. ``FolderState`` keeps that state **bounded** —
only the most recent ``max_visible`` filenames are retained, with the rest
counted in ``hidden`` — so a directory with thousands of entries costs O(1) per
update instead of growing an unbounded list. ``render_folder_tree`` turns a
state into a Rich ``Tree``. Both are free of mutable state, threads, and
``Live`` so they can be unit-tested in isolation.
"""

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple

from rich.markup import escape
from rich.tree import Tree


@dataclass(frozen=True)
class FolderState:
    """Bounded view of the folder currently being hashed.

    ``recent`` holds at most ``max_visible`` filenames (the newest); ``hidden``
    counts how many older files dropped out of that window.
    """

    folder: Optional[str] = None
    hidden: int = 0
    recent: Tuple[str, ...] = field(default=())


# Folder-pane chrome that doesn't hold filenames: the panel's top and bottom
# borders (2), the spinner line that names the folder (1), and one row reserved
# for the "… (N more)" node. The tree's own root is hidden, so it costs nothing.
_PANE_OVERHEAD = 4


def visible_file_rows(screen_height: int, stats_rows: int) -> int:
    """How many file rows fit in the folder pane for a given terminal height.

    The Stats panel takes ``stats_rows`` at the top; the folder pane fills the
    rest, minus its own chrome (``_PANE_OVERHEAD``). Always at least 1 so a tiny
    terminal still shows the most recent file.
    """
    return max(screen_height - stats_rows - _PANE_OVERHEAD, 1)


def fold_file(state: FolderState, folder: str, filename: str, max_visible: int) -> FolderState:
    """Fold a freshly hashed file into ``state``, returning a new state.

    A change of ``folder`` means the depth-first walk moved on, so start fresh;
    otherwise append, evicting the oldest name (and counting it in ``hidden``)
    once more than ``max_visible`` are retained.
    """
    if folder != state.folder:
        return FolderState(folder=folder, hidden=0, recent=(filename,))
    recent = (*state.recent, filename)
    hidden = state.hidden
    if len(recent) > max_visible:
        overflow = len(recent) - max_visible
        hidden += overflow
        recent = recent[overflow:]
    return FolderState(folder=folder, hidden=hidden, recent=recent)


def render_folder_tree(hidden: int, recent: Sequence[str]) -> Tree:
    """Render the merkelized files of the current folder as a Rich ``Tree``.

    The folder itself is named once on the adapter's spinner line, so the tree's
    root is hidden and it shows only the files. Each file gets a ✓ marker; when
    ``hidden`` is positive a leading ``… (N more)`` node stands in for the
    evicted older files. Filenames are markup-escaped so ``[`` characters are not
    parsed as Rich tags (matching ``neogit/log/render.py`` and ``neogit/diff/render.py``).
    """
    tree = Tree("", hide_root=True)
    if hidden > 0:
        tree.add(f"… ({hidden} more)")
    for name in recent:
        tree.add(f"✓ {escape(name)}")
    return tree
