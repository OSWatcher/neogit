import os
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from rich.console import Group
from rich.live import Live
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


class RichConsoleAdapter(AbstractConsoleAdapter):
    """Rich-based adapter: one ``Live`` display with a spinner line, a
    counters line, and a per-uploader-thread progress panel.

    Paths reported through the hooks are converted for display to be
    relative to ``root`` while still rendered with a leading ``/`` so they
    look absolute (matching how a committed tree is conceptually rooted
    at the commit root, like git).
    """

    def __init__(self, root: Path, max_workers: Optional[int] = None) -> None:
        self._lock = Lock()
        self._root = root
        # Mirror ThreadPoolExecutor's default so the pre-allocated row count
        # matches the actual upload pool size.
        self._n_workers = max_workers if max_workers is not None else min(32, (os.cpu_count() or 1) + 4)

        # top: a spinner-style progress with a single task acting as the
        # "currently hashing X" indicator
        self._hash_progress = Progress(
            SpinnerColumn(),
            TextColumn("Hashing {task.description}"),
        )
        self._hash_task: TaskID = self._hash_progress.add_task("…", total=None)

        # middle: a single-line counters Text rendered inside a Panel
        self._counters = Text()
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

        # assemble the live layout
        layout = Group(
            self._hash_progress,
            Panel(self._counters, title="Stats", padding=(0, 1)),
            Panel(self._upload_progress, title="Uploaders", padding=(0, 1)),
        )
        self._live = Live(layout, refresh_per_second=10)

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

    # hashing hooks (visitor thread)

    def on_file_hashed(self, path: Path) -> None:
        with self._lock:
            self._files += 1
            self._render_counters()
            self._hash_progress.update(self._hash_task, description=self._format_path(path))

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
        # Worker IDs are assigned 1..N in arrival order inside ObjectUploader,
        # but the ``on_upload_started`` hook fires only *after* a per-file
        # ``get_object`` existence check, so rows can arrive out of order
        # (e.g. #10 before #9 if #9 paid an extra network round-trip).
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
