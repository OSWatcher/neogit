# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    FileSizeColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TotalFileSizeColumn,
    TransferSpeedColumn,
)
from rich.table import Column
from rich.text import Text

from .abstract import AbstractConsoleAdapter
from .folder_tree import FolderState, fold_file, render_folder_tree, visible_file_rows


class RichConsoleAdapter(AbstractConsoleAdapter):
    """Rich-based adapter: one ``Live`` display with a spinner line, a
    counters line, and a per-uploader-thread progress panel.

    Paths reported through the hooks are converted for display to be
    relative to ``root`` while still rendered with a leading ``/`` so they
    look absolute (matching how a committed tree is conceptually rooted
    at the commit root, like git).
    """

    # Height of the Stats row at the top of the layout (panel border + 1 line).
    # The folder pane fills the rest; how many files it shows is derived from
    # the terminal height (see _visible_capacity), so the list grows to fit.
    STATS_ROWS = 3

    def __init__(self, root: Path, max_workers: Optional[int] = None) -> None:
        self._lock = Lock()
        self._root = root
        # Mirror ThreadPoolExecutor's default so the pre-allocated row count
        # matches the actual upload pool size.
        self._n_workers = max_workers if max_workers is not None else min(32, (os.cpu_count() or 1) + 4)

        # a spinner-style progress whose single task names the folder currently
        # being hashed (updated per-folder, not per-file, so it doesn't flicker).
        # The "Hashing" label is the enclosing panel title (see _render_folder),
        # so the line itself is just the spinner + folder path.
        self._hash_progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
        )
        self._hash_task: TaskID = self._hash_progress.add_task("…", total=None)

        # folder pane state: the directory whose files are currently being
        # hashed, and the (bounded) names hashed in it so far (see folder_tree.py)
        self._folder = FolderState()

        # middle: a single-line counters Text rendered inside a Panel. Keep it
        # to one line (ellipsize rather than wrap) so the fixed-height Stats row
        # never clips a wrapped line on a narrow terminal.
        self._counters = Text(no_wrap=True, overflow="ellipsis")
        self._files = 0
        self._dirs = 0
        self._trees = 0
        self._uploaded = 0
        self._skipped = 0
        self._render_counters()

        # bottom: per-worker upload rows
        self._upload_progress = Progress(
            TextColumn("[bold]#{task.fields[worker_id]:>2}[/]"),
            TextColumn("{task.description}", table_column=Column(ratio=8, no_wrap=True)),
            BarColumn(bar_width=None, table_column=Column(ratio=4)),
            FileSizeColumn(),
            TextColumn("/"),
            TotalFileSizeColumn(),
            TransferSpeedColumn(),
            expand=True,
        )
        self._worker_to_task: Dict[int, TaskID] = {}
        # Pre-allocate one (idle) row per upload worker. Otherwise the
        # Uploaders panel stays empty until the first upload reaches the
        # pool, which only happens after the visitor has hashed at least
        # one file — that can be a noticeable wait on cold trees.
        for wid in range(1, self._n_workers + 1):
            task_id = self._upload_progress.add_task("(idle)", total=None, worker_id=wid)
            self._worker_to_task[wid] = task_id

        # assemble the live layout as a single root Layout so each region is
        # sized to exactly the screen (a Layout nested in a Group overflows and
        # crops the panel borders). Stats is a fixed row on top; below it the
        # folder pane (left) sits beside the Uploaders panel (right).
        self._layout = Layout()
        self._layout.split_column(
            Layout(Panel(self._counters, title="Stats", padding=(0, 1)), name="stats", size=self.STATS_ROWS),
            Layout(name="body"),
        )
        self._layout["body"].split_row(
            Layout(name="folder"),
            Layout(Panel(self._upload_progress, title="Uploaders", padding=(0, 1)), name="uploaders"),
        )
        self._live = Live(self._layout, refresh_per_second=10)
        self._render_folder()

    def _visible_capacity(self) -> int:
        """How many file rows the folder pane can show at the current size."""
        return visible_file_rows(self._live.console.size.height, self.STATS_ROWS)

    def _render_folder(self) -> None:
        """Rebuild the folder pane from current state (call under ``_lock``)."""
        label = self._folder.folder if self._folder.folder is not None else "…"
        tree = render_folder_tree(label, self._folder.hidden, self._folder.recent)
        body = Group(self._hash_progress, tree)
        self._layout["folder"].update(Panel(body, title="Hashing", padding=(0, 1)))

    def _format_path(self, path: Path) -> str:
        """Render an absolute filesystem path as if rooted at ``self._root``."""
        try:
            rel = path.relative_to(self._root)
        except ValueError:
            return str(path)
        rel_str = str(rel)
        if rel_str == ".":
            return "/"
        return "/" + rel_str

    def _render_counters(self) -> None:
        # noqa-line below: flake8 E231 dislikes the ``{x:,}`` format spec
        files = f"{self._files:,}"  # noqa: E231
        dirs = f"{self._dirs:,}"  # noqa: E231
        trees = f"{self._trees:,}"  # noqa: E231
        uploaded = f"{self._uploaded:,}"  # noqa: E231
        skipped = f"{self._skipped:,}"  # noqa: E231
        self._counters.plain = (
            f"files: {files}  dirs: {dirs}  trees: {trees}  uploaded: {uploaded}  skipped (dedup): {skipped}"
        )

    # context manager

    def __enter__(self) -> "RichConsoleAdapter":
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._live.stop()
        return None

    # hashing hooks (main thread, consuming visitor.as_gen())

    def on_file_hashed(self, path: Path) -> None:
        with self._lock:
            self._files += 1
            self._render_counters()
            folder = self._format_path(path.parent)
            changed = folder != self._folder.folder
            self._folder = fold_file(self._folder, folder, path.name, self._visible_capacity())
            if changed:
                # escape so ``[`` in the path isn't parsed as Rich markup
                self._hash_progress.update(self._hash_task, description=escape(folder))
            self._render_folder()

    def on_dir_merkelized(self, path: Path) -> None:
        with self._lock:
            self._dirs += 1
            self._render_counters()

    # cypher merge hook (main thread)

    def on_tree_merged(self) -> None:
        with self._lock:
            self._trees += 1
            self._render_counters()

    # upload hooks (N uploader pool threads)

    def _ensure_worker_row(self, worker_id: int) -> TaskID:
        # Worker IDs are assigned 1..N in first-arrival order inside ObjectUploader,
        # but workers reach ``on_upload_started`` in non-deterministic order
        # (e.g. #10 before #9 depending on scheduling).
        # Gap-fill any missing rows below ``worker_id`` so the panel stays
        # sorted regardless of arrival order.
        while len(self._worker_to_task) < worker_id:
            next_wid = len(self._worker_to_task) + 1
            task_id = self._upload_progress.add_task(
                "(idle)",
                total=None,
                worker_id=next_wid,
            )
            self._worker_to_task[next_wid] = task_id
        return self._worker_to_task[worker_id]

    def on_upload_started(self, worker_id: int, path: Path, size: int) -> None:
        with self._lock:
            task_id = self._ensure_worker_row(worker_id)
            self._upload_progress.reset(
                task_id,
                description=self._format_path(path),
                total=size,
                worker_id=worker_id,
            )

    def on_upload_progress(self, worker_id: int, advance: int) -> None:
        task_id = self._worker_to_task.get(worker_id)
        if task_id is None:
            return
        self._upload_progress.update(task_id, advance=advance)

    def on_upload_finished(self, worker_id: int, was_skipped: bool) -> None:
        with self._lock:
            if was_skipped:
                self._skipped += 1
            else:
                self._uploaded += 1
            # Snap the bar to 100% in both cases: for real uploads in case
            # chunk rounding left it short, and for skipped files so the
            # row visually shows the dedup happened (rather than freezing
            # at 0/SIZE).
            task_id = self._worker_to_task.get(worker_id)
            if task_id is not None:
                task = self._upload_progress.tasks[task_id]
                if task.total is not None:
                    self._upload_progress.update(task_id, completed=task.total)
            self._render_counters()
