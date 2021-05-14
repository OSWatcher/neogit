from pathlib import Path
from threading import local
from typing import Dict

from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, FileSizeColumn, Progress, SpinnerColumn, TotalFileSizeColumn, TransferSpeedColumn

from .abstract import AbstractConsoleAdapter, TaskPool


class RichConsoleAdapter(AbstractConsoleAdapter):
    """This adapter will use Rich library for console output"""

    def __init__(self):
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
            BarColumn(bar_width=None),
            TransferSpeedColumn(),
            TotalFileSizeColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
        )
        self._pool_to_progress: Dict[TaskPool, Progress] = {
            TaskPool.SHA1: self._sha1_progress,
            TaskPool.Storage: self._storage_progress,
        }
        # panels
        self._sha1_panel = Panel(self._sha1_progress, title="SHA1 Pool")
        self._storage_panel = Panel(self._storage_progress, title="Object Storage Pool")
        # build layout
        self._main_layout = Layout(name="main")
        self._main_layout.split_column(
            self._sha1_panel,
            self._storage_panel,
        )
        self._live = Live(self._main_layout, refresh_per_second=10)
        # thread-local tasks
        self._local = local()

    def __enter__(self):
        self._live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._live.stop()

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
