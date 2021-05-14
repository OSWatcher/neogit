from pathlib import Path
from threading import local
from typing import Dict

from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    FileSizeColumn,
    Progress,
    SpinnerColumn,
    TimeElapsedColumn,
    TotalFileSizeColumn,
    TransferSpeedColumn,
)

from .abstract import AbstractConsoleAdapter, TaskPool


class RichConsoleAdapter(AbstractConsoleAdapter):
    """This adapter will use Rich library for console output"""

    def __init__(self):
        # main progress bar
        self._main_progress = Progress(
            SpinnerColumn(),
            "{task.description}",
            BarColumn(bar_width=None),
            "{task.completed} / {task.total}",
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            expand=True,
        )
        self._main_progress_total = 0
        self._main_task = self._main_progress.add_task("Neogit commit ", total=self._main_progress_total)
        # sha1 computation progress bar
        self._sha1_progress = Progress(
            SpinnerColumn(),
            "{task.description}",
            BarColumn(bar_width=None),
            FileSizeColumn(),
            TotalFileSizeColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
        )
        # object storage upload progress bar
        self._storage_progress = Progress(
            SpinnerColumn(),
            "{task.description}",
            BarColumn(),
            TransferSpeedColumn(),
            TotalFileSizeColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
        )
        self._pool_to_progress: Dict[TaskPool, Progress] = {
            TaskPool.SHA1: self._sha1_progress,
            TaskPool.Storage: self._storage_progress,
        }
        # add progress bar into panels
        self._sha1_panel = Panel(self._sha1_progress, title="SHA1 Pool")
        self._storage_panel = Panel(self._storage_progress, title="Object Storage Pool")
        # pipeline layout
        self._pipeline_layout = Layout(name="pipeline")
        self._pipeline_layout.split_column(
            self._sha1_panel,
            self._storage_panel,
        )
        # build main
        self._app_layout = Layout(name="main")
        self._app_layout.split_column(
            # progress bar is only 1 row
            Layout(self._main_progress, name="main_progress", size=1),
            self._pipeline_layout,
        )
        self._live = Live(self._app_layout, refresh_per_second=10)
        # thread-local tasks
        self._local = local()

    def __enter__(self):
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._live.stop()

    def increase_main_bar_total(self):
        self._main_progress_total += 1
        self._main_progress.update(self._main_task, total=self._main_progress_total)

    def advance_main_bar_progress(self):
        self._main_progress.update(self._main_task, advance=1)

    def set_pool_task(self, pool: TaskPool, filepath: Path, size: int):
        progress = self._pool_to_progress[pool]
        try:
            task = getattr(self._local, f"{pool.name.lower()}_task")
        except AttributeError:
            # create new task for this thread
            task = progress.add_task(description=str(filepath), total=size)
            setattr(self._local, f"{pool.name.lower()}_task", task)
        else:
            # set description and total, and reset completion
            progress.update(task, description=str(filepath), total=size, completed=0)

    def update_pool_task(self, pool: TaskPool, advance: int):
        try:
            task = getattr(self._local, f"{pool.name.lower()}_task")
        except AttributeError:
            raise RuntimeError(f"task not created for pool {pool}")
        else:
            progress = self._pool_to_progress[pool]
            progress.update(task, advance=advance)
